from __future__ import annotations


from pathlib import Path
from shutil import copytree
from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape
from bs4 import BeautifulSoup

from textx import get_children_of_type

from functionality_dsl.lib.component_types import COMPONENT_TYPES


# ---------- helpers ----------

def beautify_html(html_str: str) -> str:
    soup = BeautifulSoup(html_str, "html.parser")
    return soup.prettify()

def _components(model):
    cmps = getattr(model, "aggregated_components", None)
    if cmps is not None:
        return list(cmps)

    from textx import get_children_of_type as _gc
    nodes = []
    for rule in COMPONENT_TYPES.keys():
        nodes += list(_gc(rule, model))
    return nodes

def _get_server_ctx(model):
    servers = list(get_children_of_type("Server", model))
    if not servers:
        raise RuntimeError("No `Server` block found in model.")
    s = servers[0]
    cors_val = getattr(s, "cors", None)
    if isinstance(cors_val, (list, tuple)) and len(cors_val) == 1:
        cors_val = cors_val[0]

    env_val = getattr(s, "env", None)
    env_val = (env_val or "").lower()
    if env_val not in {"dev", ""}:
        # treat anything not 'dev' as production
        env_val = ""

    # Extract auth configuration
    auth_config = None
    auth = getattr(s, "auth", None)
    if auth:
        auth_type = getattr(auth, "type", None)
        if auth_type == "jwt":
            jwt_config = getattr(auth, "jwt_config", None)
            secret = getattr(jwt_config, "secret", None) if jwt_config else None
            auth_config = {
                "type": "jwt",
                "secret": secret,
            }

    # Extract roles
    roles = [r.name for r in get_children_of_type("Role", model)]

    return {
        "server": {
            "name": s.name,
            "host": getattr(s, "host", "localhost"),
            "port": int(getattr(s, "port", 8080)),
            "cors": cors_val or "http://localhost:3000",
            "env": env_val,
        },
        "auth": auth_config,
        "roles": roles,
    }

def _jinja_env(*, loader):
    return Environment(
        loader=loader,
        autoescape=select_autoescape(disabled_extensions=("jinja",)),
        trim_blocks=True,
        lstrip_blocks=True,
        undefined=StrictUndefined,
    )

# ---------- scaffold ----------
def scaffold_frontend_from_model(model, *, base_frontend_dir: Path, templates_frontend_dir: Path, out_dir: Path) -> Path:
    ctx = _get_server_ctx(model)
    copytree(base_frontend_dir, out_dir, dirs_exist_ok=True)
    env = _jinja_env(loader=FileSystemLoader(str(templates_frontend_dir)))
    for target, tpl_name in {
        "vite.config.ts": "vite.config.ts.jinja",
        "Dockerfile":     "Dockerfile.jinja",
    }.items():
        tpl = env.get_template(tpl_name)
        (out_dir / target).write_text(tpl.render(**ctx), encoding="utf-8")
    return out_dir

# ---------- page render ----------
def _is_ws_entity(ent) -> bool:
    src = getattr(ent, "source", None)
    return src and src.__class__.__name__ == "WSEndpoint"

def _is_computed_with_ws(ent) -> bool:
    if not getattr(ent, "inputs", None):
        return False
    for inp in ent.inputs:
        t = inp.target
        s = getattr(t, "source", None)
        if s and s.__class__.__name__ == "WSEndpoint":
            return True
    return False

def render_frontend_files(model, templates_dir: Path, out_dir: Path):
    env = Environment(
        loader=FileSystemLoader([str(templates_dir / "components"), str(templates_dir)]),
        autoescape=select_autoescape(disabled_extensions=("jinja",)),
        trim_blocks=True,
        lstrip_blocks=True,
        undefined=StrictUndefined,
    )

    components = _components(model)
    ctx = _get_server_ctx(model)

    ws_entities = {e.name for e in get_children_of_type("Entity", model) if _is_ws_entity(e)}
    computed_ws_entities = {
        e.name for e in get_children_of_type("Entity", model) if _is_computed_with_ws(e)
    }

    # Extract per-operation access permissions for components
    from functionality_dsl.api.generators.core.auth_generator import get_permission_dependencies

    component_permissions = {}
    for cmp in components:
        entity_name = cmp.entity_ref.name
        entity = cmp.entity_ref

        # Get the operation for this component (if it's an ActionForm)
        operation = getattr(cmp, "operation", None)

        # Get all permission dependencies for this entity
        perm_deps = get_permission_dependencies(entity, model)

        # Store per-component: either specific operation or default to "read"
        if operation:
            # ActionForm - specific operation
            roles = perm_deps.get(operation, ["public"])
            component_permissions[cmp.name] = {
                "entity": entity_name,
                "operation": operation,
                "roles": roles
            }
        else:
            # Other components - use "read" operation by default
            roles = perm_deps.get("read", ["public"])
            component_permissions[cmp.name] = {
                "entity": entity_name,
                "operation": "read",
                "roles": roles
            }

    (out_dir / "src" / "routes").mkdir(parents=True, exist_ok=True)
    page_tpl = env.get_template("+page.svelte.jinja")
    (out_dir / "src" / "routes" / "+page.svelte").write_text(
        page_tpl.render(
            components=components,
            ws_entities=ws_entities,
            computed_ws_entities=computed_ws_entities,
            auth=ctx.get("auth"),
            roles=ctx.get("roles", []),
            component_permissions=component_permissions,
        ),
        encoding="utf-8",
    )

    # Format for readability
    # try:
    #     page_path = out_dir / "src" / "routes" / "+page.svelte"

    #     raw = page_path.read_text(encoding="utf-8")
    #     pretty = beautify_html(raw)

    #     page_path.write_text(pretty, encoding="utf-8")
    # except Exception as e:
    #     print("[WARN] HTML beautification failed:", e)