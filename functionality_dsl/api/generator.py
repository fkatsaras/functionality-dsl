# generator.py
from __future__ import annotations

from collections import deque
import re
from pathlib import Path
from shutil import copytree
from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape
from textx import get_children_of_type

from functionality_dsl.lib.computed import compile_expr_to_python


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

    if getattr(attr, "optional", False):
        return f"Optional[{base}]"
    return base

def _as_headers_list(obj):
    """Normalize .headers from ExternalREST/ExternalWS to list of {key,value} dicts."""
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
    """Mutate ExternalWSEndpoint so templates have JSON-serializable attrs."""
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
        
# --------------- Mutation flow helpers ---------

def _distance_up(from_node, to_ancestor) -> int | None:
    """edges from from_node up through parents to to_ancestor (if reachable)."""
    q = deque([(from_node, 0)])
    seen = set()
    while q:
        cur, d = q.popleft()
        if id(cur) in seen:
            continue
        seen.add(id(cur))
        if cur is to_ancestor:
            return d
        for p in getattr(cur, "parents", []) or []:
            q.append((p, d + 1))
    return None

def _find_downstream_terminal_entity(ent, model):
    """
    Return the nearest descendant entity (fewest edges upward from it to 'ent')
    that has a bound external target. If none, return None.
    """
    candidates = []
    for e2 in get_children_of_type("Entity", model):
        if getattr(e2, "target", None) is None:
            continue
        dist = _distance_up(e2, ent)
        if dist is not None:
            candidates.append((dist, e2))
    if not candidates:
        return None
    candidates.sort(key=lambda t: t[0])
    return candidates[0][1]

def _is_ancestor(ancestor, node) -> bool:
    return _distance_up(node, ancestor) is not None

def _collect_chain(ent_start, ent_terminal, model):
    """
    All entities E such that ent_start is an ancestor of E and
    E is an ancestor of ent_terminal, ordered by distance from ent_start (parents-first).
    """
    all_entities = get_children_of_type("Entity", model)
    between = [E for E in all_entities if _is_ancestor(ent_start, E) and _is_ancestor(E, ent_terminal)]
    between.sort(key=lambda E: _distance_up(E, ent_start) or 10**9)
    return between


# ---------------- route helpers ----------------

def _default_rest_prefix(endpoint, entity) -> str:
    path = getattr(endpoint, "path", None)
    if isinstance(path, str) and path.strip():
        return path
    return f"/api/{getattr(endpoint, 'name', getattr(entity, 'name', 'endpoint')).lower()}"

def _default_ws_prefix(endpoint, entity) -> str:
    path = getattr(endpoint, "path", None)
    if isinstance(path, str) and path.strip():
        return path
    return f"/api/{getattr(endpoint, 'name', getattr(entity, 'name', 'endpoint')).lower()}"


# ---------------- domain models ----------------

def render_domain_files(model, templates_dir: Path, out_dir: Path):
    
    all_sources = []
    for src in get_children_of_type("ExternalRESTEndpoint", model):
        all_sources.append(src.name)
    for src in get_children_of_type("ExternalWSEndpoint", model):
        all_sources.append(src.name)
        
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

    # -------- routers --------
    routers_dir = out_dir / "app" / "api" / "routers"
    routers_dir.mkdir(parents=True, exist_ok=True)

    tpl_router_query_rest = env.get_template("router_query_rest.jinja")
    tpl_router_mutation_rest = env.get_template("router_mutation_rest.jinja")
    tpl_router_ws = env.get_template("router_ws.jinja")

    # -------- per-internal-endpoint generation --------

    # INTERNAL REST endpoints
    for iep in _internal_rest_endpoints(model):
        ent = getattr(iep, "entity")
        route_prefix = _default_rest_prefix(iep, ent)
        verb = getattr(iep, "verb", "GET").upper()
    
        # Common accumulators
        computed_attrs = []
        rest_inputs = []
        computed_parents = []
    
        ent_src = getattr(ent, "source", None)
        ent_has_ext_rest = ent_src and ent_src.__class__.__name__ == "ExternalRESTEndpoint"
    
        # === A) Entity has its own ExternalREST source
        if ent_has_ext_rest:
            ent_attrs = []
            for a in (getattr(ent, "attributes", []) or []):
                if hasattr(a, "expr") and a.expr is not None:
                    raw = compile_expr_to_python(a.expr, context="entity", known_sources=all_sources)
                else:
                    raw = f"{ent_src.name}"
                ent_attrs.append({"name": a.name, "pyexpr": raw})
    
            rest_inputs.append({
                "entity": ent.name,           # <-- bind into ctx under entity name
                "alias":  ent_src.name,       # <-- evaluate exprs against this alias
                "url": ent_src.url,
                "headers": _as_headers_list(ent_src),
                "method": (getattr(ent_src, "verb", "GET") or "GET").upper(),
                "attrs": ent_attrs,
            })
    
        # === B) Parents
        for parent in getattr(ent, "parents", []) or []:
            if isinstance(parent, dict):
                continue  # defensive: never treat pre-normalized dicts as Entity
            
            print(f"[DEBUG] Entity={parent.name} source={parent.source} type={type(parent.source)}")
            if isinstance(parent.source, list):
                for idx, s in enumerate(parent.source):
                    print(f"[DEBUG]   source[{idx}] -> {s} ({type(s)})")
            
            t_src = getattr(parent, "source", None)
            print(f"[GEN/PARENT] {ent.name} <- {getattr(parent, 'name', str(parent))} src={t_src.__class__.__name__ if t_src else None}")
        
            if t_src and t_src.__class__.__name__ == "ExternalRESTEndpoint":
                parent_attrs = []
                for a in (getattr(parent, "attributes", []) or []):
                    if hasattr(a, "expr") and a.expr is not None:
                        py = compile_expr_to_python(a.expr, context="entity", known_sources=all_sources)
                        print(f"[GEN/PARENT_ATTR] {parent.name}.{a.name} expr compiled to: {py}")
                    else:
                        # FIXED: Default to full source payload
                        py = f"{t_src.name}"
                        print(f"[GEN/PARENT_ATTR] {parent.name}.{a.name} defaulting to: {py}")
                    parent_attrs.append({"name": a.name, "pyexpr": py})
        
                print(f"[GEN/REST_INPUT] {parent.name} attrs: {parent_attrs}")
        
                rest_inputs.append({
                    "entity": parent.name,
                    "alias":  t_src.name,
                    "url": t_src.url,
                    "headers": _as_headers_list(t_src),
                    "method": (getattr(t_src, "verb", "GET") or "GET").upper(),
                    "attrs": parent_attrs,
                })
            else:
                # Computed parent (internal endpoint)
                parent_endpoint_path = None
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
        
        # === C) Populate computed attrs for entities WITHOUT an external REST source
        if not ent_has_ext_rest:
            for a in (getattr(ent, "attributes", []) or []):
                if hasattr(a, "expr") and a.expr is not None:
                    py_code = compile_expr_to_python(a.expr, context="entity", known_sources=all_sources)
                    computed_attrs.append({"name": a.name, "pyexpr": py_code})
    
        # ------------------------------------------------------
        # Generate the router depending on verb
        # ------------------------------------------------------
        if verb == "GET":
            # Query router
            (routers_dir / f"{iep.name.lower()}.py").write_text(
                tpl_router_query_rest.render(
                    endpoint={"name": iep.name, "summary": getattr(iep, "summary", None)},
                    entity=ent,
                    computed_attrs=computed_attrs,
                    rest_inputs=rest_inputs,
                    computed_parents=computed_parents,
                    route_prefix=route_prefix,
                ),
                encoding="utf-8",
            )
        else:
            # Mutation router → requires a target (usually ExternalREST)
            # --- choose terminal entity ---
            terminal_entity = _find_downstream_terminal_entity(ent, model) or ent
            
            # --- build the chain (current → ... → terminal) ---
            chain_entities = _collect_chain(ent, terminal_entity, model)
            
            # compile chain attrs
            compiled_chain = []
            for E in chain_entities:
                attrs = []
                for a in (getattr(E, "attributes", []) or []):
                    if hasattr(a, "expr") and a.expr is not None:
                        py_code = compile_expr_to_python(a.expr, context="entity", known_sources=all_sources)
                        attrs.append({"name": a.name, "pyexpr": py_code})
                compiled_chain.append({"name": E.name, "attrs": attrs})
            
            # target (if any)
            tgt = getattr(terminal_entity, "target", None)
            target = None
            if tgt:
                target = {
                    "name": tgt.name,
                    "url": tgt.url,
                    "method": getattr(tgt, "verb", verb).upper(),
                    "headers": _as_headers_list(tgt),
                }
            
            # render
            (routers_dir / f"{iep.name.lower()}.py").write_text(
                tpl_router_mutation_rest.render(
                    endpoint={"name": iep.name, "summary": getattr(iep, "summary", None)},
                    entity=ent,                         # InternalREST-bound entity
                    terminal=terminal_entity,           # terminal entity (bound to ExternalREST)
                    target=target,                      # None → echo; else forward
                    rest_inputs=rest_inputs,
                    computed_parents=computed_parents,
                    route_prefix=route_prefix,
                    compiled_chain=compiled_chain,      # << pass the whole chain
                ),
                encoding="utf-8",
            )


    # INTERNAL WS endpoints
    for iwep in _internal_ws_endpoints(model):
        ent = getattr(iwep, "entity")
        route_prefix = _default_ws_prefix(iwep, ent)

        computed_attrs = []
        # IMPORTANT: WS router evaluates computed attrs with {"ctx": ctx}
        # so we must compile against "ctx" here, regardless of sources.
        for a in (getattr(ent, "attributes", []) or []):
            if hasattr(a, "expr") and a.expr is not None:
                py_code = compile_expr_to_python(a.expr, context="ctx", known_sources=all_sources + [ent.name] )
                computed_attrs.append({"name": a.name, "pyexpr": py_code})

        ws_inputs = []

        # A) current entity has ExternalWS
        t_src = getattr(ent, "source", None)
        if t_src and t_src.__class__.__name__ == "ExternalWSEndpoint":
            _normalize_ws_source(t_src)
            # collect THIS entity's attrs (so we can shape from the raw payload)
            ent_attrs = []
            for a in (getattr(ent, "attributes", []) or []):
                if hasattr(a, "expr") and a.expr is not None:
                    py = compile_expr_to_python(a.expr, context=t_src.name, known_sources=all_sources)
                    print(f"\n\n\n\n\n\n\n\n\n[GEN/WS_COMPILED_ATTR] {ent.name}.{a.name} expr='{a.expr}' -> {py}")
                else:
                    # default: raw payload
                    py = f"{t_src.name}.get({a.name!r})" 
                ent_attrs.append({"name": a.name, "pyexpr": py})

            ws_inputs.append({
                "entity": ent.name,                # bind result under entity name in ctx
                "alias":  t_src.name,             # evaluate attrs against alias (external source name)
                "url": t_src.url,
                "headers": [(h["key"], h["value"]) for h in _as_headers_list(t_src)],
                "subprotocols": list(getattr(t_src, "subprotocols", []) or []),
                "protocol": getattr(t_src, "protocol", "json") or "json",
                "attrs": ent_attrs,
            })

        # B) parents with ExternalWS
        for parent in getattr(ent, "parents", []) or []:
            if isinstance(parent, dict):
                continue
            ps = getattr(parent, "source", None)
            if ps and ps.__class__.__name__ == "ExternalWSEndpoint":
                _normalize_ws_source(ps)
                parent_attrs = []
                for a in (getattr(parent, "attributes", []) or []):
                    if hasattr(a, "expr") and a.expr is not None:
                        py = compile_expr_to_python(a.expr, context=ps.name, known_sources=all_sources)
                        print(f"\n\n\n\n\n\n\n\n\n[GEN/WS_COMPILED_ATTR] {parent.name}.{a.name} expr='{a.expr}' -> {py}")
                    else:
                        py = f"{ps.name}.get({a.name!r})"
                    parent_attrs.append({"name": a.name, "pyexpr": py})

                ws_inputs.append({
                    "entity": parent.name,   # ctx[ParentEntity] = {shaped attrs}
                    "alias":  ps.name,       # eval attrs against alias (external source name)
                    "url": ps.url,
                    "headers": [(h["key"], h["value"]) for h in _as_headers_list(ps)],
                    "subprotocols": list(getattr(ps, "subprotocols", []) or []),
                    "protocol": getattr(ps, "protocol", "json") or "json",
                    "attrs": parent_attrs,
                })

        # if no ws_inputs at all, skip generating this WS router
        if not ws_inputs:
            continue
        
        (routers_dir / f"{iwep.name.lower()}_stream.py").write_text(
            tpl_router_ws.render(
                endpoint=iwep,
                entity=ent,
                computed_attrs=computed_attrs,   # for THIS entity
                ws_inputs=ws_inputs,             # now includes entity, alias, attrs
                route_prefix=_default_ws_prefix(iwep, ent),
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
    ctx = _server_ctx(model)
    copytree(base_backend_dir, out_dir, dirs_exist_ok=True)
    _render_env_and_docker(ctx, templates_backend_dir, out_dir)
    return out_dir
