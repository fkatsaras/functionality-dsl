from __future__ import annotations
from pathlib import Path
from shutil import copytree
from jinja2 import Environment, FileSystemLoader, select_autoescape
from textx import get_children_of_type


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