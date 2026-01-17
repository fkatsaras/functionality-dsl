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
from functionality_dsl.api.generators.core.database_generator import get_database_context
from functionality_dsl.language import build_model
from functionality_dsl.utils import print_model_debug
from functionality_dsl.language import THIS_DIR as PKG_DIR
from functionality_dsl.transformers import transform_openapi_to_fdsl

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

        # Generate JWT secret once for both backend and frontend
        from functionality_dsl.api.generators.core.infrastructure import generate_random_secret
        from functionality_dsl.api.extractors import extract_server_config

        server_config = extract_server_config(model)
        jwt_secret_value = None
        jwt_secret_var = None

        auth_config = server_config.get("auth")
        if auth_config and auth_config.get("type") == "jwt":
            jwt_config = auth_config.get("jwt", {})
            if jwt_config.get("secret"):
                jwt_secret_var = jwt_config["secret"]
                jwt_secret_value = generate_random_secret(32)
                # Store in server_config so backend can use it
                server_config["jwt_secret_var"] = jwt_secret_var
                server_config["jwt_secret_value"] = jwt_secret_value

        if target in ("all", "backend"):
            base_backend_dir = Path(PKG_DIR) / "base" / "backend"
            templates_backend_dir = Path(PKG_DIR) / "templates" / "backend"

            # Get database context for infrastructure templates
            db_context = get_database_context(model)

            scaffold_backend_from_model(
                model,
                base_backend_dir=base_backend_dir,
                templates_backend_dir=templates_backend_dir,
                out_dir=out_path,
                jwt_secret_value=jwt_secret_value,
                db_context=db_context,
                target=target,
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
                jwt_secret_value=jwt_secret_value,
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

@cli.command("visualize-model", help="Visualize an FDSL model.")
@click.pass_context
@click.argument("model_path")
@click.option("--output", "-o", "output_dir", default="docs", help="Output directory for PNG/DOT files (default: docs)")
@click.option("--no-components", "-nc", is_flag=True, help="Hide UI components from the diagram")
def visualize_model_cmd(context, model_path, output_dir, no_components):
    """
    Build a GraphViz diagram of an FDSL model (v2 syntax):
    - Server configuration
    - REST Sources (Source<REST>)
    - WS Sources (Source<WS>)
    - Entities (base and composite)
    - Generated API endpoints
    - Components (use --no-components to hide)
    """
    from graphviz import Digraph

    def get_source_operations(source):
        """Extract operations list from a source."""
        ops_obj = getattr(source, 'operations', None)
        if ops_obj:
            return getattr(ops_obj, 'operations', [])
        return []

    try:
        model = build_model(model_path)

        show_components = not no_components

        dot = Digraph(comment="FDSL Model")
        dot.attr(rankdir="LR", fontsize="10", fontname="Arial")
        dot.attr(nodesep="0.6", ranksep="1.2")
        dot.attr('edge', fontsize="9")

        # -------------------------------
        # Roles (individual nodes - will connect to entities that use them)
        # -------------------------------
        for role in model.roles:
            label = f"ROLE\\n{role.name}"
            dot.node(f"role_{role.name}", label=label,
                     shape="box", style="filled,rounded", fillcolor="#fff9c4")

        # -------------------------------
        # Auth
        # -------------------------------
        for a in model.auth:
            auth_type = getattr(a, "auth_type", getattr(a, "type", "unknown"))
            label = f"AUTH\\n{a.name}\\ntype: {auth_type}"
            dot.node(f"auth_{a.name}", label=label,
                     shape="box", style="filled,rounded", fillcolor="#ffcc80")

        # -------------------------------
        # Server
        # -------------------------------
        for s in model.servers:
            auth_ref = getattr(s, "auth", None)
            auth_str = f"\\nauth: {auth_ref.name}" if auth_ref else ""
            label = f"SERVER\\n{s.name}\\nhost: {s.host}\\nport: {s.port}{auth_str}"
            dot.node(f"server_{s.name}", label=label,
                     shape="box", style="filled,rounded", fillcolor="#bbdefb")

            # Edge: Server -> Auth
            if auth_ref:
                dot.edge(f"server_{s.name}", f"auth_{auth_ref.name}",
                         label="uses", color="#ff9800")

        # -------------------------------
        # REST Sources (Source<REST>)
        # -------------------------------
        for s in model.externalrest:
            url = getattr(s, "url", "")
            ops = get_source_operations(s)
            ops_str = ", ".join(ops) if ops else "none"

            label = f"SOURCE REST\\n{s.name}\\n{safe_label(url, 40)}\\nops: {ops_str}"
            dot.node(f"source_{s.name}", label=label,
                     shape="note", style="filled", fillcolor="#d1c4e9")

        # -------------------------------
        # WS Sources (Source<WS>)
        # -------------------------------
        for s in model.externalws:
            # Grammar stores 'channel' value in 'url' attribute
            channel = getattr(s, "url", "")
            ops = get_source_operations(s)
            ops_str = ", ".join(ops) if ops else "none"

            label = f"SOURCE WS\\n{s.name}\\n{safe_label(channel, 40)}\\nops: {ops_str}"
            dot.node(f"source_{s.name}", label=label,
                     shape="note", style="filled", fillcolor="#b39ddb")

        # -------------------------------
        # Entities
        # -------------------------------
        for e in model.entities:
            parents = getattr(e, "parents", []) or []
            is_composite = len(parents) > 0
            entity_type = getattr(e, "type", None)  # inbound/outbound for WS

            # Collect attributes
            attrs_lines = []
            for a in e.attributes:
                type_text = typespec_to_string(a.type)
                if hasattr(a, "expr") and a.expr:
                    expr_text = expr_to_string(a.expr, max_len=30)
                    attrs_lines.append(f"{a.name}: {type_text} = {safe_label(expr_text, 30)}")
                else:
                    attrs_lines.append(f"{a.name}: {type_text}")
            attrs = "\\n".join(attrs_lines)

            # Get access control
            access = getattr(e, "access", None)
            access_roles_list = []
            if access:
                access_public = getattr(access, "public_keyword", None)
                access_roles = getattr(access, "roles", None)
                if access_public:
                    access_str = "public"
                elif access_roles:
                    # access_roles contains Role objects, extract names
                    access_roles_list = [r.name for r in access_roles]
                    access_str = ", ".join(access_roles_list)
                else:
                    access_str = "public"
            else:
                access_str = "public"

            # Determine node style based on entity type
            if entity_type == "inbound":
                stereotype = "inbound"
                fillcolor = "#fff3e0"
                style = "filled,rounded"
            elif entity_type == "outbound":
                stereotype = "outbound"
                fillcolor = "#fce4ec"
                style = "filled,rounded"
            elif is_composite:
                # Composite entities: same green as regular entities, but dashed border
                stereotype = None  # No stereotype label
                fillcolor = "#c8e6c9"
                style = "filled,dashed,rounded"
            else:
                stereotype = None  # No stereotype label
                fillcolor = "#c8e6c9"
                style = "filled,rounded"

            # Build label - only show stereotype for WS entities
            if stereotype:
                label = f"[{stereotype}]\\n{e.name}\\naccess: {access_str}\\n{attrs}"
            else:
                label = f"{e.name}\\naccess: {access_str}\\n{attrs}"
            dot.node(f"entity_{e.name}", label=label,
                     shape="box", style=style, fillcolor=fillcolor)

            # Edge: Source -> Entity (for base entities with source)
            entity_source = getattr(e, "source", None)
            if entity_source:
                dot.edge(f"source_{entity_source.name}", f"entity_{e.name}",
                         label="provides", style="dashed", color="#7b1fa2")

            # Edge: Parent -> Composite Entity
            for parent in parents:
                parent_entity = getattr(parent, "entity", parent)
                parent_name = parent_entity.name if hasattr(parent_entity, "name") else str(parent_entity)
                dot.edge(f"entity_{parent_name}", f"entity_{e.name}",
                         label="composes", style="dashed", color="#1976d2")

            # Edge: Role -> Entity (for role-based access)
            for role_name in access_roles_list:
                dot.edge(f"role_{role_name}", f"entity_{e.name}",
                         label="can access", style="dotted", color="#f9a825")

        # -------------------------------
        # Generated REST API Endpoints
        # -------------------------------
        for e in model.entities:
            entity_source = getattr(e, "source", None)
            if not entity_source:
                continue

            # Check if source is REST
            is_rest_source = any(s.name == entity_source.name for s in model.externalrest)
            if not is_rest_source:
                continue

            # Get operations from the source
            ops = get_source_operations(entity_source)
            if not ops:
                continue

            # Create REST API endpoint node
            api_path = f"/api/{e.name.lower()}"
            ops_str = ", ".join(ops)
            label = f"REST API\\n{api_path}\\nops: {ops_str}"
            dot.node(f"api_{e.name}", label=label,
                     shape="box", style="filled", fillcolor="#ffe0b2")

            # Edge: Entity -> REST API
            dot.edge(f"entity_{e.name}", f"api_{e.name}",
                     label="exposes", color="#ff6f00")

        # -------------------------------
        # Generated WS Endpoints
        # -------------------------------
        for e in model.entities:
            entity_type = getattr(e, "type", None)

            # WS entities need type: inbound or outbound
            if entity_type not in ("inbound", "outbound"):
                continue

            # Create WS endpoint node
            ws_path = f"/ws/{e.name.lower()}"
            direction = "subscribe" if entity_type == "inbound" else "publish"
            label = f"WS API\\n{ws_path}\\n{direction}"
            dot.node(f"ws_{e.name}", label=label,
                     shape="box", style="filled", fillcolor="#ffccbc")

            # Edge: Entity -> WS API
            dot.edge(f"entity_{e.name}", f"ws_{e.name}",
                     label="exposes", color="#ff6f00")

        # -------------------------------
        # Components
        # -------------------------------
        if show_components:
            for c in model.components:
                comp_type = c.__class__.__name__.replace("Component", "")
                label = f"COMPONENT\\n{c.name}\\ntype: {comp_type}"
                dot.node(f"comp_{c.name}", label=label,
                         shape="ellipse", style="filled", fillcolor="#f8bbd0")

                # Edge: Component -> Entity
                entity_ref = getattr(c, "entity_ref", None) or getattr(c, "entity", None)
                if entity_ref:
                    entity_name = entity_ref.name if hasattr(entity_ref, "name") else str(entity_ref)
                    dot.edge(f"comp_{c.name}", f"entity_{entity_name}",
                             label="binds", color="#e91e63")

        # -------------------------------
        # Output
        # -------------------------------
        out_path = Path(output_dir).resolve()
        out_path.mkdir(exist_ok=True, parents=True)

        model_name = Path(model_path).stem
        file_base = out_path / f"{model_name}_diagram"
        png_file = Path(f"{file_base}.png")
        dot_file = Path(f"{file_base}.dot")
        base_file = Path(f"{file_base}")

        try:
            dot.render(str(file_base), format="png", cleanup=False)
            if dot_file.exists():
                dot_file.unlink()
            if base_file.exists():
                base_file.unlink()
            console.print(f"[{date.today().strftime('%Y-%m-%d')}] Model diagram: {png_file}", style="green")
        except Exception:
            dot.save(str(dot_file))
            console.print(f"[{date.today().strftime('%Y-%m-%d')}] GraphViz not found. DOT file: {dot_file}", style="yellow")
            console.print(f"Run: dot -Tpng {dot_file} -o {png_file}", style="yellow")

    except Exception as e:
        import traceback
        console.print(f"visualize-model failed: {e}", style="red")
        console.print(traceback.format_exc(), style="red")
        context.exit(1)
        
def _detect_spec_type(file_path: Path) -> str:
    """
    Auto-detect whether a spec file is OpenAPI or AsyncAPI.

    Returns:
        "openapi" or "asyncapi"

    Raises:
        ValueError if spec type cannot be determined
    """
    import yaml
    import json

    content = file_path.read_text(encoding="utf-8")

    # Parse the file
    if file_path.suffix in (".yaml", ".yml"):
        spec = yaml.safe_load(content)
    elif file_path.suffix == ".json":
        spec = json.loads(content)
    else:
        # Try YAML first, then JSON
        try:
            spec = yaml.safe_load(content)
        except:
            spec = json.loads(content)

    if not isinstance(spec, dict):
        raise ValueError("Invalid spec file: expected a dictionary/object at root")

    # Check for AsyncAPI marker
    if "asyncapi" in spec:
        return "asyncapi"

    # Check for OpenAPI marker
    if "openapi" in spec or "swagger" in spec:
        return "openapi"

    # Heuristic: check for channels (AsyncAPI) vs paths (OpenAPI)
    if "channels" in spec:
        return "asyncapi"
    if "paths" in spec:
        return "openapi"

    raise ValueError(
        "Cannot determine spec type. Expected 'openapi', 'swagger', or 'asyncapi' "
        "field in the spec, or 'paths' (OpenAPI) / 'channels' (AsyncAPI) sections."
    )


@cli.command("transform", help="Transform an OpenAPI/AsyncAPI spec to FDSL (auto-detects spec type)")
@click.pass_context
@click.argument("spec_path")
@click.option("--out", "-o", "output_path", default=None, help="Output FDSL file path (default: print to stdout)")
@click.option("--server-name", "-n", default=None, help="Override server name (default: from API title)")
@click.option("--host", "-h", default="localhost", help="Server host (default: localhost)")
@click.option("--port", "-p", default=8000, type=int, help="Server port (default: 8000)")
def transform_cmd(context, spec_path, output_path, server_name, host, port):
    """
    Transform an OpenAPI or AsyncAPI specification to FDSL.

    Automatically detects the spec type:
    - OpenAPI 3.x / Swagger 2.x -> FDSL with REST sources
    - AsyncAPI 2.x/3.x -> FDSL with WebSocket sources

    Supports YAML (.yaml, .yml) and JSON (.json) spec files.

    Examples:
        fdsl transform api.yaml
        fdsl transform api.yaml --out generated.fdsl
        fdsl transform websocket-api.yaml --server-name MyWSAPI
        fdsl transform petstore.json --port 3000
    """
    from ..transformers.asyncapi_to_fdsl import transform_asyncapi_to_fdsl

    try:
        spec_file = Path(spec_path).resolve()

        if not spec_file.exists():
            console.print(f"[{date.today().strftime('%Y-%m-%d')}] File not found: {spec_file}", style="red")
            context.exit(1)

        # Auto-detect spec type
        spec_type = _detect_spec_type(spec_file)
        console.print(f"[{date.today().strftime('%Y-%m-%d')}] Detected spec type: {spec_type.upper()}", style="blue")

        output_file = Path(output_path).resolve() if output_path else None

        # Call appropriate transformer
        if spec_type == "openapi":
            fdsl_content = transform_openapi_to_fdsl(
                openapi_path=spec_file,
                output_path=output_file,
                server_name=server_name,
                host=host,
                port=port,
            )
        else:  # asyncapi
            fdsl_content = transform_asyncapi_to_fdsl(
                asyncapi_path=spec_file,
                output_path=output_file,
                server_name=server_name,
                host=host,
                port=port,
            )

        if output_file:
            console.print(f"[{date.today().strftime('%Y-%m-%d')}] FDSL written to: {output_file}", style="green")
        else:
            # Print to stdout
            console.print(fdsl_content)

    except Exception as e:
        import traceback
        console.print(f"[{date.today().strftime('%Y-%m-%d')}] Transform failed: {e}", style="red")
        console.print(traceback.format_exc(), style="red")
        context.exit(1)


def main():
    cli(prog_name="fdsl")