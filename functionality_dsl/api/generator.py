from __future__ import annotations

import re

from pathlib import Path
from shutil import copytree
from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape
from textx import get_children_of_type

def _entities(model):
    return list(get_children_of_type("Entity", model))

def _rest_endpoints(model):
    return list(get_children_of_type("RESTEndpoint", model))

def _ws_endpoints(model):
    return list(get_children_of_type("WSEndpoint", model))

def _pyd_type_for(attr):
    # very simple mapper
    t = getattr(attr, "type", None)
    return {
        "int": "int",
        "float": "float",
        "string": "str",
        "bool": "bool",
        "datetime": "datetime",
    }.get((t or "").lower(), "Any")
    
def _as_headers_list(obj):
    """
    Normalize the .headers attribute from a RESTEndpoint or WSEndpoint.
    Returns list[{"key": str, "value": str}].
    Accepts either:
      - None
      - list of Header objects (from grammar with headers: [Key: "Value", ...])
      - a single string "Key: Value; Another: Foo"
    """
    hs = getattr(obj, "headers", None)
    out = []
    if not hs:
        return out

    # Case 1: grammar gave us a list of Header model objects
    if isinstance(hs, list):
        for h in hs:
            k = getattr(h, "key", None)
            v = getattr(h, "value", None)
            if k and v is not None:
                out.append({"key": k, "value": v})
        return out

    # Case 2: grammar gave us a single string
    if isinstance(hs, str):
        # split on semicolon or comma as separators
        parts = [p.strip() for p in re.split(r"[;,]", hs) if p.strip()]
        for p in parts:
            if ":" in p:
                k, v = p.split(":", 1)
                out.append({"key": k.strip(), "value": v.strip()})
        return out

    return out


def render_domain_files(model, templates_dir: Path, out_dir: Path):
    """
    Renders:
      - app/schemas/models.py
      - app/api/routers/*.py
    using templates in templates_dir.
    """
    env = Environment(
        loader=FileSystemLoader(str(templates_dir)),
        autoescape=select_autoescape(disabled_extensions=("jinja",)),
        trim_blocks=True,
        lstrip_blocks=True,
        undefined=StrictUndefined,
    )

    # -------- models --------
    entities_ctx = []
    for e in _entities(model):
        attrs_ctx = []
        for a in getattr(e, "attributes", []) or []:
            # computed if it has an Expr attached
            if hasattr(a, "expr") and a.expr is not None:
                attrs_ctx.append({
                    "name": a.name,
                    "kind": "computed",
                    "expr_raw": getattr(a, "expr_str", "") or "",
                    "py_type": "Any",
                })
            else:
                attrs_ctx.append({
                    "name": a.name,
                    "kind": "schema",
                    "py_type": _pyd_type_for(a),
                })
        entities_ctx.append({
            "name": e.name,
            "has_inputs": bool(getattr(e, "inputs", None)),
            "attributes": attrs_ctx,
        })

    models_tpl = env.get_template("models.jinja")
    models_out = out_dir / "app" / "schemas" / "models.py"
    models_out.parent.mkdir(parents=True, exist_ok=True)
    models_out.write_text(models_tpl.render(entities=entities_ctx), encoding="utf-8")

    # -------- routers --------
    routers_dir = out_dir / "app" / "api" / "routers"
    routers_dir.mkdir(parents=True, exist_ok=True)

    # 1) source-bound entities (REST vs WS)
    for e in _entities(model):
        src = getattr(e, "source", None)
        if not src:
            continue

        if src.__class__.__name__ == "RESTEndpoint":
            if (templates_dir / "router_entity_proxy.jinja").exists():
                # normalize headers for the template
                src.headers = _as_headers_list(src)
                tpl = env.get_template("router_entity_proxy.jinja")
                (routers_dir / f"{e.name.lower()}_source.py").write_text(
                    tpl.render(entity=e), encoding="utf-8"
                )

        elif src.__class__.__name__ == "WSEndpoint":
            if (templates_dir / "router_ws_listener.jinja").exists():
                # normalize headers for ws too (harmless if none)
                src.headers = _as_headers_list(src)
                subs = getattr(src, "subprotocols", None)
                try:
                    if subs and hasattr(subs, "items"):
                        src.subprotocols = list(subs.items)
                except Exception:
                    src.subprotocols = []
                tpl = env.get_template("router_ws_listener.jinja")
                (routers_dir / f"{e.name.lower()}_ws.py").write_text(
                    tpl.render(entity=e, ws=src), encoding="utf-8"
                )

    # 2) computed entity routers
    if (templates_dir / "router_proxy_computed.jinja").exists():
        tpl = env.get_template("router_proxy_computed.jinja")
        for e in _entities(model):
            inputs = []
            for inp in getattr(e, "inputs", []) or []:
                tgt = inp.target
                src = getattr(tgt, "source", None)
                headers = _as_headers_list(src) if src else []
                inputs.append({
                    "alias": inp.alias,
                    "target_name": tgt.name,
                    "target_source_url": getattr(src, "url", None) if src else None,
                    "target_headers": headers,   # ← NEW
                })

            computed_attrs = []
            for a in getattr(e, "attributes", []) or []:
                if hasattr(a, "expr") and a.expr is not None:
                    pyexpr = getattr(a, "_py", None) or ""
                    computed_attrs.append({"name": a.name, "pyexpr": pyexpr})

            if inputs or computed_attrs:
                (routers_dir / f"{e.name.lower()}_computed.py").write_text(
                    tpl.render(entity=e, inputs=inputs, computed_attrs=computed_attrs),
                    encoding="utf-8",
                )

    # 3) raw external REST endpoints
    if (templates_dir / "router_proxy.jinja").exists():
        tpl = env.get_template("router_proxy.jinja")
        for ep in _rest_endpoints(model):
            ep.headers = _as_headers_list(ep)  # ← add this
            (routers_dir / f"{ep.name.lower()}.py").write_text(
                tpl.render(endpoint=ep), encoding="utf-8"
            )

    # 4) WS listeners (standalone, not tied to entity)
    if (templates_dir / "router_ws_listener.jinja").exists():
        tpl = env.get_template("router_ws_listener.jinja")
        for ws in _ws_endpoints(model):
            ws.headers = _as_headers_list(ws)  # existing line

            # normalize subprotocols to a plain list[str]
            subs = getattr(ws, "subprotocols", None)
            try:
                # if it's a textX object with .items, pull them out
                if subs and hasattr(subs, "items"):
                    ws.subprotocols = list(subs.items)
                # if it's already a list (or None), leave it
            except Exception:
                ws.subprotocols = []

            (routers_dir / f"{ws.name.lower()}.py").write_text(
                tpl.render(ws=ws), encoding="utf-8"
            )


def _server_ctx(model):
    server = next(iter(get_children_of_type("Server", model)), None)
    if server is None:
        raise RuntimeError("No `Server` block found in model.")
    
    cors_val = getattr(server, "cors", None)
    
    if isinstance(cors_val, (list, tuple)) and len(cors_val) == 1:
        cors_val = cors_val[0]
        
    return {
        "server": {
            "name": server.name,
            "host": getattr(server, "host", "localhost"),
            "port": int(getattr(server, "port", 8080)),
            "cors": cors_val or "http://localhost:3000",
        }
    }
    
def _render_env_and_docker(ctx: dict, templates_dir: Path, out_dir: Path):
    env = Environment(
        loader=FileSystemLoader(str(templates_dir)),
        autoescape=select_autoescape(disabled_extensions=("jinja",)),
        trim_blocks=True,
        lstrip_blocks=True,
    )

    render_map = {
        ".env":               "env.jinja",
        "docker-compose.yml": "docker-compose.yaml.jinja",
        "Dockerfile":         "Dockerfile.jinja",
    }

    out_dir.mkdir(parents=True, exist_ok=True)
    for target, tpl_name in render_map.items():
        tpl = env.get_template(tpl_name)
        (out_dir / target).write_text(tpl.render(**ctx), encoding="utf-8")

def scaffold_backend_from_model(model, *,
                               base_backend_dir: Path,
                               templates_backend_dir: Path,
                               out_dir: Path) -> Path:
    """
    Copies the base backend scaffold and renders .env, docker-compose.yml, Dockerfile
    using values from the model's `Server` block.
    """
    ctx = _server_ctx(model)

    # 1) copy the base scaffold (app/, pyproject.toml, etc.)
    copytree(base_backend_dir, out_dir, dirs_exist_ok=True)

    # 2) render env + docker bits into out/
    _render_env_and_docker(ctx, templates_backend_dir, out_dir)

    return out_dir