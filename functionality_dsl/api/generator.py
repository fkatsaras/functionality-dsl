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
    """Return schema (non-computed) attribute names for an entity."""
    names: list[str] = []
    for a in (getattr(ent, "attributes", []) or []):
        # computed if it has an 'expr' attribute set
        if not (hasattr(a, "expr") and a.expr is not None):
            names.append(getattr(a, "name"))
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
            "has_inputs": bool(getattr(e, "inputs", None)),
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
        route_prefix = _default_rest_prefix(iep, ent)

        has_inputs = bool(getattr(ent, "inputs", None))
        if has_inputs:
            # Computed entity: decide REST inputs vs WS-only inputs to compute
            computed_attrs = [
                {"name": a.name, "pyexpr": getattr(a, "_py", "") or ""}
                for a in (getattr(ent, "attributes", []) or [])
                if hasattr(a, "expr") and a.expr is not None
            ]

            ws_inputs = []
            rest_inputs = []

            for inp in (getattr(ent, "inputs", []) or []):
                tgt = inp.target
                t_src = getattr(tgt, "source", None)

                if t_src and t_src.__class__.__name__ == "ExternalWSEndpoint":
                    _normalize_ws_source(t_src)
                    ws_inputs.append({
                        "alias": inp.alias,
                        "url": t_src.url,
                        "headers": [(h["key"], h["value"]) for h in _as_headers_list(t_src)],
                        "subprotocols": list(getattr(t_src, "subprotocols", []) or []),
                        "protocol": getattr(t_src, "protocol", "json") or "json",
                    })
                elif t_src and t_src.__class__.__name__ == "ExternalRESTEndpoint":
                    rest_inputs.append({
                        "alias": inp.alias,
                        "target_name": tgt.name,
                        "url": t_src.url,
                        "headers": _as_headers_list(t_src),
                        "fields": _schema_attr_names(tgt),
                    })

            if ws_inputs:
                # If any WS input exists, we *could* stream; but this is the REST internal endpoint.
                # Keep REST-ONLY computed behavior: fetch from REST inputs only; WS inputs are ignored here.
                pass

            # REST-ONLY computed (simple GET that computes)
            (routers_dir / f"{iep.name.lower()}.py").write_text(
                tpl_router_computed_rest.render(
                    endpoint=iep,
                    entity=ent,
                    computed_attrs=computed_attrs,
                    rest_inputs=rest_inputs,
                    route_prefix=route_prefix,
                ),
                encoding="utf-8",
            )
            continue

        # Non-computed entity
        src = getattr(ent, "source", None)
        if src and src.__class__.__name__ == "ExternalRESTEndpoint":
            # RAW REST entity - simple pass-through list
            src.headers = _as_headers_list(src)
            schema_attrs = _schema_attr_names(ent)
            (routers_dir / f"{iep.name.lower()}.py").write_text(
                tpl_router_entity_rest.render(
                    endpoint=iep,
                    entity=ent,
                    schema_attrs=schema_attrs,
                    route_prefix=route_prefix,
                ),
                encoding="utf-8",
            )
        else:
            # source is WS or None: cannot expose as REST list without a polling adapter
            # choose to skip for now
            continue

    # INTERNAL WS endpoints
    for iwep in _internal_ws_endpoints(model):
        ent = getattr(iwep, "entity")
        route_prefix = _default_ws_prefix(iwep, ent)

        # Build inputs for WS router: we only stream if there is at least one WS upstream
        computed_attrs = [
            {"name": a.name, "pyexpr": getattr(a, "_py", "") or ""}
            for a in (getattr(ent, "attributes", []) or [])
            if hasattr(a, "expr") and a.expr is not None
        ]

        ws_inputs = []
        for inp in (getattr(ent, "inputs", []) or []):
            tgt = inp.target
            t_src = getattr(tgt, "source", None)
            if t_src and t_src.__class__.__name__ == "ExternalWSEndpoint":
                _normalize_ws_source(t_src)
                ws_inputs.append({
                    "alias": inp.alias,
                    "url": t_src.url,
                    "headers": [(h["key"], h["value"]) for h in _as_headers_list(t_src)],
                    "subprotocols": list(getattr(t_src, "subprotocols", []) or []),
                    "protocol": getattr(t_src, "protocol", "json") or "json",
                })

        if not ws_inputs and getattr(ent, "_source_kind", None) != "external-ws":
            # No WS inputs: cannot meaningfully stream; skip.
            continue

        (routers_dir / f"{iwep.name.lower()}_stream.py").write_text(
            tpl_router_ws.render(
                endpoint=iwep,
                entity=ent,
                computed_attrs=computed_attrs,
                ws_inputs=ws_inputs,
                ws_aliases=[wi["alias"] for wi in ws_inputs],
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
