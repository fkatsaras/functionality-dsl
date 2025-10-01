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

def _auth_headers(ext):
    a = getattr(ext, "auth", None)
    if not a:
        return []

    kind = getattr(a, "kind", "").lower()
    if kind == "bearer":
        token = getattr(a, "token", "")
        if token.startswith("env:"):
            import os
            token = os.getenv(token.split(":", 1)[1], "")
        return [("Authorization", f"Bearer {token}")]

    if kind == "basic":
        import base64, os
        user = getattr(a, "username", "")
        pw = getattr(a, "password", "")
        if user.startswith("env:"):
            user = os.getenv(user.split(":", 1)[1], "")
        if pw.startswith("env:"):
            pw = os.getenv(pw.split(":", 1)[1], "")
        creds = f"{user}:{pw}"
        return [("Authorization", "Basic " + base64.b64encode(creds.encode()).decode())]

    if kind == "api_key":
        key = getattr(a, "key", "")
        val = getattr(a, "value", "")
        loc = getattr(a, "location", "header")
        if val.startswith("env:"):
            import os
            val = os.getenv(val.split(":", 1)[1], "")
        if loc == "header":
            return [(key, val)]
        else:
            # For query injection we can keep a sentinel
            return [("__queryparam__", f"{key}={val}")]

    return []

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
        
# --- chain helpers -------------------------------------------------

def _resolve_source_alias(ent, ent_src):
    """
    Map DSL 'source' references to runtime context identifiers.
    - If the source is an endpoint (InternalWS, ExternalWS, InternalREST, ExternalREST),
      return the ENTITY name (because runtime seeds the entity).
    - If the source is another entity, return its name directly.
    """
    if not ent_src:
        return ent.name
    cls = ent_src.__class__.__name__
    if cls in ("InternalWSEndpoint", "ExternalWSEndpoint", "InternalRESTEndpoint", "ExternalRESTEndpoint"):
        return ent.name  # entity gets seeded from endpoint payload
    return ent_src.name


def _all_ancestors(entity, model):
    """Return all ancestors of entity, in topological (oldest→newest) order."""
    seen = set()
    order = []
    def visit(e):
        if id(e) in seen:
            return
        seen.add(id(e))
        for p in getattr(e, "parents", []) or []:
            visit(p)
        order.append(e)
    visit(entity)
    return [e for e in order if e is not entity]

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
    tpl_router_ws_pub = env.get_template("router_ws_pub.jinja")
    tpl_router_ws_sub = env.get_template("router_ws_sub.jinja")
    tpl_router_ws_duplex = env.get_template("router_ws_duplex.jinja")

    # -------- per-internal-endpoint generation --------
    
    for src in get_children_of_type("ExternalRESTEndpoint", model):
        print(f"[DEBUG] ExternalREST {src.name} auth={getattr(src, 'auth', None)}")

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
                    print('[DEBUG] HEREHERHEHRHEHRHEHRHEHRHERHEHREHREHRHERHEHREHRHERHERHH')
                    raw = compile_expr_to_python(a.expr, context="entity", known_sources=all_sources + [ent_src.name])
                else:
                    raw = f"{ent_src.name}"
                ent_attrs.append({"name": a.name, "pyexpr": raw})
                
                computed_attrs.append({"name": a.name, "pyexpr": raw})
    
            rest_inputs.append({
                "entity": ent.name,           # <-- bind into ctx under entity name
                "alias":  ent_src.name,       # <-- evaluate exprs against this alias
                "url": ent_src.url,
                "headers": _as_headers_list(ent_src) + _auth_headers(ent_src),
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
                    "headers": _as_headers_list(t_src) + _auth_headers(t_src),
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
            ancestors = _all_ancestors(ent, model)  # oldest-first

            # collect inline-computed only (no ExternalREST, no InternalREST endpoint)
            def _has_internal_rest_endpoint_for(e):
                for other_iep in _internal_rest_endpoints(model):
                    if getattr(other_iep, "entity").name == e.name:
                        return True
                return False

            ancestors = _all_ancestors(ent, model)
            inline_chain = []
            for E in ancestors:
                E_src = getattr(E, "source", None)
                if E_src and E_src.__class__.__name__ == "ExternalRESTEndpoint":
                    
                    # treat like top-level ExternalREST input
                    ent_attrs = []
                    for a in getattr(E, "attributes", []) or []:
                        py = compile_expr_to_python(a.expr, context="entity", known_sources=all_sources) if getattr(a, "expr", None) else f"{E_src.name}"
                        ent_attrs.append({"name": a.name, "pyexpr": py})
                    rest_inputs.append({
                        "entity": E.name,
                        "alias":  E_src.name,
                        "url": E_src.url,
                        "headers": _as_headers_list(E_src) + _auth_headers(E_src),
                        "method": (getattr(E_src, "verb", "GET") or "GET").upper(),
                        "attrs": ent_attrs,
                    })
                elif not _has_internal_rest_endpoint_for(E):
                    # inline compute
                    attrs = []
                    for a in (getattr(E, "attributes", []) or []):
                        if getattr(a, "expr", None):
                            py_code = compile_expr_to_python(a.expr, context="ctx", known_sources=all_sources + [E.name])
                            attrs.append({"name": a.name, "pyexpr": py_code})
                    inline_chain.append({"name": E.name, "attrs": attrs})

                
            # Query router
            (routers_dir / f"{iep.name.lower()}.py").write_text(
                tpl_router_query_rest.render(
                    endpoint={"name": iep.name, "summary": getattr(iep, "summary", None)},
                    entity=ent,
                    computed_attrs=computed_attrs,
                    rest_inputs=rest_inputs,
                    computed_parents=computed_parents,
                    route_prefix=route_prefix,
                    inline_chain=inline_chain,
                ),
                encoding="utf-8",
            )
        else:
            # Mutation router → requires a target (usually ExternalREST)
            # --- choose terminal entity ---
            terminal_entity = _find_downstream_terminal_entity(ent, model) or ent
            
            # --- build the chain (start -> ... -> terminal), computed-only nodes ---
            ancestors = _all_ancestors(terminal_entity, model)  # oldest-first
            chain_entities = ancestors + [terminal_entity]
            
            compiled_chain = []
            for E in chain_entities:
                attrs = []
                for a in (getattr(E, "attributes", []) or []):
                    if hasattr(a, "expr") and a.expr is not None:
                        # IMPORTANT: compile against ctx
                        py_code = compile_expr_to_python(a.expr, context="ctx", known_sources=all_sources + [E.name])
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
                    "headers": _as_headers_list(tgt) + _auth_headers(tgt),
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
        
        mode = getattr(iwep, "mode", None) or "subscribe"

        if mode == "duplex":
            # inbound = internal entity (this iwep)
            inbound_chain_entities = _all_ancestors(ent, model) + [ent]

            # outbound = external duplex entity (find its entity)
            outbound_chain_entities = []
            for ext_ws in get_children_of_type("ExternalWSEndpoint", model):
                if getattr(ext_ws, "mode", None) == "duplex":
                    out_ent = getattr(ext_ws, "entity", None)
                    if out_ent:
                        outbound_chain_entities = _all_ancestors(out_ent, model) + [out_ent]
                        break
        else:
            chain_entities = _all_ancestors(ent, model) + [ent]

        compiled_chain_inbound = []
        compiled_chain_outbound = []
        ws_inputs = []

        # ------------------ Inbound chain build ------------------
        if mode == "duplex":
            scan_entities = inbound_chain_entities
        else:
            scan_entities = chain_entities

        for E in scan_entities:
            t_src = getattr(E, "source", None)
            if t_src and t_src.__class__.__name__ == "ExternalWSEndpoint":
                _normalize_ws_source(t_src)
                ent_attrs = []
                for a in getattr(E, "attributes", []) or []:
                    if hasattr(a, "expr") and a.expr is not None:
                        py = compile_expr_to_python(a.expr, context=t_src.name, known_sources=all_sources)
                    else:
                        py = f"{t_src.name}.get({a.name!r})"
                    ent_attrs.append({"name": a.name, "pyexpr": py})
                ws_inputs.append({
                    "entity": E.name,
                    "alias": t_src.name,
                    "url": t_src.url,
                    "headers": [(h["key"], h["value"]) for h in _as_headers_list(t_src)] + _auth_headers(t_src),
                    "subprotocols": list(getattr(t_src, "subprotocols", []) or []),
                    "protocol": getattr(t_src, "protocol", "json") or "json",
                    "attrs": ent_attrs,
                })
            elif (
                t_src
                and t_src.__class__.__name__ == "InternalWSEndpoint"
                and getattr(t_src, "mode", None) == "publish"
            ):
                # Internal publish as source → skip ws_inputs
                ent_attrs = []
                for a in getattr(E, "attributes", []) or []:
                    if hasattr(a, "expr") and a.expr is not None:
                        py = compile_expr_to_python(
                            a.expr,
                            context="ctx",
                            known_sources=all_sources + [t_src.name]
                        )
                        ent_attrs.append({"name": a.name, "pyexpr": py})
                if ent_attrs:
                    compiled_chain_inbound.append({"name": E.name, "attrs": ent_attrs})
            else:
                # Computed-only
                attrs = []
                for a in getattr(E, "attributes", []) or []:
                    if hasattr(a, "expr") and a.expr is not None:
                        py_code = compile_expr_to_python(a.expr, context="ctx", known_sources=all_sources + [E.name])
                        attrs.append({"name": a.name, "pyexpr": py_code})
                if attrs:
                    compiled_chain_inbound.append({"name": E.name, "attrs": attrs})

        # Deduplicate ws_inputs
        unique = {}
        for w in ws_inputs:
            key = (w["alias"], w["url"])
            if key not in unique:
                unique[key] = w
        ws_inputs = list(unique.values())
        
        # ------------------ External targets ------------------
        external_targets = []
        if mode in ("publish", "duplex"):
            for ext_ws in get_children_of_type("ExternalWSEndpoint", model):
                ext_entity = getattr(ext_ws, "entity", None)
                if ext_entity and ext_entity.name == ent.name:
                    ext_mode = getattr(ext_ws, "mode", None)
                    if ext_mode in ("publish", "duplex"):
                        _normalize_ws_source(ext_ws)
                        external_targets.append({
                            "url": ext_ws.url,
                            "headers": [(h["key"], h["value"]) for h in _as_headers_list(ext_ws)] + _auth_headers(ext_ws),
                            "subprotocols": list(getattr(ext_ws, "subprotocols", []) or []),
                            "protocol": getattr(ext_ws, "protocol", "json") or "json",
                        })
                        
        # ------------------ Outbound chain build ------------------
        if mode == "duplex":
            scan_entities = outbound_chain_entities
        else:
            scan_entities = chain_entities

        for E in scan_entities:
            out_attrs = []
            for a in getattr(E, "attributes", []) or []:
                if hasattr(a, "expr") and a.expr is not None:
                    py = compile_expr_to_python(a.expr, context="ctx", known_sources=all_sources + [E.name])
                    out_attrs.append({"name": a.name, "pyexpr": py})
            if out_attrs:
                compiled_chain_outbound.append({"name": E.name, "attrs": out_attrs})
                
        # ------------------ Outbound seed entity ------------------
        outbound_seed_entity = None
        if mode == "duplex" and outbound_chain_entities:
            # Always use the FIRST entity in the outbound chain as seed
            outbound_seed_entity = outbound_chain_entities[0].name
        
        # ------------------ Template selection ------------------
        if mode == "subscribe":
            tpl = tpl_router_ws_sub
            filename = f"{iwep.name.lower()}_sub.py"
            render_args = {
                "compiled_chain": compiled_chain_inbound,
                "ws_inputs": ws_inputs,
                "external_targets": [],
            }
        elif mode == "publish":
            tpl = tpl_router_ws_pub
            filename = f"{iwep.name.lower()}_pub.py"
            render_args = {
                "compiled_chain": compiled_chain_outbound,
                "ws_inputs": [],
                "external_targets": external_targets,
            }
        elif mode == "duplex":
            tpl = tpl_router_ws_duplex
            filename = f"{iwep.name.lower()}_duplex.py"
            render_args = {
                "compiled_chain_inbound": compiled_chain_inbound,
                "compiled_chain_outbound": compiled_chain_outbound,
                "ws_inputs": ws_inputs,
                "external_targets": external_targets,
                "outbound_seed_entity": outbound_seed_entity,
            }
        else:
            raise RuntimeError(f"Unknown WS mode: {mode}")

        (routers_dir / filename).write_text(
            tpl.render(
                endpoint=iwep,
                entity=ent,
                route_prefix=_default_ws_prefix(iwep, ent),
                **render_args
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
