"""
Code-generation driver for Functionality-DSL.

Steps
-----
1. Parse/validate the .fdsl file ->  `model`
2. Copy the FastAPI skeleton from  base/backend_base/  into <output_dir>/backend
3. Render Jinja templates with the model context:
      models.py     * Pydantic schemas
      services.py   * SQLAlchemy pipeline queries
      router.py     * FastAPI endpoints
4. Done → you can `uvicorn app.main:app --reload` inside output_dir/backend
"""
from __future__ import annotations
from pathlib import Path
import shutil

from functionality_dsl.language import build_model
from functionality_dsl.templates import env as jinja_env

# --------------------------------------------------------------------------- #
# 1) template map: {template → relative output path inside backend package}   #
# --------------------------------------------------------------------------- #
TEMPLATES: dict[str, str] = {
    "models.py.j2"   : "app/models.py",
    "schemas.py.j2"  : "app/schemas.py",
    "services.py.j2" : "app/services.py",
    "router.py.j2"   : "app/router.py",
}

# --------------------------------------------------------------------------- #
# 2) helpers                                                                  #
# --------------------------------------------------------------------------- #
def _copy_backend_base(target: Path) -> None:
    """
    Copy the FastAPI skeleton (base/app/*) into <output>/backend/app
    """
    src = Path(__file__).parent / "base" / "app"
    dst = target / "backend" / "app"
    shutil.copytree(src, dst, dirs_exist_ok=True)
    

def _render_templates(model, backend_dir: Path) -> None:
    """
    Feed every Jinja template with the **context** extracted from `model`
    and write the rendered text to the backend_dir.
    """
    ctx = dict(
        backend_entities  = getattr(model, "backend_entities", []),
        pipelines         = getattr(model, "pipelines", []),
        endpoints         = getattr(model, "endpoints", []),
        frontend_entities = getattr(model, "frontend_entities", []),
    )

    for tmpl_name, rel_path in TEMPLATES.items():
        template = jinja_env.get_template(tmpl_name)
        text     = template.render(**ctx)

        out_path = backend_dir / rel_path
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(text, encoding="utf-8")
        

# --------------------------------------------------------------------------- #
# 3) public entry-point used by the CLI                                       #
# --------------------------------------------------------------------------- #
def run_codegen(model_file: str, out_dir: Path | str) -> None:
    """
    Parse *model_file* and generate a FastAPI project inside *out_dir*.
    """
    out_path = Path(out_dir).resolve()
    backend_path = out_path / "backend"

    # 3-a) model = parse + semantic checks
    model = build_model(model_file)

    # 3-b) skeleton
    _copy_backend_base(out_path)

    # 3-c) Jinja templates
    _render_templates(model, backend_path)

    # 3-d) friendly message
    print(f"✅  Code generated in {out_path} (backend package ready to run)")
    

# --------------------------------------------------------------------------- #
# Convenience: allow `python -m functionality_dsl.generate <file> <dir>`     #
# --------------------------------------------------------------------------- #
if __name__ == "__main__":
    import sys
    if len(sys.argv) != 3:
        print("Usage: python -m functionality_dsl.generate model.fdsl output_dir")
        sys.exit(1)
    run_codegen(sys.argv[1], sys.argv[2])