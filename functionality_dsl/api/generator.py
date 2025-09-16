from __future__ import annotations

import re
from pathlib import Path
from shutil import copytree
from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape
from textx import get_children_of_type


# ---------------- helpers ----------------

def _entities(model):
    return list(get_children_of_type("Entity", model))

def _rest_endpoints(model):
    return list(get_children_of_type("RESTEndpoint", model))

def _pyd_type_for(attr):
    t = getattr(attr, "type", None)
    
    base = {
        "int": "int",
        "float": "float",
        "string": "str",
        "bool": "bool",
        "datetime": "datetime",
    }.get((t or "").lower(), "Any")
    
    # If its an optional field, mark the model attr
    if getattr(attr, "optional", False):
        return f"Optional[{base}]"
    return base

def _schema_attr_names(ent) -> list[str]:
    """Return schema (non-computed) attribute names for an entity."""
    names: list[str] = []
    for a in (getattr(ent, "attributes", []) or []):
        if not (hasattr(a, "expr") and a.expr is not None):
            names.append(getattr(a, "name"))
    return names

def _as_headers_list(obj):
    """
    Normalize .headers from RESTEndpoint/WSEndpoint to list[{'key','value'}].
    Accepts:
      - None
      - list of Header nodes with .key/.value
      - single string like "Key: Val; Another: Foo"
    """
    hs = getattr(obj, "headers", None)
    out = []
    if not hs:
        return out

    if isinstance(hs, list):
        for h in hs:
            k = getattr(h, "key", None)
            v = getattr(h, "value", None)
            if k and v is not None:
                out.append({"key": k, "value": v})
        return out

    if isinstance(hs, str):
        parts = [p.strip() for p in re.split(r"[;,]", hs) if p.strip()]
        for p in parts:
            if ":" in p:
                k, v = p.split(":", 1)
                out.append({"key": k.strip(), "value": v.strip()})
        return out

    return out

def _normalize_ws_source(ws):
    """
    Mutate a WSEndpoint so templates have simple, JSON-serializable attrs.
    - headers -> list of {'key','value'}
    - subprotocols -> [] or list[str]
    """
    if ws is None:
        return
    ws.headers = _as_headers_list(ws)
    subs = getattr(ws, "subprotocols", None)
    try:
        if subs and hasattr(subs, "items"):
            ws.subprotocols = list(subs.items)
        else:
            ws.subprotocols = subs or []
    except Exception:
        ws.subprotocols = []


def render_domain_files(model, templates_dir: Path, out_dir: Path):
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
    models_out = out_dir / "app" / "domain" / "models.py"
    models_out.parent.mkdir(parents=True, exist_ok=True)
    models_out.write_text(models_tpl.render(entities=entities_ctx), encoding="utf-8")

    # -------- routers --------
    routers_dir = out_dir / "app" / "api" / "routers"
    routers_dir.mkdir(parents=True, exist_ok=True)

    # ---- Load templates
    tpl_router_entity_rest  = env.get_template("router_rest.jinja")      # RAW REST entity
    tpl_router_computed_rest = env.get_template("router_computed_rest.jinja")   # COMPUTED (no WS)
    tpl_router_ws           = env.get_template("router_ws.jinja")               # COMPUTED (with WS)
    tpl_router_action = env.get_template("router_action.jinja")         # POST / PUT 

    # -------- per-entity generation --------
    for e in _entities(model):
        src = getattr(e, "source", None)
        has_inputs = bool(getattr(e, "inputs", None))

        if has_inputs:
            # Computed entity: decide WS vs REST
            computed_attrs = [
                {"name": a.name, "pyexpr": getattr(a, "_py", "") or ""}
                for a in (getattr(e, "attributes", []) or [])
                if hasattr(a, "expr") and a.expr is not None
            ]

            ws_inputs = []
            rest_inputs = []

            for inp in (getattr(e, "inputs", []) or []):
                tgt = inp.target
                t_src = getattr(tgt, "source", None)

                if t_src and t_src.__class__.__name__ == "WSEndpoint":
                    _normalize_ws_source(t_src)
                    ws_inputs.append({
                        "alias": inp.alias,
                        "url": t_src.url,
                        "headers": [(h["key"], h["value"]) for h in _as_headers_list(t_src)],
                        "subprotocols": list(getattr(t_src, "subprotocols", []) or []),
                        "protocol": getattr(t_src, "protocol", "json") or "json",
                    })
                elif t_src and t_src.__class__.__name__ == "RESTEndpoint":
                    rest_inputs.append({
                        "alias": inp.alias,
                        "target_name": tgt.name,
                        "url": t_src.url,
                        "headers": _as_headers_list(t_src),
                        "fields": _schema_attr_names(tgt),
                    })

            if ws_inputs:
                # STREAMING computed
                (routers_dir / f"{e.name.lower()}_stream.py").write_text(
                    tpl_router_ws.render(
                        entity=e,
                        computed_attrs=computed_attrs,
                        ws_inputs=ws_inputs,
                        ws_aliases=[wi["alias"] for wi in ws_inputs],
                    ),
                    encoding="utf-8",
                )
            else:
                # REST-ONLY computed (simple GET that computes)
                (routers_dir / f"{e.name.lower()}.py").write_text(
                    tpl_router_computed_rest.render(
                        entity=e,
                        computed_attrs=computed_attrs,
                        rest_inputs=rest_inputs,
                    ),
                    encoding="utf-8",
                )
            continue
        
        # -------- Passthrough routers for REST actions (POST/PUT/PATCH/DELETE) --------
        for ep in _rest_endpoints(model):
            verb = (getattr(ep, "verb", "GET") or "GET").upper()
            if verb in {"POST", "PUT", "PATCH", "DELETE"}:
                ep.headers = _as_headers_list(ep)
                (routers_dir / f"{ep.name.lower()}_action.py").write_text(
                    tpl_router_action.render(endpoint=ep),
                    encoding="utf-8",
                )

        # Non-computed entity
        if src and src.__class__.__name__ == "RESTEndpoint":
            # RAW REST entity - simple pass-through list
            src.headers = _as_headers_list(src)
            schema_attrs = _schema_attr_names(e)
            (routers_dir / f"{e.name.lower()}.py").write_text(
                tpl_router_entity_rest.render(entity=e, schema_attrs=schema_attrs),
                encoding="utf-8",
            )

        elif src and src.__class__.__name__ == "WSEndpoint":
            # Raw WS entity: no router in minimal backend (we bind to computed)
            pass

        else:
            # Entity without a source: nothing to expose here
            pass


# ---------------- server / env / docker rendering ----------------

def _server_ctx(model):
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
        
    
    return {
        "server": {
            "name": s.name,
            "host": getattr(s, "host", "localhost"),
            "port": int(getattr(s, "port", 8080)),
            "cors": cors_val or "http://localhost:3000",
            "env": env_val,
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

def scaffold_backend_from_model(model, base_backend_dir: Path, templates_backend_dir: Path, out_dir: Path) -> Path:
    """
    Copies the base backend scaffold and renders .env, docker-compose.yml, Dockerfile
    using values from the model's `Server` block.
    """
    ctx = _server_ctx(model)
    copytree(base_backend_dir, out_dir, dirs_exist_ok=True)
    _render_env_and_docker(ctx, templates_backend_dir, out_dir)
    return out_dir
