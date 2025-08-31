from pathlib import Path
import click
import os

from datetime import date
from rich import pretty
from rich.console import Console

from functionality_dsl.api.generator import scaffold_backend_from_model, render_domain_files
from functionality_dsl.language import build_model
from functionality_dsl.utils import print_model_debug
from functionality_dsl.language import THIS_DIR as PKG_DIR

pretty.install()
console = Console()

def make_executable(path: str):
    mode = os.stat(path).st_mode
    mode |= (mode & 0o444) >> 2
    os.chmod(path, mode)
    
@click.group()
@click.pass_context
def cli(context):
    context.ensure_object(dict)
    
@cli.command("validate", help="Model Validation")
@click.pass_context
@click.argument("model_path")
def validate(context, model_path):
    try:
        _ = build_model(model_path)
        console.print(f"[{date.today().strftime('%Y-%m-%d')}] Model validation success!", style='green')
    except Exception as e:
        console.print(f"[{date.today().strftime('%Y-%m-%d')}] Validation failed with error(s): {e}", style='red')
        context.exit(1)
    else:
        context.exit(0)
        
@cli.command("inspect", help="Parse and print a summary of the model (routes, actions, shapes).")
@click.pass_context
@click.argument("model_path")
def inspect_cmd(context, model_path):
    try:
        model = build_model(model_path)
        console.print(f"[{date.today().strftime('%Y-%m-%d')}] Model validation success!", style='green')
        print_model_debug(model)
    except Exception as e:
        console.print(f"[{date.today().strftime('%Y-%m-%d')}] Inspect failed with error(s): {e}", style='red')
        context.exit(1)
    else:
        context.exit(0)

@cli.command("generate-backend", help="Emit a runnable FastAPI backend from the model's Server block.")
@click.pass_context
@click.argument("model_path")
@click.option("--out", "out_dir", default="api", help="Output directory for the backend scaffold (default: ./api)")
def generate_backend(context, model_path, out_dir):
    try:
        model = build_model(model_path)
        # Resolve directories relative to the installed package
        base_backend_dir = Path(PKG_DIR) / "base" / "backend"
        templates_backend_dir = Path(PKG_DIR) / "templates" / "backend"
        out_path = Path(out_dir).resolve()

        scaffold_backend_from_model(
            model,
            base_backend_dir=base_backend_dir,
            templates_backend_dir=templates_backend_dir,
            out_dir=out_path,
        )
        render_domain_files(model, templates_backend_dir, out_path)

        # make docker helpers executable if you add shell scripts later
        console.print(f"[{date.today().strftime('%Y-%m-%d')}] Backend emitted to: {out_path}", style="green")
    except Exception as e:
        console.print(f"[{date.today().strftime('%Y-%m-%d')}] Generate failed with error(s): {e}", style="red")
        context.exit(1)
    else:
        context.exit(0)
        
def main():
    cli(prog_name="fdsl")