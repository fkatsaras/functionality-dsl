"""Infrastructure scaffolding and file generation."""

import re
from pathlib import Path
from shutil import copytree
from jinja2 import Environment, FileSystemLoader, select_autoescape

from ..extractors import extract_server_config


def render_infrastructure_files(context, templates_dir, output_dir):
    """
    Render infrastructure files (.env, docker-compose.yml, Dockerfile)
    from templates using the provided context.
    """
    env = Environment(
        loader=FileSystemLoader(str(templates_dir)),
        autoescape=select_autoescape(disabled_extensions=("jinja",)),
        trim_blocks=True,
        lstrip_blocks=True,
    )

    # Map output files to their templates
    file_mappings = {
        ".env": "env.jinja",
        "docker-compose.yml": "docker-compose.yaml.jinja",
        "Dockerfile": "Dockerfile.jinja",
    }

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    for output_file, template_name in file_mappings.items():
        template = env.get_template(template_name)
        content = template.render(**context)
        (output_dir / output_file).write_text(content, encoding="utf-8")
        print(f"[GENERATED] {output_file}")


def _copy_runtime_libs(lib_root: Path, backend_core_dir: Path):
    """
    Copy the essential runtime modules (builtins, compiler, runtime)
    from functionality_dsl/lib/ into the generated backend app/core/.
    Automatically patches imports so the generated backend
    is fully self-contained (no dependency on functionality_dsl).
    """
    print("[SCAFFOLD] Copying DSL runtime modules...")

    src_dirs = ["builtins", "runtime"]
    backend_core_dir.mkdir(parents=True, exist_ok=True)

    for d in src_dirs:
        src = lib_root / d
        dest = backend_core_dir / d
        if not src.exists():
            print(f"  [WARN] Missing {src}, skipping.")
            continue
        copytree(src, dest, dirs_exist_ok=True)
        print(f"  [OK] Copied {d}/")

    # --- Patch safe_eval.py to remove absolute import ---
    safe_eval_dest = backend_core_dir / "runtime" / "safe_eval.py"
    if safe_eval_dest.exists():
        text = safe_eval_dest.read_text(encoding="utf-8")

        # Replace import from generator to local backend core
        patched = re.sub(
            r"from\s+functionality_dsl\.lib\.builtins\.registry",
            "from app.core.builtins.registry",
            text,
        )

        safe_eval_dest.write_text(patched, encoding="utf-8")
        print("  [PATCH] Updated import in runtime/safe_eval.py")

    # --- Create a lightweight computed.py facade ---
    computed_dest = backend_core_dir / "computed.py"
    computed_dest.write_text(
        "# Auto-generated DSL runtime bridge\n\n"
        "from app.core.builtins.registry import (\n"
        "    DSL_FUNCTIONS,\n"
        "    DSL_FUNCTION_REGISTRY,\n"
        "    DSL_FUNCTION_SIG,\n"
        ")\n"
        "from app.core.compiler.expr_compiler import compile_expr_to_python\n",
        encoding="utf-8",
    )
    print("  [OK] Created app/core/computed.py")


def scaffold_backend_from_model(model, base_backend_dir: Path, templates_backend_dir: Path, out_dir: Path) -> Path:
    """
    Scaffold the complete backend structure from the model.
    Copies base files and renders environment/Docker configuration.
    """
    print("\n[SCAFFOLD] Creating backend structure...")

    # Extract server configuration
    context = extract_server_config(model)

    # Copy base backend files
    copytree(base_backend_dir, out_dir, dirs_exist_ok=True)
    print(f"[SCAFFOLD] Copied base files to {out_dir}")

    # ---  Copy DSL runtime ---
    from functionality_dsl.lib import builtins  # ensures proper path resolution
    lib_root = Path(builtins.__file__).parent.parent  # functionality_dsl/lib/
    backend_core_dir = out_dir / "app" / "core"
    _copy_runtime_libs(lib_root, backend_core_dir)

    # Render infrastructure files
    render_infrastructure_files(context, templates_backend_dir, out_dir)

    return out_dir
