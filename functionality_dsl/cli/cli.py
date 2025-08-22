import sys
import click
import os
from rich import print, pretty

from functionality_dsl.language import build_model

pretty.install()

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
        print("[*] Model validation success!!")
    except Exception as e:
        print(f"[*] Validation failed with error(s): {e}")
        context.exit(1)
    else:
        context.exit(0)
        
def main():
    cli(prog_name="fdsl")