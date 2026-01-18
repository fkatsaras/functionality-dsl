"""Infrastructure scaffolding and file generation."""

import re
import secrets
import shutil
import string
from pathlib import Path
from shutil import copytree
from jinja2 import Environment, FileSystemLoader, select_autoescape
from textx import get_children_of_type

from ...extractors import extract_server_config


def generate_random_secret(length: int = 32) -> str:
    """Generate a random alphanumeric secret string."""
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def render_infrastructure_files(context, templates_dir, output_dir, target="all", db_context=None):
    """
    Render infrastructure files (.env, docker-compose.yml, Dockerfile)
    from templates using the provided context.

    Args:
        context: Template context dictionary
        templates_dir: Path to templates directory
        output_dir: Output directory for generated files
        target: Generation target ("all", "backend", or "frontend")
        db_context: Database context for templates (optional)
    """
    # Add target to context for conditional rendering
    context["target"] = target
    env = Environment(
        loader=FileSystemLoader(str(templates_dir)),
        autoescape=select_autoescape(disabled_extensions=("jinja",)),
        trim_blocks=True,
        lstrip_blocks=True,
    )

    # Process auth configurations for environment variables (multi-auth support)
    auth_env_vars = []
    auth_configs = context.get("auth_configs", {})

    for auth_name, auth_config in auth_configs.items():
        auth_type = auth_config.get("auth_type")
        roles = auth_config.get("roles", [])

        if auth_type == "jwt":
            # JWT needs a secret key
            secret_var = auth_config.get("secret", "JWT_SECRET")
            auth_env_vars.append({
                "name": secret_var,
                "value": generate_random_secret(32),
                "comment": f"JWT Secret for {auth_name} (auto-generated)"
            })

        elif auth_type == "apikey":
            # API Key needs a keys list with roles
            secret_var = auth_config.get("secret", "API_KEYS")
            # Generate example keys with roles
            example_keys = []
            for role in roles[:3]:  # Limit to 3 example keys
                key = f"{role}_key_{generate_random_secret(8)}"
                example_keys.append(f"{key}:{role}")
            if not example_keys:
                example_keys = [f"default_key_{generate_random_secret(8)}"]
            auth_env_vars.append({
                "name": secret_var,
                "value": ",".join(example_keys),
                "comment": f"API Keys for {auth_name} (format: key:role1;role2,...)"
            })

        elif auth_type == "basic":
            # Basic auth needs username:password:roles
            users_var = auth_config.get("users", "BASIC_AUTH_USERS")
            # Generate example users with roles
            example_users = []
            for role in roles[:2]:  # Limit to 2 example users
                password = generate_random_secret(12)
                example_users.append(f"{role}:{password}:{role}")
            if not example_users:
                example_users = [f"admin:{generate_random_secret(12)}:admin"]
            auth_env_vars.append({
                "name": users_var,
                "value": ",".join(example_users),
                "comment": f"Basic Auth users for {auth_name} (format: user:pass:role1;role2,...)"
            })

        elif auth_type == "session":
            # Session doesn't need env vars for secrets (uses in-memory store)
            pass

    context["auth_env_vars"] = auth_env_vars

    # Legacy support: also set jwt_secret_var for old templates
    auth_config = context.get("auth")
    if auth_config and auth_config.get("type") == "jwt":
        jwt_config = auth_config.get("jwt", {})
        if jwt_config.get("secret"):
            context["jwt_secret_var"] = jwt_config["secret"]
            if "jwt_secret_value" not in context:
                context["jwt_secret_value"] = generate_random_secret(32)

    # Merge database context if provided
    if db_context:
        context.update(db_context)

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


def _copy_runtime_libs(lib_root: Path, backend_core_dir: Path, templates_dir: Path = None):
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

    # --- Copy error_handlers.py to app/core ---
    if templates_dir:
        error_handlers_src = templates_dir / "core" / "error_handlers.py"
        error_handlers_dest = backend_core_dir / "error_handlers.py"
        if error_handlers_src.exists():
            shutil.copy2(error_handlers_src, error_handlers_dest)
            print("  [OK] Created app/core/error_handlers.py")
        else:
            print("  [WARN] error_handlers.py template not found")
    else:
        print("  [WARN] templates_dir not provided, skipping error_handlers.py")


def _extract_auth_configs(model):
    """
    Extract auth configurations from the model for env generation.

    Returns dict mapping auth_name -> {auth_type, secret, roles, ...}
    """
    auth_configs = {}

    # Get all Auth declarations - access directly from model since Auth is a union type
    auth_blocks = getattr(model, "auth", []) or []

    # Get all Role declarations to map roles to auths
    role_blocks = get_children_of_type("Role", model)
    roles_by_auth = {}
    for role in role_blocks:
        auth_name = role.auth.name if role.auth else None
        if auth_name:
            if auth_name not in roles_by_auth:
                roles_by_auth[auth_name] = []
            roles_by_auth[auth_name].append(role.name)

    for auth in auth_blocks:
        auth_name = auth.name
        auth_type = getattr(auth, "kind", None)  # Use 'kind' from Auth<kind> syntax

        if not auth_type:
            continue

        config = {
            "auth_type": auth_type,
            "auth_name": auth_name,
            "roles": roles_by_auth.get(auth_name, []),
        }

        # Helper to get value or default
        def get_or_default(attr, default):
            val = getattr(auth, attr, None)
            return val if val is not None and val != "" else default

        # Extract type-specific config (fields are directly on auth object now)
        if auth_type == "jwt":
            config["secret"] = get_or_default("secret", "JWT_SECRET")

        elif auth_type == "apikey":
            config["secret"] = get_or_default("secret", "API_KEYS")

        elif auth_type == "basic":
            config["users"] = "BASIC_AUTH_USERS"

        auth_configs[auth_name] = config

    return auth_configs


def scaffold_backend_from_model(model, base_backend_dir: Path, templates_backend_dir: Path, out_dir: Path, jwt_secret_value: str = None, db_context: dict = None, target: str = "all") -> Path:
    """
    Scaffold the complete backend structure from the model.
    Copies base files and renders environment/Docker configuration.

    Args:
        model: The parsed FDSL model
        base_backend_dir: Path to base backend template files
        templates_backend_dir: Path to backend Jinja templates
        out_dir: Output directory for generated code
        jwt_secret_value: Pre-generated JWT secret value (optional)
        db_context: Database context for templates (optional)
        target: Generation target ("all", "backend", or "frontend")
    """
    print("\n[SCAFFOLD] Creating backend structure...")

    # Extract server configuration
    context = extract_server_config(model)

    # Extract auth configurations for multi-auth env generation
    context["auth_configs"] = _extract_auth_configs(model)

    # Use pre-generated JWT secret if provided
    if jwt_secret_value:
        context["jwt_secret_value"] = jwt_secret_value

    # Copy base backend files
    copytree(base_backend_dir, out_dir, dirs_exist_ok=True)
    print(f"[SCAFFOLD] Copied base files to {out_dir}")

    # ---  Copy DSL runtime ---
    from functionality_dsl.lib import builtins  # ensures proper path resolution
    lib_root = Path(builtins.__file__).parent.parent  # functionality_dsl/lib/
    backend_core_dir = out_dir / "app" / "core"
    _copy_runtime_libs(lib_root, backend_core_dir, templates_backend_dir)

    # Render infrastructure files
    render_infrastructure_files(context, templates_backend_dir, out_dir, target=target, db_context=db_context)

    return out_dir
