# generator.py
from __future__ import annotations

import re
from pathlib import Path
from shutil import copytree
from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape
from textx import get_children_of_type


# ---------------- helpers ----------------

def _entities(model):
    return list(get_children_of_type("Entity", model))

def _internal_rest_endpoints(model):
    return list(get_children_of_type("InternalRESTEndpoint", model))

def _internal_ws_endpoints(model):
    return list(get_children_of_type("InternalWSEndpoint", model))

def _pyd_type_for(attr):
    t = getattr(attr, "type", None)

    base = {
        "int": "int",
        "float": "float",
        "number": "float",
        "string": "str",
        "bool": "bool",
        "datetime": "datetime",
        "uuid": "str",
        "dict": "dict",
        "list": "list",
    }.get((t or "").lower(), "Any")

    # If its an optional field, mark the model attr
    if getattr(attr, "optional", False):
        return f"Optional[{base}]"
    return base

def _schema_attr_names(ent) -> list[str]:
    print(f"[DEBUG] _schema_attr_names called with: {type(ent)} - {ent}")
    
    names: list[str] = []
    attributes = getattr(ent, "attributes", []) or []
    print(f"[DEBUG] Found {len(attributes)} attributes: {attributes}")
    
    for i, a in enumerate(attributes):
        print(f"[DEBUG] Processing attribute {i}: type={type(a)}, value={a}")
        print(f"[DEBUG] Attribute dir: {dir(a)}")
        
        # Check if it has expr
        has_expr = hasattr(a, "expr")
        expr_value = getattr(a, "expr", None) if has_expr else None
        print(f"[DEBUG] has_expr={has_expr}, expr_value={expr_value}")
        
        # computed if it has an 'expr' attribute set
        if not (hasattr(a, "expr") and a.expr is not None):
            print(f"[DEBUG] This is a schema attribute, getting name...")
            
            # Debug the name access
            if hasattr(a, "name"):
                attr_name = getattr(a, "name")
                print(f"[DEBUG] Attribute name: {attr_name}")
                names.append(attr_name)
            else:
                print(f"[DEBUG] ERROR: Attribute has no 'name' attribute!")
                print(f"[DEBUG] Available attributes: {dir(a)}")
        else:
            print(f"[DEBUG] This is a computed attribute, skipping...")
    
    print(f"[DEBUG] Final names list: {names}")
    return names

def _as_headers_list(obj):
    """
    Normalize .headers from ExternalREST/ExternalWS to list[{'key','value'}].
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
    Mutate a ExternalWSEndpoint so templates have simple, JSON-serializable attrs.
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


# ---------------- route helpers ----------------

def _default_rest_prefix(endpoint, entity) -> str:
    """
    Default REST router prefix for internal endpoints.
    """
    path = getattr(endpoint, "path", None)
    if isinstance(path, str) and path.strip():
        return path
    return f"/api/{getattr(endpoint, 'name', getattr(entity, 'name', 'endpoint')).lower()}"

def _default_ws_prefix(endpoint, entity) -> str:
    """
    Default WS router prefix for internal endpoints.
    """
    path = getattr(endpoint, "path", None)
    if isinstance(path, str) and path.strip():
        return path
    # follow previous convention '/api/entities/<name>/stream'
    return f"/api/{getattr(endpoint, 'name', getattr(entity, 'name', 'endpoint')).lower()}"


# ---------------- domain models ----------------

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
                    "py_type": _pyd_type_for(a),
                })
            else:
                attrs_ctx.append({
                    "name": a.name,
                    "kind": "schema",
                    "py_type": _pyd_type_for(a),
                })
        entities_ctx.append({
            "name": e.name,
            "has_parents": bool(getattr(e, "parents", None)),
            "attributes": attrs_ctx,
        })

    models_tpl = env.get_template("models.jinja")
    models_out = out_dir / "app" / "domain" / "models.py"
    models_out.parent.mkdir(parents=True, exist_ok=True)
    models_out.write_text(models_tpl.render(entities=entities_ctx), encoding="utf-8")

    # -------- routers (INTERNAL ONLY) --------
    routers_dir = out_dir / "app" / "api" / "routers"
    routers_dir.mkdir(parents=True, exist_ok=True)

    # ---- Load templates
    tpl_router_entity_rest   = env.get_template("router_rest.jinja")             # RAW REST entity via internal
    tpl_router_computed_rest = env.get_template("router_computed_rest.jinja")    # COMPUTED (no WS) via internal
    tpl_router_ws            = env.get_template("router_ws.jinja")               # COMPUTED/WS via internal

    # -------- per-internal-endpoint generation --------

    # INTERNAL REST endpoints
    for iep in _internal_rest_endpoints(model):
        ent = getattr(iep, "entity")
        
        # DEBUG: Print entity details
        print(f"[DEBUG] Entity type: {type(ent)}")
        print(f"[DEBUG] Entity: {ent}")
        print(f"[DEBUG] Entity dir: {dir(ent)}")
        
        if hasattr(ent, "attributes"):
            print(f"[DEBUG] Entity.attributes type: {type(ent.attributes)}")
            print(f"[DEBUG] Entity.attributes: {ent.attributes}")
        else:
            print(f"[DEBUG] Entity has no 'attributes' attribute!")
            if isinstance(ent, dict):
                print(f"[DEBUG] Entity dict keys: {ent.keys()}")
        
        route_prefix = _default_rest_prefix(iep, ent)
        # ... rest of the code

        has_parents = bool(getattr(ent, "parents", None))
        print(f"[GEN/REST] endpoint={iep.name} entity={ent.name} has_parents={has_parents}")

        if has_parents:
            computed_attrs = [
                {"name": a.name, "pyexpr": getattr(a, "_py", "") or ""}
                for a in (getattr(ent, "attributes", []) or [])
                if hasattr(a, "expr") and a.expr is not None
            ]

            ws_inputs = []
            rest_inputs = []
            computed_parents = []  # Add this new list

            
            for parent in getattr(ent, "parents", []) or []:
                t_src = getattr(parent, "source", None)
                # DEBUG: Print parent details
                print(f"[DEBUG] Parent type: {type(parent)}")
                print(f"[DEBUG] Parent: {parent}")
                print(f"[DEBUG] Parent dir: {dir(parent)}")
                print(f"[DEBUG] Parent name: {getattr(parent, 'name', 'NO_NAME')}")
                print(f"[GEN/PARENT] {ent.name} <- {parent.name} src={t_src.__class__.__name__ if t_src else None}")
                if hasattr(parent, "attributes"):
                    print(f"[DEBUG] Parent.attributes: {parent.attributes}")
                else:
                    print(f"[DEBUG] Parent has no 'attributes' attribute!")

                if t_src and t_src.__class__.__name__ == "ExternalWSEndpoint":
                    _normalize_ws_source(t_src)
                    ws_inputs.append({
                        "name": parent.name,
                        "url": t_src.url,
                        "headers": [(h["key"], h["value"]) for h in _as_headers_list(t_src)],
                        "subprotocols": list(getattr(t_src, "subprotocols", []) or []),
                        "protocol": getattr(t_src, "protocol", "json") or "json",
                    })
                elif t_src and t_src.__class__.__name__ == "ExternalRESTEndpoint":
                    # External REST source - parent is a source entity
                    rest_inputs.append({
                        "name": parent.name,
                        "url": t_src.url,
                        "headers": _as_headers_list(t_src),
                        "fields": _schema_attr_names(parent),
                        "method": (getattr(t_src, "verb", "GET") or "GET").upper(),  # NEW
                    })
                else:
                    # No external source - this parent is a computed entity
                    # Find the corresponding internal endpoint for this parent
                    parent_endpoint_path = None

                    # Look for the internal endpoint that serves this parent entity
                    for other_iep in _internal_rest_endpoints(model):
                        if getattr(other_iep, "entity").name == parent.name:
                            parent_endpoint_path = _default_rest_prefix(other_iep, getattr(other_iep, "entity"))
                            break
                        
                    if parent_endpoint_path:
                        computed_parents.append({
                            "name": parent.name,
                            "endpoint": parent_endpoint_path
                        })
                        print(f"[GEN/COMPUTED_DEP] {ent.name} <- {parent.name} via {parent_endpoint_path}")
                    else:
                        print(f"[GEN/WARNING] Could not find endpoint for computed parent {parent.name}")
                        
            attrs_ctx = []
            for a in getattr(ent, "attributes", []) or []:
                if hasattr(a, "expr") and a.expr is not None:
                    attrs_ctx.append({
                        "name": a.name,
                        "kind": "computed",
                        "expr_raw": getattr(a, "expr_str", "") or "",
                        "py_type": _pyd_type_for(a),
                    })
                else:
                    attrs_ctx.append({
                        "name": a.name,
                        "kind": "schema",
                        "py_type": _pyd_type_for(a),
                    })

            entity_info = {"name": ent.name}
            entity_attributes = getattr(ent, "attributes", []) or []
            if entity_attributes:
                entity_info["attributes"] = [{"name": getattr(attr, "name")} for attr in entity_attributes]
            
            (routers_dir / f"{iep.name.lower()}.py").write_text(
                tpl_router_computed_rest.render(
                    endpoint={"name": iep.name, "summary": getattr(iep, "summary", None)},
                    entity=ent,   # ← keep it as the textX Entity object
                    computed_attrs=computed_attrs,
                    rest_inputs=rest_inputs,
                    computed_parents=computed_parents,
                    route_prefix=route_prefix,
                ),
                encoding="utf-8",
            )
            continue

        # Non-computed entity (RAW, ExternalREST)
        src = getattr(ent, "source", None)
        if src and src.__class__.__name__ == "ExternalRESTEndpoint":
            src.headers = _as_headers_list(src)
            schema_attrs = _schema_attr_names(ent)
        
            # If only one attribute, we'll wrap the payload under it.
            wrapper_attr = schema_attrs[0] if len(schema_attrs) == 1 else None
        
            (routers_dir / f"{iep.name.lower()}.py").write_text(
                tpl_router_entity_rest.render(
                    endpoint={"name": iep.name, "summary": getattr(iep, "summary", None)},
                    entity={"name": ent.name, "source": src},
                    schema_attrs=schema_attrs,
                    wrapper_attr=wrapper_attr,    # NEW
                    route_prefix=route_prefix,
                ),
                encoding="utf-8",
            )
        
        else:
            continue
 
    # INTERNAL WS endpoints
    for iwep in _internal_ws_endpoints(model):
        ent = getattr(iwep, "entity")
        route_prefix = _default_ws_prefix(iwep, ent)
 
        computed_attrs = [
            {"name": a.name, "pyexpr": getattr(a, "_py", "") or ""}
            for a in (getattr(ent, "attributes", []) or [])
            if hasattr(a, "expr") and a.expr is not None
        ]
 
        ws_inputs = []
        for parent in getattr(ent, "parents", []) or []:
            t_src = getattr(parent, "source", None)
            if t_src and t_src.__class__.__name__ == "ExternalWSEndpoint":
                _normalize_ws_source(t_src)
                ws_inputs.append({
                    "name": parent.name,
                    "url": t_src.url,
                    "headers": [(h["key"], h["value"]) for h in _as_headers_list(t_src)],
                    "subprotocols": list(getattr(t_src, "subprotocols", []) or []),
                    "protocol": getattr(t_src, "protocol", "json") or "json",
                })
 
        if not ws_inputs and getattr(ent, "_source_kind", None) != "external-ws":
            continue
 
        (routers_dir / f"{iwep.name.lower()}_stream.py").write_text(
            tpl_router_ws.render(
                endpoint=iwep,
                entity=ent,
                computed_attrs=computed_attrs,
                ws_inputs=ws_inputs,
                ws_aliases=[wi["name"] for wi in ws_inputs],
                route_prefix=route_prefix,
            ),
            encoding="utf-8",
        )



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
