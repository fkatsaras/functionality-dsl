from __future__ import annotations

import re
from pathlib import Path
from shutil import copytree
from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape
from textx import get_children_of_type


# ---------------- helpers ----------------

def _entities(model):
    return list(get_children_of_type("Entity", model))

def _pyd_type_for(attr):
    t = getattr(attr, "type", None)
    return {
        "int": "int",
        "float": "float",
        "string": "str",
        "bool": "bool",
        "datetime": "datetime",
    }.get((t or "").lower(), "Any")

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

    # -------- routers only (minimal backend) --------
    routers_dir = out_dir / "app" / "api" / "routers"
    routers_dir.mkdir(parents=True, exist_ok=True)

    # Templates in your current set
    tpl_router_rest = env.get_template("router_rest.jinja")
    tpl_router_ws   = env.get_template("router_ws.jinja")

    # -------- per-entity generation --------
    for e in _entities(model):
        src = getattr(e, "source", None)
        has_inputs = bool(getattr(e, "inputs", None))

        if has_inputs:
            # Computed streaming entity (requires at least one WS input)
            computed_attrs = [
                {"name": a.name, "pyexpr": getattr(a, "_py", "") or ""}
                for a in (getattr(e, "attributes", []) or [])
                if hasattr(a, "expr") and a.expr is not None
            ]

            ws_inputs = []
            for inp in (getattr(e, "inputs", []) or []):
                tgt = inp.target
                t_src = getattr(tgt, "source", None)
                if t_src and t_src.__class__.__name__ == "WSEndpoint":
                    _normalize_ws_source(t_src)
                    ws_inputs.append({
                        "alias": inp.alias,
                        "url": t_src.url,
                        # list of pairs is OK; template uses tojson -> list of lists works with websockets
                        "headers": [(h["key"], h["value"]) for h in _as_headers_list(t_src)],
                        "subprotocols": list(getattr(t_src, "subprotocols", []) or []),
                        "protocol": getattr(t_src, "protocol", "json") or "json",
                    })

            if not ws_inputs:
                # Minimal backend: we only support streaming computed entities if there is a WS input.
                # You can extend later to support REST-only computed via a REST router or a task.
                raise RuntimeError(
                    f"Computed entity '{e.name}' has no WS inputs; "
                    "the minimal backend only supports streaming computed entities with at least one WSEndpoint input."
                )

            (routers_dir / f"{e.name.lower()}_stream.py").write_text(
                tpl_router_ws.render(
                    entity=e,
                    computed_attrs=computed_attrs,
                    ws_inputs=ws_inputs,
                    ws_aliases=[wi["alias"] for wi in ws_inputs],
                ),
                encoding="utf-8",
            )
            continue

        # Non-computed entity
        if src and src.__class__.__name__ == "RESTEndpoint":
            src.headers = _as_headers_list(src)
            schema_attrs = _schema_attr_names(e)
            (routers_dir / f"{e.name.lower()}.py").write_text(
                tpl_router_rest.render(entity=e, schema_attrs=schema_attrs),
                encoding="utf-8",
            )

        elif src and src.__class__.__name__ == "WSEndpoint":
            # Raw WS entity: schema-only (no router in minimal backend)
            pass

        else:
            # Entity without a source: nothing to expose in this minimal backend
            pass


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
