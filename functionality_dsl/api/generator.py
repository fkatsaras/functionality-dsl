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

def _ws_endpoints(model):
    return list(get_children_of_type("WSEndpoint", model))

def _pyd_type_for(attr):
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
            # already list/None
            ws.subprotocols = subs or []
    except Exception:
        ws.subprotocols = []


# ---------------- code generation ----------------

def render_domain_files(model, templates_dir: Path, out_dir: Path):
    env = Environment(
        loader=FileSystemLoader(str(templates_dir)),
        autoescape=select_autoescape(disabled_extensions=("jinja",)),
        trim_blocks=True,
        lstrip_blocks=True,
        undefined=StrictUndefined,
    )

    # -------- models (to app/domain/models.py) --------
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

    # -------- directories --------
    routers_dir = out_dir / "app" / "api" / "routers"
    repos_dir   = out_dir / "app" / "infra" / "repositories"
    svcs_dir    = out_dir / "app" / "services"
    for d in (routers_dir, repos_dir, svcs_dir):
        d.mkdir(parents=True, exist_ok=True)

    # -------- load templates --------
    tpl_adapter_rest   = env.get_template("adapters.jinja")                    # REST entities
    tpl_adapter_ws     = env.get_template("adapters_ws_entity.jinja")          # WS entities (entity-named import)
    tpl_svc_entity     = env.get_template("service_entity.jinja")
    tpl_svc_computed   = env.get_template("service_computed.jinja")
    tpl_router_entity  = env.get_template("router_controller_entity.jinja")
    tpl_router_comp    = env.get_template("router_controller_computed.jinja")
    tpl_ws_listener    = env.get_template("router_ws_listener.jinja") if (templates_dir / "router_ws_listener.jinja").exists() else None
    tpl_ws_listener    = env.get_template("router_ws_listener.jinja") if (templates_dir / "router_ws_listener.jinja").exists() else None
    tpl_ws_comp_stream = env.get_template("router_ws_computed.jinja") if (templates_dir / "router_ws_computed.jinja").exists() else None

    # Remember WS endpoints already used by entities (to avoid duplicate standalone listeners)
    ws_nodes_used_by_entities = set()

    # -------- per-entity generation --------
    for e in _entities(model):
        src = getattr(e, "source", None)
        has_inputs = bool(getattr(e, "inputs", None))

        if has_inputs:
            # Computed entity
            inputs = [{"alias": inp.alias, "target_name": inp.target.name}
                      for inp in (getattr(e, "inputs", []) or [])]

            computed_attrs = [{"name": a.name, "pyexpr": getattr(a, "_py", "") or ""} \
                              for a in (getattr(e, "attributes", []) or []) \
                              if hasattr(a, "expr") and a.expr is not None]

            (svcs_dir / f"{e.name.lower()}_service.py").write_text(
                tpl_svc_computed.render(entity=e, inputs=inputs, computed_attrs=computed_attrs),
                encoding="utf-8",
            )
            (routers_dir / f"{e.name.lower()}.py").write_text(
                tpl_router_comp.render(entity=e, inputs=inputs),
                encoding="utf-8",
            )
        
            if tpl_ws_comp_stream:
                ws_inputs = []
                for inp in (getattr(e, "inputs", []) or []):
                    tgt = inp.target
                    src = getattr(tgt, "source", None)
                    if src and src.__class__.__name__ == "WSEndpoint":
                        ws_inputs.append({"alias": inp.alias, "target_name": tgt.name})
                if ws_inputs:
                    # Use the first WS-backed input as the trigger; import its listener module
                    ws_input_listener_module = ws_inputs[0]["target_name"].lower() + "_ws"
                    (routers_dir / f"{e.name.lower()}_stream.py").write_text(
                        tpl_ws_comp_stream.render(
                            entity=e,
                            inputs=inputs,  # pass all inputs; service will compute with all
                            ws_input_listener_module=ws_input_listener_module,
                        ),
                        encoding="utf-8",
                    )
            continue

        # Non-computed entity
        schema_attrs = [getattr(a, "name", None) for a in (getattr(e, "attributes", []) or [])]

        if src and src.__class__.__name__ == "RESTEndpoint":
            # REST entity: REST adapter + standard svc/router
            src.headers = _as_headers_list(src)
            (repos_dir / f"{e.name.lower()}_adapter.py").write_text(
                tpl_adapter_rest.render(entity=e, schema_attrs=schema_attrs),
                encoding="utf-8",
            )
            (svcs_dir / f"{e.name.lower()}_service.py").write_text(
                tpl_svc_entity.render(entity=e, schema_attrs=schema_attrs),
                encoding="utf-8",
            )
            (routers_dir / f"{e.name.lower()}.py").write_text(
                tpl_router_entity.render(entity=e),
                encoding="utf-8",
            )

        elif src and src.__class__.__name__ == "WSEndpoint":
            # WS entity: entity-named WS listener + WS adapter + standard svc/router
            if not tpl_ws_listener:
                raise RuntimeError("router_ws_listener.jinja not found, but a WSEntity is present.")
            _normalize_ws_source(src)
            ws_nodes_used_by_entities.add(src)

            # listener named <entity>_ws.py to avoid collisions and match adapter import
            (routers_dir / f"{e.name.lower()}_ws.py").write_text(
                tpl_ws_listener.render(entity=e, ws=src),
                encoding="utf-8",
            )
            (repos_dir / f"{e.name.lower()}_adapter.py").write_text(
                tpl_adapter_ws.render(entity=e, schema_attrs=schema_attrs),
                encoding="utf-8",
            )
            (svcs_dir / f"{e.name.lower()}_service.py").write_text(
                tpl_svc_entity.render(entity=e, schema_attrs=schema_attrs),
                encoding="utf-8",
            )
            (routers_dir / f"{e.name.lower()}.py").write_text(
                tpl_router_entity.render(entity=e),
                encoding="utf-8",
            )

        else:
            # Entity without a source (still generate trivial svc/router)
            (svcs_dir / f"{e.name.lower()}_service.py").write_text(
                tpl_svc_entity.render(entity=e, schema_attrs=schema_attrs),
                encoding="utf-8",
            )
            (routers_dir / f"{e.name.lower()}.py").write_text(
                tpl_router_entity.render(entity=e),
                encoding="utf-8",
            )

    # -------- Standalone WS listeners (for WS endpoints not bound to any entity) --------
    if tpl_ws_listener:
        for ws in _ws_endpoints(model):
            if ws in ws_nodes_used_by_entities:
                continue  # already generated via an entity
            _normalize_ws_source(ws)
            (routers_dir / f"{ws.name.lower()}.py").write_text(
                tpl_ws_listener.render(ws=ws),
                encoding="utf-8",
            )


# ---------------- server / env / docker rendering ----------------

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
    copytree(base_backend_dir, out_dir, dirs_exist_ok=True)
    _render_env_and_docker(ctx, templates_backend_dir, out_dir)
    return out_dir
