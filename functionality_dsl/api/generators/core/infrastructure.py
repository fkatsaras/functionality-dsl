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
from ...gen_logging import get_logger

logger = get_logger(__name__)


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

    # Entity auth is DB-backed - no env vars needed for entity auth secrets
    # Source auth uses env vars for static credentials to external APIs
    context["auth_env_vars"] = []  # Entity auth (unused)
    context["source_auth_env_vars"] = context.get("source_auth_env_vars", [])

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
        logger.debug(f"[GENERATED] {output_file}")


def _copy_runtime_libs(lib_root: Path, backend_core_dir: Path, templates_dir: Path = None):
    """
    Copy the essential runtime modules (builtins, compiler, runtime)
    from functionality_dsl/lib/ into the generated backend app/core/.
    Automatically patches imports so the generated backend
    is fully self-contained (no dependency on functionality_dsl).
    """
    logger.debug("[SCAFFOLD] Copying DSL runtime modules...")

    src_dirs = ["builtins", "runtime"]
    backend_core_dir.mkdir(parents=True, exist_ok=True)

    for d in src_dirs:
        src = lib_root / d
        dest = backend_core_dir / d
        if not src.exists():
            logger.warning(f"  [WARN] Missing {src}, skipping.")
            continue
        copytree(src, dest, dirs_exist_ok=True)
        logger.debug(f"  [OK] Copied {d}/")

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
        logger.debug("  [PATCH] Updated import in runtime/safe_eval.py")

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
    logger.debug("  [OK] Created app/core/computed.py")

    # --- Copy error_handlers.py to app/core ---
    if templates_dir:
        error_handlers_src = templates_dir / "core" / "error_handlers.py"
        error_handlers_dest = backend_core_dir / "error_handlers.py"
        if error_handlers_src.exists():
            shutil.copy2(error_handlers_src, error_handlers_dest)
            logger.debug("  [OK] Created app/core/error_handlers.py")
        else:
            logger.warning("  [WARN] error_handlers.py template not found")
    else:
        logger.warning("  [WARN] templates_dir not provided, skipping error_handlers.py")


def _extract_auth_configs(model):
    """
    Extract auth configurations from the model.

    Auth types (from grammar):
    - Auth<http> with scheme: bearer | basic
    - Auth<apikey> with in: header | query | cookie

    All auth is DB-backed - no env vars needed.

    Returns dict mapping auth_name -> {auth_type, scheme/location, roles, ...}
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

        # Extract type-specific config
        if auth_type == "http":
            config["scheme"] = getattr(auth, "scheme", "bearer")

        elif auth_type == "apikey":
            config["location"] = getattr(auth, "location", "header")
            config["name"] = getattr(auth, "keyName", "X-API-Key")

        auth_configs[auth_name] = config

    return auth_configs


def generate_test_infrastructure(model, templates_dir: Path, out_dir: Path, exposure_map: dict, db_context: dict = None):
    """
    Generate test infrastructure including:
    - tests/conftest.py (fixtures for auth, db, client)
    - tests/api/test_{entity}.py for each entity
    - CI/CD workflows (.github/workflows/)
    - Pre-commit configuration
    - Scripts (prestart.py, test.sh)

    Args:
        model: The parsed FDSL model
        templates_dir: Path to templates directory
        out_dir: Output directory
        exposure_map: Entity exposure configuration
        db_context: Database context (optional)
    """
    logger.info("[TEST] Generating test infrastructure...")

    # Setup Jinja environment
    env = Environment(
        loader=FileSystemLoader(str(templates_dir)),
        autoescape=select_autoescape(disabled_extensions=("jinja",)),
        trim_blocks=True,
        lstrip_blocks=True,
    )

    # Extract auth configuration for test fixtures
    auth_configs = _extract_auth_configs(model)
    has_auth = len(auth_configs) > 0
    has_bearer_auth = any(c.get("scheme") == "bearer" for c in auth_configs.values() if c.get("auth_type") == "http")
    has_basic_auth = any(c.get("scheme") == "basic" for c in auth_configs.values() if c.get("auth_type") == "http")
    has_apikey_auth = any(c.get("auth_type") == "apikey" for c in auth_configs.values())

    # Find admin role (first role in first auth config)
    admin_role = None
    default_role = None
    apikey_header = "X-API-Key"
    apikey_location = "header"  # header, query, or cookie

    if auth_configs:
        first_auth = next(iter(auth_configs.values()))
        roles = first_auth.get("roles", [])
        if roles:
            admin_role = roles[0]
            default_role = roles[0]

        # Get API key header name and location
        for auth_config in auth_configs.values():
            if auth_config.get("auth_type") == "apikey":
                apikey_header = auth_config.get("name", "X-API-Key")
                apikey_location = auth_config.get("location", "header")
                break

    # Get FDSL file name
    fdsl_file = getattr(model, "_tx_filename", "unknown.fdsl")

    test_context = {
        "fdsl_file": fdsl_file,
        "has_auth": has_auth,
        "has_bearer_auth": has_bearer_auth,
        "has_basic_auth": has_basic_auth,
        "has_apikey_auth": has_apikey_auth,
        "admin_role": admin_role,
        "default_role": default_role,
        "apikey_header": apikey_header,
        "apikey_location": apikey_location,
        "uses_default_db": db_context.get("uses_default_db", False) if db_context else False,
        "db_user": db_context.get("db_user", "fdsl_user") if db_context else "fdsl_user",
        "db_password": db_context.get("db_password", "fdsl_pass") if db_context else "fdsl_pass",
        "db_name": db_context.get("db_name", "fdsl_db") if db_context else "fdsl_db",
        "db_port": db_context.get("db_port", 5432) if db_context else 5432,
    }

    # 1. Generate tests/conftest.py
    tests_dir = out_dir / "tests"
    tests_api_dir = tests_dir / "api"
    tests_dir.mkdir(parents=True, exist_ok=True)
    tests_api_dir.mkdir(parents=True, exist_ok=True)

    conftest_template = env.get_template("tests/conftest.py.jinja")
    conftest_content = conftest_template.render(**test_context)
    (tests_dir / "conftest.py").write_text(conftest_content, encoding="utf-8")
    logger.debug("[TEST] Generated tests/conftest.py")

    # Create __init__.py files
    (tests_dir / "__init__.py").write_text('"""Tests for the generated FDSL application."""', encoding="utf-8")
    (tests_api_dir / "__init__.py").write_text('"""API route tests."""', encoding="utf-8")

    # 2. Generate test_{entity}.py for each entity
    entity_test_template = env.get_template("tests/api/test_entity.py.jinja")

    for entity_name, config in exposure_map.items():
        # Get entity from model
        entity = None
        entities = get_children_of_type("Entity", model)
        for e in entities:
            if e.name == entity_name:
                entity = e
                break

        if not entity:
            continue

        # Determine operations
        operations = []
        is_composite = False  # Entities without sources (derived/computed entities)

        if config.get("rest_path"):
            # REST entity - check if it has a source
            source = entity.source if hasattr(entity, "source") and entity.source else None
            if source and hasattr(source, "operations") and source.operations:
                # Handle SourceOperationsList - operations attribute contains the list
                ops_list = getattr(source.operations, "operations", None)
                if ops_list:
                    # Operations can be strings or objects with .name
                    operations = [op if isinstance(op, str) else (op.name if hasattr(op, "name") else str(op)) for op in ops_list]
                else:
                    logger.debug(f"  Could not extract operations from {type(source.operations)}")
            else:
                # No source = composite/derived entity (only has read operation)
                is_composite = True
                operations = ['read']

        # Parse access control
        access_config = {
            "read": "public",
            "create": "public",
            "update": "public",
            "delete": "public",
            "read_roles": [],
            "create_roles": [],
            "update_roles": [],
            "delete_roles": [],
        }

        if hasattr(entity, "access") and entity.access:
            access = entity.access
            if isinstance(access, str):
                # Simple access: public or AuthName
                for op in ["read", "create", "update", "delete"]:
                    access_config[op] = access
            elif isinstance(access, list):
                # List of roles
                for op in ["read", "create", "update", "delete"]:
                    access_config[f"{op}_roles"] = [r.name if hasattr(r, "name") else str(r) for r in access]
            elif hasattr(access, "operations"):
                # Per-operation access
                for op_access in access.operations:
                    op_name = op_access.operation
                    if isinstance(op_access.access, list):
                        access_config[f"{op_name}_roles"] = [r.name if hasattr(r, "name") else str(r) for r in op_access.access]
                    else:
                        access_config[op_name] = op_access.access

        # Get attributes with test values
        attributes = []
        if hasattr(entity, "attributes") and entity.attributes:
            for attr in entity.attributes:
                # Generate test value based on type
                attr_type = attr.type.name if hasattr(attr.type, "name") else str(attr.type)
                test_value = _generate_test_value(attr_type)

                attributes.append({
                    "name": attr.name,
                    "type": attr_type,
                    "readonly": hasattr(attr, "modifiers") and "readonly" in [m.name for m in (attr.modifiers or [])],
                    "optional": hasattr(attr, "modifiers") and "optional" in [m.name for m in (attr.modifiers or [])],
                    "is_computed": hasattr(attr, "computed_expr") and attr.computed_expr is not None,
                    "test_value": test_value,
                })

        # Extract required parameters from source
        required_params = []
        source_has_auth = False
        if hasattr(entity, "source") and entity.source:
            source = entity.source
            # Check for params
            if hasattr(source, "params") and source.params:
                # SourceParamsList has a 'params' attribute containing the actual list
                params_list = getattr(source.params, "params", None)
                if params_list:
                    for param in params_list:
                        param_name = param if isinstance(param, str) else (param.name if hasattr(param, "name") else str(param))

                        # Find matching attribute in entity to get type
                        test_val = '"test_value"'  # Default fallback
                        if hasattr(entity, "attributes") and entity.attributes:
                            for attr in entity.attributes:
                                if attr.name == param_name:
                                    attr_type = attr.type.name if hasattr(attr.type, "name") else str(attr.type)
                                    test_val = _generate_test_value(attr_type)
                                    break

                        required_params.append({
                            "name": param_name,
                            "test_value": test_val,
                        })
            # Check for source auth (external auth)
            if hasattr(source, "auth") and source.auth:
                source_has_auth = True

        entity_context = {
            **test_context,
            "entity": {
                "name": entity_name,
                "operations": operations,
                "type": getattr(entity, "type", None),
                "access": access_config,
                "attributes": attributes,
                "required_params": required_params,
                "source_has_auth": source_has_auth,
            },
        }

        test_content = entity_test_template.render(**entity_context)
        test_file = tests_api_dir / f"test_{entity_name.lower()}.py"
        test_file.write_text(test_content, encoding="utf-8")
        logger.debug(f"[TEST] Generated tests/api/test_{entity_name.lower()}.py")

    # 3. Generate CI/CD workflows
    github_dir = out_dir / ".github" / "workflows"
    github_dir.mkdir(parents=True, exist_ok=True)

    # Test workflow
    test_workflow_template = env.get_template(".github/workflows/test.yml.jinja")
    test_workflow_content = test_workflow_template.render(**test_context)
    (github_dir / "test.yml").write_text(test_workflow_content, encoding="utf-8")
    logger.debug("[TEST] Generated .github/workflows/test.yml")

    # Lint workflow
    lint_workflow_template = env.get_template(".github/workflows/lint.yml.jinja")
    lint_workflow_content = lint_workflow_template.render(**test_context)
    (github_dir / "lint.yml").write_text(lint_workflow_content, encoding="utf-8")
    logger.debug("[TEST] Generated .github/workflows/lint.yml")

    # 4. Generate pre-commit configuration
    precommit_template = env.get_template(".pre-commit-config.yaml.jinja")
    precommit_content = precommit_template.render(**test_context)
    (out_dir / ".pre-commit-config.yaml").write_text(precommit_content, encoding="utf-8")
    logger.debug("[TEST] Generated .pre-commit-config.yaml")

    # 5. Generate scripts
    scripts_dir = out_dir / "scripts"
    scripts_dir.mkdir(parents=True, exist_ok=True)

    # Copy test.sh (static file)
    test_sh_src = templates_dir / "scripts" / "test.sh"
    if test_sh_src.exists():
        shutil.copy2(test_sh_src, scripts_dir / "test.sh")
        (scripts_dir / "test.sh").chmod(0o755)  # Make executable
        logger.debug("[TEST] Generated scripts/test.sh")

    # Generate prestart.py (if using database OR has auth)
    # Auth systems need DB initialization even if not using BYODB
    if test_context["uses_default_db"] or test_context["has_auth"]:
        prestart_template = env.get_template("scripts/prestart.py.jinja")
        prestart_content = prestart_template.render(**test_context)
        (scripts_dir / "prestart.py").write_text(prestart_content, encoding="utf-8")
        logger.debug("[TEST] Generated scripts/prestart.py")

    logger.info("[TEST] Test infrastructure generation complete!")


def _generate_test_value(attr_type: str):
    """Generate appropriate test value based on attribute type."""
    # Handle complex types
    attr_type_lower = attr_type.lower()

    # Array types
    if 'array' in attr_type_lower:
        if '<' in attr_type:
            # array<LineItem> -> realistic nested data
            inner_type = attr_type.split('<')[1].split('>')[0]
            if inner_type == 'LineItem':
                return '[{"product_id": 1, "name": "Test Product", "price": 19.99, "quantity": 2}]'
            elif inner_type in ['Product', 'ProductImage', 'ShippingOption', 'Order']:
                return '[]'  # Empty array for complex types in tests
            else:
                return '[1, 2, 3]'  # Default array
        return '[]'

    # Object types
    if 'object' in attr_type_lower:
        if '<' in attr_type:
            inner_type = attr_type.split('<')[1].split('>')[0]
            if inner_type == 'Category':
                return '{"id": 1, "name": "Electronics", "slug": "electronics"}'
            elif inner_type == 'Address':
                return '{"street": "123 Main St", "city": "Boston", "zip": "02101", "country": "USA"}'
            else:
                return '{}'
        return '{}'

    # Datetime/URI types
    if 'datetime' in attr_type_lower:
        return '"2024-01-15T10:30:00Z"'
    if 'uri' in attr_type_lower:
        return '"https://example.com/image.jpg"'

    # Basic types
    basic_types = {
        "string": '"test_value"',
        "integer": '42',
        "number": '19.99',
        "boolean": 'True',
    }

    return basic_types.get(attr_type_lower, '"test"')


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
    logger.debug("[SCAFFOLD] Creating backend structure...")

    # Extract server configuration
    context = extract_server_config(model)

    # Extract auth configurations for multi-auth env generation
    context["auth_configs"] = _extract_auth_configs(model)

    # Use pre-generated JWT secret if provided
    if jwt_secret_value:
        context["jwt_secret_value"] = jwt_secret_value

    # Copy base backend files
    copytree(base_backend_dir, out_dir, dirs_exist_ok=True)
    logger.debug(f"[SCAFFOLD] Copied base files to {out_dir}")

    # ---  Copy DSL runtime ---
    from functionality_dsl.lib import builtins  # ensures proper path resolution
    lib_root = Path(builtins.__file__).parent.parent  # functionality_dsl/lib/
    backend_core_dir = out_dir / "app" / "core"
    _copy_runtime_libs(lib_root, backend_core_dir, templates_backend_dir)

    # Render infrastructure files
    render_infrastructure_files(context, templates_backend_dir, out_dir, target=target, db_context=db_context)

    return out_dir
