"""
CLI entry-point for the functionality-dsl project.

Run `pip install -e .` in the repo root, then:

    funcdsl validate examples/app.fdsl
    funcdsl generate examples/app.fdsl ./generated
"""
from __future__ import annotations

# from pathlib import Path

import click
from rich.console import Console
from rich import pretty


# ---- local imports ----
from functionality_dsl.language import build_model  # type: ignore
# from functionality_dsl.generate import run_codegen  # type: ignore

pretty.install()
console = Console()

# ---- CLI root ----
@click.group(help="fdsl :  validate model files and generate FastAPI code.")
@click.version_option(message="functionality DSL %(version)s")
def cli() -> None:
    pass

# ---- validate ----
@cli.command(short_help="Validate a .fdsl model")
@click.argument("model_path", type=click.Path(exists=True, dir_okay=False))
def validate(model_path: str) -> None:
    """ Parse and semantically validate a .fdsl file"""
    try:
        build_model(model_path)
        click.echo("Model OK ✔ ")
    except Exception as e:
        click.echo(f"Validation failed: {e}", err=True)
        raise SystemExit(1) from e
    
    

# # ---- generate ----
# @cli.command(short_help="Generate FastAPI project from model")
# @click.argument("model_path", type=click.Path(exists=True, dir_okay=False))
# @click.argument(
#     "output_dir",
#     default="generated",
#     required=False,
#     type=click.Path(file_okay=False),
# )
# def generate(model_path: str, output_dir: str) -> None:
#     """Generate backend boilerplate from an .fdsl model."""
#     outdir = Path(output_dir).resolve()
#     outdir.mkdir(parents=True, exist_ok=True)

#     try:
#         run_codegen(model_path, outdir)
#         click.echo(f"Code generated in {outdir}")
#     except Exception as e:
#         click.echo(f"Generation error: {e}", err=True)
#         raise SystemExit(1) from e


def main() -> None:
    cli(prog_name="fdsl")