# functionality_dsl/frontend/generator.py
from __future__ import annotations
from pathlib import Path
import re
from shutil import copytree
from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape
from textx import get_children_of_type

# ---- helpers ----
def _components(model):
    from textx import get_children_of_type as _gc
    return list(_gc("Component", model))

def _get_server_ctx(model):
    servers = list(get_children_of_type("Server", model))
    if not servers:
        raise RuntimeError("No `Server` block found in model.")
    s = servers[0]
    cors_val = getattr(s, "cors", None)
    if isinstance(cors_val, (list, tuple)) and len(cors_val) == 1:
        cors_val = cors_val[0]
    return {
        "server": {
            "name": s.name,
            "host": getattr(s, "host", "localhost"),
            "port": int(getattr(s, "port", 8080)),
            "cors": cors_val or "http://localhost:3000",
        }
    }

def _props_to_dict(cmp):
    """
    Consume parser annotations:
      - columns: p._keys -> [{key: "..."}]
      - primaryKey (and others): p._value -> "..."
    """
    props = {}
    for p in getattr(cmp, "props", []) or []:
        if hasattr(p, "_keys"):
            props[p.key] = [{"key": k} for k in p._keys]
        elif hasattr(p, "_value"):
            props[p.key] = p._value
        else:
            # last-resort literal if present
            val = getattr(p, "value", None) or getattr(p, "text", None)
            props[p.key] = str(val) if val is not None else None
    print(props)
    return props

# ---- SvelteKit scaffold (copy base + render Jinja templates) ----
def _jinja_env(*, loader):
    env = Environment(
        loader=loader,
        autoescape=select_autoescape(disabled_extensions=("jinja",)),
        trim_blocks=True,
        lstrip_blocks=True,
        undefined=StrictUndefined,
    )
    env.filters["props_dict"] = lambda cmp: _props_to_dict(cmp)
    return env

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

def _render_component(env: Environment, cmp):
    type_name = getattr(cmp, "type_name", None) or getattr(cmp, "type", None)
    if not type_name:
        raise RuntimeError("Component missing type")
    props = _props_to_dict(cmp)
    # try specific, fall back to a default renderer
    for name in (f"components/{type_name}.svelte.jinja", "components/_default.svelte.jinja"):
        try:
            tpl = env.get_template(name)
            return tpl.render(component=cmp, props=props)
        except Exception:
            continue
    raise RuntimeError(f"No template for component type '{type_name}'")

def render_frontend_files(model, templates_dir: Path, out_dir: Path):
    env = _jinja_env(loader=FileSystemLoader([str(templates_dir / "components"), str(templates_dir)]))
    components = _components(model)
    snippets = [_render_component(env, c) for c in components]
    page_tpl = env.get_template("+page.svelte.jinja")
    (out_dir / "src" / "routes" / "+page.svelte").write_text(page_tpl.render(snippets=snippets), encoding="utf-8")