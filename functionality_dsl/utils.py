from textx.model import get_children_of_type

def print_model_debug(model):
    def _get(attr, fallback_kind=None):
        if hasattr(model, attr):
            return getattr(model, attr)
        # fallback for older models without aggregates
        return list(get_children_of_type(fallback_kind, model)) if fallback_kind else []

    servers     = _get("aggregated_servers", "Server")
    databases   = _get("aggregated_databases", "Database")
    models      = _get("aggregated_models", "Model")
    requests    = _get("aggregated_requests", "Request")
    responses   = _get("aggregated_responses", "Response")
    rest_eps    = _get("aggregated_restendpoints", "RESTEndpoint")
    ws_eps      = _get("aggregated_websockets", "WebSocketEndpoint")
    actions     = _get("aggregated_actions", "Action")

    print("=== SUMMARY ===")
    print(f"Servers: {len(servers)} | REST: {len(rest_eps)} | WS: {len(ws_eps)}")
    print(f"DBs: {len(databases)} | Models: {len(models)} | Requests: {len(requests)} | Responses: {len(responses)}")
    print(f"Actions: {len(actions)}")
    print()

    if servers:
        print("=== SERVERS ===")
        for s in servers:
            base = getattr(s, "base", "/")
            base_norm = getattr(s, "base_norm", base)
            print(f"- {s.name}: {getattr(s,'host','?')}:{getattr(s,'port','?')} base={base_norm}\n")
        print()

    if rest_eps:
        print("=== REST ENDPOINTS ===")
        for ep in rest_eps:
            full_path = getattr(ep, "full_path", ep.path)
            path_params = getattr(ep, "path_params", [])
            print(f"- {ep.name}: {getattr(ep, 'verb', 'GET')} {full_path} (server={ep.server.name}) params={path_params}\n")
        print()

    if actions:
        print("=== ACTIONS ===")
        for a in actions:
            full_path = getattr(a, "full_path", getattr(a.using, "path", "?"))
            verb = getattr(a, "verb", getattr(a.using, "verb", "GET"))
            server_name = getattr(a, "server_name", getattr(a.using.server, "name", "?"))
            path_params = getattr(a, "path_params", [])
            req = getattr(a, "request", None)
            req_name = req.name if req else "?"
            req_attrs = getattr(req, "resolved_attributes", getattr(req, "attributes", [])) or []
            # normalize to name:type for printing
            def _fmt_attr(x): 
                return f"{getattr(x,'name', x.get('name'))}:{getattr(x,'type', x.get('type'))}"
            req_attrs_str = ", ".join(_fmt_attr(x) for x in req_attrs)
            # responses
            resp_entries = getattr(a, "responses_list", None)
            if resp_entries is None:
                # fallback from grammar objects
                resp_entries = []
                for r in getattr(a, "responses", []):
                    raw = getattr(r, "shape", None)
                    is_null = (raw is None) or (isinstance(raw, str) and raw.lower() in ("none","null"))
                    resp_entries.append({"status": r.status, "shape": getattr(raw, "name", None), "is_null": is_null})
            resp_str = ", ".join(f"{e['status']}: {'None' if e['is_null'] else e['shape']}" for e in resp_entries)

            print(f"- {a.name}: {verb} {full_path} (server={server_name})")
            print(f"  request: {req_name}  attrs: [{req_attrs_str}]  path_params: {path_params}")
            print(f"  responses: {resp_str}\n")
        print()