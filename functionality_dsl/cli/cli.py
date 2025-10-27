from pathlib import Path
import subprocess
import sys
import click
import os

from datetime import date
from rich import pretty
from rich.console import Console
from textx import metamodel_from_file
from textx.export import metamodel_export, PlantUmlRenderer
from plantuml import PlantUML

from functionality_dsl.api.generator import scaffold_backend_from_model, render_domain_files
from functionality_dsl.api.frontend_generator import render_frontend_files, scaffold_frontend_from_model
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

@cli.command("generate", help="Emit a runnable project (backend, frontend, or both).")
@click.pass_context
@click.argument("model_path")
@click.option(
    "--target",
    type=click.Choice(["all", "backend", "frontend"], case_sensitive=False),
    default="all",
    help="What to generate (default: all)."
)
@click.option("--out", "out_dir", default="generated", help="Output directory (default: ./generated)")
def generate(context, model_path, target, out_dir):
    try:
        model = build_model(model_path)
        out_path = Path(out_dir).resolve()

        if target in ("all", "backend"):
            base_backend_dir = Path(PKG_DIR) / "base" / "backend"
            templates_backend_dir = Path(PKG_DIR) / "templates" / "backend"
            scaffold_backend_from_model(
                model,
                base_backend_dir=base_backend_dir,
                templates_backend_dir=templates_backend_dir,
                out_dir=out_path,
            )
            render_domain_files(model, templates_backend_dir, out_path)
            console.print(f"[{date.today().strftime('%Y-%m-%d')}] Backend emitted to: {out_path}", style="green")

        if target in ("all", "frontend"):
            base_frontend_dir = Path(PKG_DIR) / "base" / "frontend"
            templates_frontend_dir = Path(PKG_DIR) / "templates" / "frontend"
            # copy SvelteKit scaffold + render vite.config.ts & Dockerfile
            scaffold_frontend_from_model(
                model,
                base_frontend_dir=base_frontend_dir,
                templates_frontend_dir=templates_frontend_dir,
                out_dir=out_path / "frontend",
            )
            # then write generated components
            render_frontend_files(model, templates_frontend_dir, out_path / "frontend")
            console.print(f"[{date.today().strftime('%Y-%m-%d')}] Frontend emitted to: {out_path / 'frontend'}", style="green")

    except Exception as e:
        console.print(f"[{date.today().strftime('%Y-%m-%d')}] Generate failed with error(s): {e}", style="red")
        context.exit(1)
    else:
        context.exit(0)
        
@cli.command("visualize", help="Export a PlantUML diagram of a textX grammar/metamodel.")
@click.pass_context
@click.argument("grammar_path")
def visualize_cmd(context, grammar_path):
    try:
        gpath = Path(grammar_path).resolve()
        out_dir = Path("docs").resolve()
        out_dir.mkdir(parents=True, exist_ok=True)

        # build textX metamodel
        mm = metamodel_from_file(str(gpath))

        # write PlantUML source (.puml)
        pu_file = out_dir / (gpath.stem + "_metamodel.puml")
        metamodel_export(mm, str(pu_file), renderer=PlantUmlRenderer())

        console.print(f"[{date.today().strftime('%Y-%m-%d')}] Rendering PlantUML diagram...", style="blue")

        # Use Python PlantUML API (renders via public PlantUML server)
        server = PlantUML(url="http://www.plantuml.com/plantuml/img/")
        server.processes_file(str(pu_file))

        out_file = out_dir / (pu_file.stem + ".png")
        if out_file.exists():
            console.print(f"[{date.today().strftime('%Y-%m-%d')}] Diagram written to: {out_file}", style="green")
            context.exit(0)
        else:
            console.print(f"[{date.today().strftime('%Y-%m-%d')}] PlantUML did not produce {out_file.name}.", style="red")
            context.exit(1)

    except Exception as e:
        console.print(f"[{date.today().strftime('%Y-%m-%d')}] Visualize failed with error(s): {e}", style="red")
        context.exit(1)
        
def main():
    cli(prog_name="fdsl")