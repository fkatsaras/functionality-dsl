from __future__ import annotations
from pathlib import Path
from shutil import copytree
from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape
from textx import get_children_of_type

# ---------- helpers ----------
def _components(model):
    # Prefer the typed list from your model processor, else fallback
    cmps = getattr(model, "aggregated_components", None)
    if cmps is not None:
        return list(cmps)
    from textx import get_children_of_type as _gc
    nodes = []
    for rule in ("LiveTableComponent", "LineChartComponent"):
        nodes += list(_gc(rule, model))
    return nodes

def _entities(model):
    return list(get_children_of_type("Entity", model))

def _get_server_ctx(model):
    servers = list(get_children_of_type("Server", model))
    if not servers:
        raise RuntimeError("No `Server` block found in model.")
    s = servers[0]
    cors_val = getattr(s, "cors", None)
    if isinstance(cors_val, (list, tuple)) and len(cors_val) == 1:
        cors_val = cors_val[0]
    return {
        "server": {
            "name": s.name,
            "host": getattr(s, "host", "localhost"),
            "port": int(getattr(s, "port", 8080)),
            "cors": cors_val or "http://localhost:3000",
        }
    }

def _jinja_env(*, loader):
    return Environment(
        loader=loader,
        autoescape=select_autoescape(disabled_extensions=("jinja",)),
        trim_blocks=True,
        lstrip_blocks=True,
        undefined=StrictUndefined,
    )

# ---------- scaffold ----------
def scaffold_frontend_from_model(model, *, base_frontend_dir: Path, templates_frontend_dir: Path, out_dir: Path) -> Path:
    ctx = _get_server_ctx(model)
    copytree(base_frontend_dir, out_dir, dirs_exist_ok=True)
    env = _jinja_env(loader=FileSystemLoader(str(templates_frontend_dir)))
    for target, tpl_name in {
        "vite.config.ts": "vite.config.ts.jinja",
        "Dockerfile":     "Dockerfile.jinja",
    }.items():
        tpl = env.get_template(tpl_name)
        (out_dir / target).write_text(tpl.render(**ctx), encoding="utf-8")
    return out_dir

# ---------- page render ----------
def render_frontend_files(model, templates_dir: Path, out_dir: Path):
    # loader must include the /components dir so the page template can import the macro
    env = _jinja_env(loader=FileSystemLoader([str(templates_dir / "components"), str(templates_dir)]))

    components = _components(model)
    ents = _entities(model)

    # Entities with REST sources -> have GET /api/entities/<name>/
    rest_entities = []
    # Computed entities that depend on ≥1 WS input -> have WS /api/entities/<name>/stream
    computed_ws_entities = []

    # Build the two sets
    for e in ents:
        src = getattr(e, "source", None)
        inputs = getattr(e, "inputs", None)

        if src and src.__class__.__name__ == "RESTEndpoint":
            rest_entities.append(e.name)

        if inputs:
            for inp in inputs:
                tgt = inp.target
                t_src = getattr(tgt, "source", None)
                if t_src and t_src.__class__.__name__ == "WSEndpoint":
                    computed_ws_entities.append(e.name)
                    break  # once is enough

    # Write page
    (out_dir / "src" / "routes").mkdir(parents=True, exist_ok=True)
    page_tpl = env.get_template("+page.svelte.jinja")
    (out_dir / "src" / "routes" / "+page.svelte").write_text(
        page_tpl.render(
            components=components,
            rest_entities=rest_entities,
            computed_ws_entities=computed_ws_entities,
        ),
        encoding="utf-8",
    )
