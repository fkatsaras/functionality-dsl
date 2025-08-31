from __future__ import annotations
from pathlib import Path
from shutil import copytree
from jinja2 import Environment, FileSystemLoader, select_autoescape
from textx import get_children_of_type

def _entities(model):
    return list(get_children_of_type("Entity", model))

def _rest_endpoints(model):
    return list(get_children_of_type("RESTEndpoint", model))

def _ws_endpoints(model):
    return list(get_children_of_type("WSEndpoint", model))

def _pyd_type_for(attr):
    # very simple mapper; adapt as needed to your DSL types
    t = getattr(attr, "type", None)
    return {
        "int": "int",
        "float": "float",
        "string": "str",
        "bool": "bool",
        "datetime": "datetime",
    }.get((t or "").lower(), "Any")

def render_domain_files(model, templates_dir: Path, out_dir: Path):
    """
    Renders:
      - app/schemas/generated_models.py
      - app/api/routers/generated_*.py
    using templates in templates_dir.
    """
    env = Environment(
        loader=FileSystemLoader(str(templates_dir)),
        autoescape=select_autoescape(disabled_extensions=("jinja",)),
        trim_blocks=True,
        lstrip_blocks=True,
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
    models_out = out_dir / "app" / "schemas" / "generated_models.py"
    models_out.parent.mkdir(parents=True, exist_ok=True)
    models_out.write_text(models_tpl.render(entities=entities_ctx), encoding="utf-8")

    # -------- routers --------
    routers_dir = out_dir / "app" / "api" / "routers"
    routers_dir.mkdir(parents=True, exist_ok=True)

    # 1) direct REST proxies for source-bound entities
    if (templates_dir / "router_entity_proxy.jinja").exists():
        tpl = env.get_template("router_entity_proxy.jinja")
        for e in _entities(model):
            if getattr(e, "source", None):
                (routers_dir / f"generated_{e.name.lower()}_source.py").write_text(
                    tpl.render(entity=e), encoding="utf-8"
                )

    # 2) computed entity routers
    if (templates_dir / "router_proxy_computed.jinja").exists():
        tpl = env.get_template("router_proxy_computed.jinja")
        for e in _entities(model):
            inputs = []
            for inp in getattr(e, "inputs", []) or []:
                tgt = inp.target
                src = getattr(tgt, "source", None)
                inputs.append({
                    "alias": inp.alias,
                    "target_name": tgt.name,
                    "target_source_url": getattr(src, "url", None) if src else None,
                })

            computed_attrs = []
            for a in getattr(e, "attributes", []) or []:
                if hasattr(a, "expr") and a.expr is not None:
                    pyexpr = getattr(a, "_py", None) or ""
                    computed_attrs.append({"name": a.name, "pyexpr": pyexpr})

            if inputs or computed_attrs:
                (routers_dir / f"generated_{e.name.lower()}_computed.py").write_text(
                    tpl.render(entity=e, inputs=inputs, computed_attrs=computed_attrs),
                    encoding="utf-8",
                )

    # 3) raw external REST endpoints
    if (templates_dir / "router_proxy.jinja").exists():
        tpl = env.get_template("router_proxy.jinja")
        for ep in _rest_endpoints(model):
            (routers_dir / f"generated_external_{ep.name.lower()}.py").write_text(
                tpl.render(endpoint=ep), encoding="utf-8"
            )

    # 4) WS listeners
    if (templates_dir / "router_ws_listener.jinja").exists():
        tpl = env.get_template("router_ws_listener.jinja")
        for ws in _ws_endpoints(model):
            (routers_dir / f"generated_ws_{ws.name.lower()}.py").write_text(
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