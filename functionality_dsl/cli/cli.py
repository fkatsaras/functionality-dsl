from pathlib import Path
import subprocess
import sys
import click
import os
import re

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

def typespec_to_string(type_spec) -> str:
    """
    Convert a TypeSpec AST object to a readable string representation.

    Examples:
    - string -> "string"
    - integer(1..10) -> "integer(1..10)"
    - array<Product> -> "array<Product>"
    - object<ProductData>? -> "object<ProductData>?"
    """
    if type_spec is None:
        return "unknown"

    # Handle array<Entity>
    if hasattr(type_spec, 'itemEntity') and type_spec.itemEntity:
        result = f"array<{type_spec.itemEntity.name}>"
    # Handle object<Entity>
    elif hasattr(type_spec, 'nestedEntity') and type_spec.nestedEntity:
        result = f"object<{type_spec.nestedEntity.name}>"
    # Handle base types (string, integer, number, etc.)
    elif hasattr(type_spec, 'baseType') and type_spec.baseType:
        result = type_spec.baseType

        # Add format if present (e.g., string<email>)
        if hasattr(type_spec, 'format') and type_spec.format:
            result += f"<{type_spec.format}>"
    else:
        # Fallback: try to get typename or baseType
        result = getattr(type_spec, 'typename', 'unknown')

    # Add constraint if present (e.g., (1..10))
    if hasattr(type_spec, 'constraint') and type_spec.constraint:
        constraint = type_spec.constraint
        if hasattr(constraint, 'range') and constraint.range:
            range_expr = constraint.range
            if hasattr(range_expr, 'exact') and range_expr.exact is not None:
                result += f"({range_expr.exact})"
            elif hasattr(range_expr, 'min') and hasattr(range_expr, 'max'):
                min_val = range_expr.min if range_expr.min is not None else ""
                max_val = range_expr.max if range_expr.max is not None else ""
                result += f"({min_val}..{max_val})"

    # Add nullable marker if present
    if hasattr(type_spec, 'nullable') and type_spec.nullable:
        result += "?"

    return result


def expr_to_string(expr, max_len=50) -> str:
    """
    Convert an Expression AST object to a readable string.
    Uses the compiled Python representation as a fallback.

    Falls back to compiled Python code if direct conversion fails.
    """
    if expr is None:
        return ""

    # Try to use the already-compiled Python code if available
    if hasattr(expr, '_py'):
        code = expr._py
        if len(code) > max_len:
            return code[:max_len] + "..."
        return code

    # Fallback: compile it now
    try:
        from functionality_dsl.lib.compiler.expr_compiler import compile_expr_to_python
        code = compile_expr_to_python(expr)
        if len(code) > max_len:
            return code[:max_len] + "..."
        return code
    except Exception:
        # If compilation fails, return a simple indicator
        return f"<expr: {expr.__class__.__name__}>"


def safe_label(text: str, max_len=50, escape_angles=True):
    """
    Make text safe for GraphViz labels:
    - escape quotes
    - optionally escape < > { } | characters used by DOT
    - replace newlines
    - truncate long expressions

    Args:
        text: The text to escape
        max_len: Maximum length before truncation
        escape_angles: If True, escape < > characters. Set to False for type annotations.
    """
    if text is None:
        return ""

    text = str(text)

    # GraphViz escapes
    text = text.replace("\\", "\\\\")
    text = text.replace('"', '\\"')

    # Only escape angles, braces, pipes if requested
    # For type annotations like "array<Product>", we don't want to escape < >
    if escape_angles:
        text = text.replace("<", "\\<").replace(">", "\\>")
        text = text.replace("{", "\\{").replace("}", "\\}")
        text = text.replace("|", "\\|")

    text = text.replace("\n", " ")

    if len(text) > max_len:
        text = text[:max_len] + "..."

    return text

    
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
        import traceback
    
        console.print(
            f"[{date.today().strftime('%Y-%m-%d')}] Generate failed with error(s): {e}",
            style="red",
        )

        tb_lines = traceback.format_exc().splitlines()
        last_lines = tb_lines[-50:]

        console.print("\n".join(last_lines), style="red")

        context.exit(1)
    else:
        context.exit(0)
        
@cli.command("visualize", help="Generate a metamodel diagram using GraphViz or PlantUML")
@click.pass_context
@click.argument("grammar_path")
@click.option(
    "--engine",
    type=click.Choice(["dot", "plantuml"], case_sensitive=False),
    default="dot",
    help="Select visualization engine: dot (GraphViz) or plantuml"
)
def visualize_cmd(context, grammar_path, engine):
    """
    Docstring for visualize_cmd
    
    :param context: click execution context
    :param grammar_path: The path to the TextX grammar file
    :param engine: Description
    """
    try:
        gpath = Path(grammar_path).resolve()

        # Output directory
        out_dir = Path("docs").resolve()
        out_dir.mkdir(parents=True, exist_ok=True)

        # Build the meta-model
        mm = metamodel_from_file(str(gpath))

        # plantuml + dot require different intermediate formats
        stem = gpath.stem
        base_name = f"{stem}_metamodel"

        # ------------------------------------------------------------------
        # ENGINE: GraphViz (dot)
        # ------------------------------------------------------------------
        if engine == "dot":
            dot_file = out_dir / f"{base_name}.dot"
            png_file = out_dir / f"{base_name}.png"

            metamodel_export(mm, str(dot_file))

            console.print(f"[{date.today().strftime('%Y-%m-%d')}] Rendering with GraphViz...", style="blue")

            exit_status = os.system(f"dot -Tpng {dot_file} -o {png_file}")

            if exit_status != 0:
                console.print(f"[{date.today().strftime('%Y-%m-%d')}] GraphViz rendering failed.", style="red")
                context.exit(1)

            dot_file.unlink(missing_ok=True)
            console.print(f"[{date.today().strftime('%Y-%m-%d')}] Diagram written to: {png_file}", style="green")
            context.exit(0)

        # ------------------------------------------------------------------
        # ENGINE: PlantUML (local)
        # ------------------------------------------------------------------
        elif engine == "plantuml":
            pu_file = out_dir / f"{base_name}.puml"
            svg_file = out_dir / f"{base_name}.svg"
            png_file = out_dir / f"{base_name}_plant.png"

            metamodel_export(mm, str(pu_file), renderer=PlantUmlRenderer())

            console.print(f"[{date.today().strftime('%Y-%m-%d')}] Rendering with PlantUML...", style="blue")

            # Ensure PlantUML writes SVG into docs/ by using -o relative path
            # PlantUML expects *folder name*, not full path
            exit_status = os.system(f"plantuml -Tsvg -o . {pu_file}")

            if exit_status != 0:
                console.print(f"[{date.today().strftime('%Y-%m-%d')}] PlantUML failed to render.", style="red")
                context.exit(1)

            # Check if SVG now exists
            if not svg_file.exists():
                console.print(f"[{date.today().strftime('%Y-%m-%d')}] PlantUML produced no SVG output.", style="red")
                context.exit(1)

            # Convert SVG → PNG
            os.system(f"convert -background white -flatten {svg_file} {png_file}")

            # Cleanup
            pu_file.unlink(missing_ok=True)
            svg_file.unlink(missing_ok=True)

            console.print(f"[{date.today().strftime('%Y-%m-%d')}] Diagram written to: {png_file}", style="green")
            context.exit(0)

    except Exception as e:
        console.print(f"[{date.today().strftime('%Y-%m-%d')}] Visualization failed with: {e}", style="red")
        context.exit(1)

@cli.command("visualize-model", help="Visualize an FDSL model (not the metamodel).")
@click.pass_context
@click.argument("model_path")
@click.option("--output", "-o", "output_dir", default="docs", help="Output directory for PNG/DOT files (default: docs)")
def visualize_model_cmd(context, model_path, output_dir):
    """
    Build a GraphViz diagram of the *model instance*:
    - Servers
    - Entities
    - Endpoints (REST + WS)
    - Components
    - Sources
    """
    from graphviz import Digraph
    try:
        model = build_model(model_path)

        dot = Digraph(comment="FDSL Model")
        dot.attr(rankdir="LR", fontsize="10", fontname="Arial")
        # Improve graph layout to show all connections clearly
        dot.attr(nodesep="0.5", ranksep="1.0")
        # Make edge labels more visible
        dot.attr('edge', fontsize="9")

        # -------------------------------
        # Servers
        # -------------------------------
        for s in model.servers:
            label_text = (
                f"[SERVER]\\n"
                f"{safe_label(s.name)}\\n"
                f"host={safe_label(s.host)}\\n"
                f"port={safe_label(s.port)}"
            )
            dot.node(
                f"server_{s.name}",
                label=label_text,
                shape="box", style="filled", fillcolor="#bbdefb"
            )

        # -------------------------------
        # Entities
        # -------------------------------
        for e in model.entities:
            # Collect attributes safely - convert TypeSpec and Expr AST to strings
            attrs_lines = []
            for a in e.attributes:
                # Convert TypeSpec AST to readable string (don't escape < > in types)
                type_text = safe_label(typespec_to_string(a.type), escape_angles=False)

                if hasattr(a, "expr") and a.expr:
                    # Convert Expression AST to readable string (ESCAPE angles in expressions!)
                    expr_text = safe_label(expr_to_string(a.expr, max_len=40), escape_angles=True)
                    attrs_lines.append(f"{safe_label(a.name, escape_angles=False)}: {type_text} = {expr_text}")
                else:
                    attrs_lines.append(f"{safe_label(a.name, escape_angles=False)}: {type_text}")

            attrs = "\\n".join(attrs_lines)  # Newline inside a DOT record

            # Build label content - use plain text, not HTML-like labels
            # The format is:  [ENTITY] Name\nattributes...
            node_label = f"[ENTITY]\\n{safe_label(e.name, escape_angles=False)}\\n{attrs}"

            dot.node(
                f"entity_{e.name}",
                label=node_label,  # Use label parameter explicitly
                shape="box", fillcolor="#c8e6c9", style="filled,rounded",
                fontcolor="black",  # Ensure text is visible on green background
                fontsize="10"  # Explicit font size for readability
            )

            # Inheritance - use 'parents' not 'super' (entities can have multiple parents)
            parents = getattr(e, "parents", []) or []
            for parent in parents:
                dot.edge(
                    f"entity_{parent.name}",
                    f"entity_{e.name}",
                    label="extends"
                )

            # v2 syntax: Entity expose blocks (REST/WebSocket)
            expose = getattr(e, "expose", None)
            if expose:
                # REST expose
                rest_expose = getattr(expose, "rest", None)
                if rest_expose:
                    rest_path = getattr(rest_expose, "path", "")
                    # In expose blocks, operations is just a plain list
                    operations = getattr(expose, "operations", [])
                    # Show actual operations, not defaults
                    ops_str = ", ".join(operations) if operations else ""

                    if ops_str:
                        node_label = (
                            f"[REST API]\\n"
                            f"{safe_label(rest_path)}\\n"
                            f"ops: {safe_label(ops_str)}"
                        )
                    else:
                        node_label = (
                            f"[REST API]\\n"
                            f"{safe_label(rest_path)}"
                        )
                    dot.node(
                        f"api_rest_{e.name}",
                        label=node_label,
                        shape="box", fillcolor="#ffe0b2", style="filled"
                    )

                    # Entity -> REST API
                    dot.edge(
                        f"entity_{e.name}",
                        f"api_rest_{e.name}",
                        label="exposes",
                        color="#ff6f00"
                    )

                # WebSocket expose
                websocket_expose = getattr(expose, "websocket", None)
                if websocket_expose:
                    # WebSocket uses 'channel' not 'path'
                    websocket_path = getattr(websocket_expose, "channel", "")
                    # In expose blocks, operations is just a plain list
                    operations = getattr(expose, "operations", [])
                    # Show actual operations, not defaults
                    ops_str = ", ".join(operations) if operations else ""

                    if ops_str:
                        node_label = (
                            f"[WS API]\\n"
                            f"{safe_label(websocket_path)}\\n"
                            f"ops: {safe_label(ops_str)}"
                        )
                    else:
                        node_label = (
                            f"[WS API]\\n"
                            f"{safe_label(websocket_path)}"
                        )
                    dot.node(
                        f"api_ws_{e.name}",
                        label=node_label,
                        shape="box", fillcolor="#ffccbc", style="filled"
                    )

                    # Entity -> WS API
                    dot.edge(
                        f"entity_{e.name}",
                        f"api_ws_{e.name}",
                        label="exposes",
                        color="#ff6f00"
                    )

        # -------------------------------
        # REST Endpoints
        # -------------------------------
        for ep in model.apirest:
            node_label = (
                f"[REST]\\n"
                f"{safe_label(ep.name)}\\n"
                f"{safe_label(ep.method)} {safe_label(ep.path)}"
            )
            dot.node(
                f"rest_{ep.name}",
                label=node_label,
                shape="box", fillcolor="#ffe0b2", style="filled"
            )

            # Add edge from endpoint to response entity
            response = getattr(ep, "response", None)
            if response:
                schema = getattr(response, "schema", None)
                if schema:
                    entity = getattr(schema, "entity", None)
                    if entity:
                        dot.edge(
                            f"rest_{ep.name}",
                            f"entity_{entity.name}",
                            label="response",
                            color="#ff6f00"
                        )

            # Add edge from request entity to endpoint
            request = getattr(ep, "request", None)
            if request:
                schema = getattr(request, "schema", None)
                if schema:
                    entity = getattr(schema, "entity", None)
                    if entity:
                        dot.edge(
                            f"entity_{entity.name}",
                            f"rest_{ep.name}",
                            label="request",
                            color="#1976d2"
                        )

        # -------------------------------
        # WS Endpoints
        # -------------------------------
        for ep in model.apiws:
            # EndpointWS uses 'path' attribute (not 'channel')
            ws_path = getattr(ep, "path", getattr(ep, "channel", ""))
            node_label = (
                f"[WS]\\n"
                f"{safe_label(ep.name)}\\n"
                f"path={safe_label(ws_path)}"
            )
            dot.node(
                f"ws_{ep.name}",
                label=node_label,
                shape="box", fillcolor="#ffccbc", style="filled"
            )

            # Subscribe block (server -> client, so endpoint -> entity)
            subscribe = getattr(ep, "subscribe", None)
            if subscribe:
                message = getattr(subscribe, "message", None)
                if message:
                    entity = getattr(message, "entity", None)
                    if entity:
                        dot.edge(
                            f"ws_{ep.name}",
                            f"entity_{entity.name}",
                            label="subscribe",
                            color="#ff6f00"
                        )

            # Publish block (client -> server, so entity -> endpoint)
            publish = getattr(ep, "publish", None)
            if publish:
                message = getattr(publish, "message", None)
                if message:
                    entity = getattr(message, "entity", None)
                    if entity:
                        dot.edge(
                            f"entity_{entity.name}",
                            f"ws_{ep.name}",
                            label="publish",
                            color="#1976d2"
                        )

        # -------------------------------
        # Components
        # -------------------------------
        for c in model.components:
            node_label = (
                f"[COMPONENT]\\n"
                f"{safe_label(c.name)}"
            )
            dot.node(
                f"comp_{c.name}",
                label=node_label,
                shape="ellipse", fillcolor="#f8bbd0", style="filled"
            )

            # v1 syntax: component -> endpoint
            if getattr(c, "endpoint", None):
                ep = c.endpoint
                if ep.__class__.__name__ == "EndpointWS":
                    target = f"ws_{ep.name}"
                else:
                    target = f"rest_{ep.name}"
                dot.edge(
                    f"comp_{c.name}",
                    target,
                    label="endpoint"
                )

            # v2 syntax: component -> entity
            if getattr(c, "entity", None):
                entity = c.entity
                dot.edge(
                    f"comp_{c.name}",
                    f"entity_{entity.name}",
                    label="binds to",
                    color="#e91e63"
                )

        # -------------------------------
        # External Sources (REST) - handles both v1 and v2
        # -------------------------------
        for s in model.externalrest:
            # Detect v2 syntax (has base_url and operations) vs v1 (has url)
            is_v2 = hasattr(s, "base_url") and hasattr(s, "operations")

            if is_v2:
                # v2 syntax - show base_url and operations
                base_url = getattr(s, "base_url", "")
                operations_block = getattr(s, "operations", None)
                operations = getattr(operations_block, "simple_ops", []) if operations_block else []
                ops_str = ", ".join(operations) if operations else "none"

                node_label = (
                    f"[SOURCE REST]\\n"
                    f"{safe_label(s.name)}\\n"
                    f"{safe_label(base_url)}\\n"
                    f"ops: {safe_label(ops_str)}"
                )
                dot.node(
                    f"source_{s.name}",
                    label=node_label,
                    shape="note", fillcolor="#d1c4e9", style="filled"
                )

                # Find entities that reference this source
                for e in model.entities:
                    entity_source = getattr(e, "source", None)
                    if entity_source and entity_source.name == s.name:
                        dot.edge(
                            f"source_{s.name}",
                            f"entity_{e.name}",
                            label="provides",
                            color="#7b1fa2",
                            style="dashed"
                        )
            else:
                # v1 syntax - show url
                node_label = (
                    f"[SOURCE REST]\\n"
                    f"{safe_label(s.name)}\\n"
                    f"{safe_label(s.url)}"
                )
                dot.node(
                    f"extrest_{s.name}",
                    label=node_label,
                    shape="note", fillcolor="#d1c4e9", style="filled"
                )

                # Add edge from source to response entity
                response = getattr(s, "response", None)
                if response:
                    schema = getattr(response, "schema", None)
                    if schema:
                        entity = getattr(schema, "entity", None)
                        if entity:
                            dot.edge(
                                f"extrest_{s.name}",
                                f"entity_{entity.name}",
                                label="provides",
                                color="#7b1fa2",
                                style="dashed"
                            )

                # Add edge from request entity to source (for mutations)
                request = getattr(s, "request", None)
                if request:
                    schema = getattr(request, "schema", None)
                    if schema:
                        entity = getattr(schema, "entity", None)
                        if entity:
                            dot.edge(
                                f"entity_{entity.name}",
                                f"extrest_{s.name}",
                                label="sends",
                                color="#7b1fa2",
                                style="dashed"
                            )

        # -------------------------------
        # External Sources (WS) - handles both v1 and v2
        # -------------------------------
        for s in model.externalws:
            # Detect v2 syntax (has channel and operations) vs v1 (has url)
            is_v2 = hasattr(s, "channel") and hasattr(s, "operations")

            if is_v2:
                # v2 syntax - show channel and operations
                channel = getattr(s, "channel", "")
                operations_block = getattr(s, "operations", None)
                operations = getattr(operations_block, "simple_ops", []) if operations_block else []
                ops_str = ", ".join(operations) if operations else "none"

                node_label = (
                    f"[SOURCE WS]\\n"
                    f"{safe_label(s.name)}\\n"
                    f"{safe_label(channel)}\\n"
                    f"ops: {safe_label(ops_str)}"
                )
                dot.node(
                    f"source_{s.name}",
                    label=node_label,
                    shape="note", fillcolor="#b39ddb", style="filled"
                )

                # Find entities that reference this source (for subscribe)
                for e in model.entities:
                    entity_source = getattr(e, "source", None)
                    if entity_source and entity_source.name == s.name:
                        dot.edge(
                            f"source_{s.name}",
                            f"entity_{e.name}",
                            label="streams",
                            color="#7b1fa2",
                            style="dashed"
                        )

                    # Find entities that target this source (for publish)
                    target = getattr(e, "target", None)
                    if target and target.name == s.name:
                        dot.edge(
                            f"entity_{e.name}",
                            f"source_{s.name}",
                            label="publishes",
                            color="#7b1fa2",
                            style="dashed"
                        )
            else:
                # v1 syntax - show url
                node_label = (
                    f"[SOURCE WS]\\n"
                    f"{safe_label(s.name)}\\n"
                    f"{safe_label(s.url)}"
                )
                dot.node(
                    f"extws_{s.name}",
                    label=node_label,
                    shape="note", fillcolor="#b39ddb", style="filled"
                )

                # Subscribe block (external source -> entity)
                subscribe = getattr(s, "subscribe", None)
                if subscribe:
                    message = getattr(subscribe, "message", None)
                    if message:
                        entity = getattr(message, "entity", None)
                        if entity:
                            dot.edge(
                                f"extws_{s.name}",
                                f"entity_{entity.name}",
                                label="streams",
                                color="#7b1fa2",
                                style="dashed"
                            )

                # Publish block (entity -> external source)
                publish = getattr(s, "publish", None)
                if publish:
                    message = getattr(publish, "message", None)
                    if message:
                        entity = getattr(message, "entity", None)
                        if entity:
                            dot.edge(
                                f"entity_{entity.name}",
                                f"extws_{s.name}",
                                label="sends",
                                color="#7b1fa2",
                                style="dashed"
                            )

        # -------------------------------
        # Output
        # -------------------------------
        out_path = Path(output_dir).resolve()
        out_path.mkdir(exist_ok=True, parents=True)

        # Create filename based on the input model file
        model_name = Path(model_path).stem  # Get filename without extension
        file_base = out_path / f"{model_name}_diagram"

        png_file = Path(f"{file_base}.png")
        dot_file = Path(f"{file_base}.dot")
        base_file = Path(f"{file_base}")  # graphviz creates a file without extension too

        # Try to render PNG, but fallback to just saving .dot file if graphviz not installed
        try:
            # Render with cleanup=False to keep the .dot file temporarily
            dot.render(str(file_base), format="png", cleanup=False)

            # Delete temporary files after successful render (cleanup)
            if dot_file.exists():
                dot_file.unlink()
            if base_file.exists():
                base_file.unlink()

            console.print(
                f"[{date.today().strftime('%Y-%m-%d')}] Model visualization written to: {png_file}",
                style="green"
            )
        except Exception:
            # Fallback: save .dot file only if PNG generation fails
            dot.save(str(dot_file))
            console.print(
                f"[{date.today().strftime('%Y-%m-%d')}] GraphViz 'dot' executable not found. Saved DOT file to: {dot_file}",
                style="yellow"
            )
            console.print(
                f"To generate PNG: Install GraphViz (https://graphviz.org/download/) and run: dot -Tpng {dot_file} -o {png_file}",
                style="yellow"
            )

    except Exception as e:
        console.print(f"visualize-model failed: {e}", style="red")
        context.exit(1)
        
def main():
    cli(prog_name="fdsl")