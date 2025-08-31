# functionality_dsl/frontend/generator.py
from __future__ import annotations
from pathlib import Path
from shutil import copytree
from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape
from textx import get_children_of_type

# ---- helpers ----
def _components(model):
    from textx import get_children_of_type as _gc
    return list(_gc("Component", model))

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

# ---- SvelteKit scaffold (copy base + render Jinja templates) ----
def scaffold_frontend_from_model(model, *, base_frontend_dir: Path, templates_frontend_dir: Path, out_dir: Path) -> Path:
    """
    Copies the base SvelteKit scaffold into out_dir (which should be .../<root>/frontend)
    and renders Jinja templates that depend on the Server block (e.g. vite.config.ts, Dockerfile).
    """
    ctx = _get_server_ctx(model)

    # 1) copy the base scaffold (package.json, src/, tailwind, etc.)
    copytree(base_frontend_dir, out_dir, dirs_exist_ok=True)

    # 2) render Jinja templates that need server info
    env = Environment(
        loader=FileSystemLoader(str(templates_frontend_dir)),
        autoescape=select_autoescape(disabled_extensions=("jinja",)),
        trim_blocks=True,
        lstrip_blocks=True,
        undefined=StrictUndefined,
    )
    render_map = {
        "vite.config.ts": "vite.config.ts.jinja",
        "Dockerfile":     "Dockerfile.jinja",
    }
    for target, tpl_name in render_map.items():
        tpl = env.get_template(tpl_name)
        (out_dir / target).write_text(tpl.render(**ctx), encoding="utf-8")

    return out_dir

# ---- Component emission (LiveTable) ----
def _human_label(s: str) -> str:
    import re
    s = re.sub(r'[_\\-]+', ' ', s)
    s = re.sub(r'(?<!^)([A-Z])', r' \\1', s)
    return s[:1].upper() + s[1:]

def render_frontend_files(model, templates_dir: Path, out_dir: Path):
    """
    Emits Svelte components for Component<LiveTable> into:
        <out_dir>/src/lib/components/<ComponentName>.svelte

    NOTE: We use custom Jinja delimiters to avoid clashing with Svelte's {#if}/{#each}.
    """
    env = Environment(
        loader=FileSystemLoader(str(templates_dir)),
        autoescape=select_autoescape(disabled_extensions=("jinja",)),
        trim_blocks=True,
        lstrip_blocks=True,
        undefined=StrictUndefined,
        # avoid Svelte conflicts:
        variable_start_string="[[",
        variable_end_string="]]",
        block_start_string="[%",   # if you need blocks later
        block_end_string="%]",
        comment_start_string="[#",
        comment_end_string="#]",
    )

    gen_dir = out_dir / "src" / "lib" / "components"
    gen_dir.mkdir(parents=True, exist_ok=True)

    live_table_tpl = "LiveTable.svelte.jinja"
    if not (templates_dir / live_table_tpl).exists():
        return  

    tpl = env.get_template(live_table_tpl)

    for cmp in _components(model):
        name = getattr(cmp, "name", None)
        if not name:
            continue

        kind = (getattr(cmp, "kind", None)
                or getattr(cmp, "type", None)
                or getattr(cmp, "componentType", None)
                or "").lower()
        if kind != "livetable":
            continue

        ent = getattr(cmp, "entity", None)
        if not ent or not getattr(ent, "name", None):
            continue
        ent_name = ent.name

        inputs = getattr(ent, "inputs", None) or []
        has_computed = any(getattr(a, "expr", None) is not None for a in (getattr(ent, "attributes", None) or []))
        src_url = f"/api/entities/{ent_name.lower()}/" if (inputs or has_computed) else f"/api/entities/{ent_name.lower()}/"

        prim_key = None
        cols = []

        for p in getattr(cmp, "props", []) or []:
            key = getattr(p, "key", None)
            if key == "primaryKey":
                v = getattr(p, "value", None) or getattr(p, "text", None) or ""
                prim_key = v.strip('"') if isinstance(v, str) else v
            if key == "columns":
                items = getattr(p, "items", []) or []
                for expr in items:
                    s = getattr(expr, "string", None) or getattr(expr, "value", None) or ""
                    if not s:
                        try:
                            s = str(expr)
                        except Exception:
                            s = ""
                    s = (s or "").strip()
                    if s.startswith("data."):
                        attr_name = s[len("data."):]
                        cols.append({"key": attr_name, "label": _human_label(attr_name)})

        if not cols:
            cols = [{"key": a.name, "label": _human_label(a.name)} for a in (getattr(ent, "attributes", []) or [])]

        if not prim_key:
            keys = [c["key"] for c in cols]
            prim_key = "id" if "id" in keys else keys[0]

        out_path = gen_dir / f"{name}.svelte"
        out_path.write_text(
            tpl.render(src=src_url, columns=cols, primaryKey=prim_key),
            encoding="utf-8",
        )
