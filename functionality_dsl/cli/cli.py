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
from functionality_dsl.language import THIS_DIR as PKG_DIR
from functionality_dsl.transformers import transform_openapi_to_fdsl
from textx import get_children_of_type

pretty.install()
console = Console()

def make_executable(path: str):
    mode = os.stat(path).st_mode
    mode |= (mode & 0o444) >> 2
    os.chmod(path, mode)


def extract_source_auth_secrets(model):
    """
    Extract auth secrets from sources that reference Auth with secret field.

    Returns list of env var names for source auth (e.g., ["FINNHUB_API_KEY"])
    """
    secrets = set()

    # Get all REST and WS sources
    rest_sources = get_children_of_type("SourceREST", model)
    ws_sources = get_children_of_type("SourceWS", model)

    for source in list(rest_sources) + list(ws_sources):
        auth = getattr(source, "auth", None)
        if auth:
            # Check if auth has a secret field (source-level auth)
            secret = getattr(auth, "secret", None)
            if secret:
                secrets.add(secret)

    return list(secrets)

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


def _visualize_metamodel(context, grammar_path, output_dir, engine):
    """
    Visualize a TextX grammar metamodel (advanced use case).
    """
    try:
        gpath = Path(grammar_path).resolve()
        out_dir = Path(output_dir).resolve()
        out_dir.mkdir(parents=True, exist_ok=True)

        # Build the meta-model
        mm = metamodel_from_file(str(gpath))

        stem = gpath.stem
        base_name = f"{stem}_metamodel"

        if engine == "dot":
            dot_file = out_dir / f"{base_name}.dot"
            png_file = out_dir / f"{base_name}.png"

            metamodel_export(mm, str(dot_file))
            console.print(f"[{date.today().strftime('%Y-%m-%d')}] Rendering metamodel with GraphViz...", style="blue")

            exit_status = os.system(f"dot -Tpng {dot_file} -o {png_file}")
            if exit_status != 0:
                console.print(f"[{date.today().strftime('%Y-%m-%d')}] GraphViz rendering failed.", style="red")
                context.exit(1)

            dot_file.unlink(missing_ok=True)
            console.print(f"[{date.today().strftime('%Y-%m-%d')}] Metamodel diagram: {png_file}", style="green")

        elif engine == "plantuml":
            pu_file = out_dir / f"{base_name}.puml"
            svg_file = out_dir / f"{base_name}.svg"
            png_file = out_dir / f"{base_name}_plant.png"

            metamodel_export(mm, str(pu_file), renderer=PlantUmlRenderer())
            console.print(f"[{date.today().strftime('%Y-%m-%d')}] Rendering metamodel with PlantUML...", style="blue")

            exit_status = os.system(f"plantuml -Tsvg -o . {pu_file}")
            if exit_status != 0:
                console.print(f"[{date.today().strftime('%Y-%m-%d')}] PlantUML failed to render.", style="red")
                context.exit(1)

            if not svg_file.exists():
                console.print(f"[{date.today().strftime('%Y-%m-%d')}] PlantUML produced no SVG output.", style="red")
                context.exit(1)

            os.system(f"convert -background white -flatten {svg_file} {png_file}")
            pu_file.unlink(missing_ok=True)
            svg_file.unlink(missing_ok=True)
            console.print(f"[{date.today().strftime('%Y-%m-%d')}] Metamodel diagram: {png_file}", style="green")

        context.exit(0)

    except Exception as e:
        console.print(f"[{date.today().strftime('%Y-%m-%d')}] Metamodel visualization failed: {e}", style="red")
        context.exit(1)


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

            # Extract source auth secrets (env vars for external API auth)
            source_auth_secrets = extract_source_auth_secrets(model)
            if source_auth_secrets:
                db_context["source_auth_env_vars"] = source_auth_secrets

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
        
@cli.command("visualize", help="Visualize an FDSL model as a diagram.")
@click.pass_context
@click.argument("model_path")
@click.option("--output", "-o", "output_dir", default="docs", help="Output directory for PNG/DOT files (default: docs)")
@click.option("--no-components", "-nc", is_flag=True, help="Hide UI components from the diagram")
@click.option("--metamodel", is_flag=True, help="Visualize the grammar metamodel instead of an FDSL model (advanced)")
@click.option("--engine", type=click.Choice(["dot", "plantuml"], case_sensitive=False), default="dot", help="Rendering engine for metamodel visualization")
def visualize_cmd(context, model_path, output_dir, no_components, metamodel, engine):
    """
    Build a GraphViz diagram of an FDSL model:
    - Server configuration
    - REST Sources (Source<REST>)
    - WS Sources (Source<WS>)
    - Entities (base and composite)
    - Generated API endpoints
    - Components (use --no-components to hide)

    Use --metamodel to visualize the TextX grammar metamodel instead (advanced).
    """
    # Handle metamodel visualization (special case)
    if metamodel:
        _visualize_metamodel(context, model_path, output_dir, engine)
        return
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
        # Auth<type> mechanisms
        # -------------------------------
        # Collect referenced auth names (by roles, sources, or entity access)
        referenced_auths = set()
        for role in model.roles:
            auth_ref = getattr(role, "auth", None)
            if auth_ref:
                referenced_auths.add(auth_ref.name)
        for s in model.externalrest:
            auth_ref = getattr(s, "auth", None)
            if auth_ref:
                referenced_auths.add(auth_ref.name)
        for s in model.externalws:
            auth_ref = getattr(s, "auth", None)
            if auth_ref:
                referenced_auths.add(auth_ref.name)

        for a in model.auth:
            # Skip orphaned auth declarations (not referenced by any role or source)
            if a.name not in referenced_auths:
                continue
            # Get auth type from class name (AuthJWT -> jwt, AuthSession -> session, etc.)
            class_name = a.__class__.__name__
            if class_name.startswith("Auth"):
                auth_type = class_name[4:].lower()  # AuthJWT -> jwt
            else:
                auth_type = "unknown"
            label = f"AUTH<{auth_type}>\\n{a.name}"
            dot.node(f"auth_{a.name}", label=label,
                     shape="box", style="filled,rounded", fillcolor="#ffcc80")

        # -------------------------------
        # Roles (with 'uses' relationship to Auth)
        # -------------------------------
        for role in model.roles:
            auth_ref = getattr(role, "auth", None)
            label = f"ROLE\\n{role.name}"
            dot.node(f"role_{role.name}", label=label,
                     shape="box", style="filled,rounded", fillcolor="#fff9c4")

            # Edge: Role -> Auth (uses relationship)
            if auth_ref:
                dot.edge(f"role_{role.name}", f"auth_{auth_ref.name}",
                         label="uses", style="dashed", color="#ff9800")

        # -------------------------------
        # Server (record shape with sections)
        # -------------------------------
        for s in model.servers:
            # Section 1: stereotype + name, Section 2: attributes
            attrs = f"host: {s.host}\\lport: {s.port}\\l"
            label = f"«server»\\n{s.name}|{attrs}"
            dot.node(f"server_{s.name}", label=label,
                     shape="record", style="filled", fillcolor="#bbdefb")

        # -------------------------------
        # REST Sources (Source<REST>)
        # -------------------------------
        for s in model.externalrest:
            url = getattr(s, "url", "")
            ops = get_source_operations(s)
            ops_str = ", ".join(ops) if ops else "none"
            source_auth = getattr(s, "auth", None)
            # Get params if defined
            params_obj = getattr(s, "params", None)
            params_list = getattr(params_obj, "params", []) if params_obj else []
            params_str = ", ".join(params_list) if params_list else None

            # Section 1: stereotype + name, Section 2: attributes
            attrs = f"url: {safe_label(url, 40)}\\loperations: {ops_str}\\l"
            if params_str:
                attrs += f"params: {params_str}\\l"
            label = f"«source» REST\\n{s.name}|{attrs}"
            dot.node(f"source_{s.name}", label=label,
                     shape="record", style="filled", fillcolor="#d1c4e9")

            # Edge: Source -> Auth (if source has auth configured)
            if source_auth:
                dot.edge(f"source_{s.name}", f"auth_{source_auth.name}",
                         label="auth", style="dotted", color="#ff9800")

        # -------------------------------
        # WS Sources (Source<WS>)
        # -------------------------------
        for s in model.externalws:
            # Grammar stores 'channel' value in 'url' attribute
            channel = getattr(s, "url", "")
            ops = get_source_operations(s)
            ops_str = ", ".join(ops) if ops else "stream"
            source_auth = getattr(s, "auth", None)
            # Get params if defined
            params_obj = getattr(s, "params", None)
            params_list = getattr(params_obj, "params", []) if params_obj else []
            params_str = ", ".join(params_list) if params_list else None

            # Section 1: stereotype + name, Section 2: attributes
            attrs = f"channel: {safe_label(channel, 40)}\\loperations: {ops_str}\\l"
            if params_str:
                attrs += f"params: {params_str}\\l"
            label = f"«source» WS\\n{s.name}|{attrs}"
            dot.node(f"source_{s.name}", label=label,
                     shape="record", style="filled", fillcolor="#b39ddb")

            # Edge: Source -> Auth (if source has auth configured)
            if source_auth:
                dot.edge(f"source_{s.name}", f"auth_{source_auth.name}",
                         label="auth", style="dotted", color="#ff9800")

        # -------------------------------
        # Entities (UML Class Diagram Style)
        # -------------------------------
        # First pass: identify schema-only entities (used in nested types)
        schema_only_entities = set()
        for e in model.entities:
            for a in e.attributes:
                type_spec = getattr(a, "type", None)
                if type_spec:
                    item_entity = getattr(type_spec, "itemEntity", None)
                    nested_entity = getattr(type_spec, "nestedEntity", None)
                    if item_entity:
                        schema_only_entities.add(item_entity.name)
                    if nested_entity:
                        schema_only_entities.add(nested_entity.name)

        for e in model.entities:
            parents = getattr(e, "parents", []) or []
            is_composite = len(parents) > 0
            entity_type = getattr(e, "flow", None)  # inbound/outbound for WS
            is_schema_only = e.name in schema_only_entities and not getattr(e, "source", None) and not getattr(e, "access", None)

            # Collect attributes and nested entity references
            attrs_lines = []
            nested_entity_refs = []  # Track for drawing edges
            for a in e.attributes:
                type_text = typespec_to_string(a.type)
                # Escape angle brackets in type text for record shapes (e.g., integer<int64> -> integer\<int64\>)
                type_text_escaped = safe_label(type_text, max_len=100, escape_angles=True)
                if hasattr(a, "expr") and a.expr:
                    expr_text = expr_to_string(a.expr, max_len=30)
                    attrs_lines.append(f"+ {a.name}: {type_text_escaped} = {safe_label(expr_text, 30)}\\l")
                else:
                    attrs_lines.append(f"+ {a.name}: {type_text_escaped}\\l")

                # Track nested entity refs for edges
                type_spec = getattr(a, "type", None)
                if type_spec:
                    item_entity = getattr(type_spec, "itemEntity", None)
                    nested_entity = getattr(type_spec, "nestedEntity", None)
                    if item_entity:
                        nested_entity_refs.append((a.name, item_entity.name, "array"))
                    if nested_entity:
                        nested_entity_refs.append((a.name, nested_entity.name, "object"))

            attrs = "".join(attrs_lines)

            # Get access control (handles new multi-auth syntax)
            access = getattr(e, "access", None)
            access_roles_list = []
            access_auth_list = []
            if access:
                access_public = getattr(access, "public_keyword", None)
                access_items = getattr(access, "access_items", None)
                access_rules = getattr(access, "access_rules", None)
                auth_ref = getattr(access, "auth_ref", None)

                if access_public:
                    access_str = "public"
                elif auth_ref:
                    # Auth-only access: access: AuthName
                    access_str = auth_ref.name
                    access_auth_list.append(auth_ref.name)
                elif access_items:
                    # List access: access: [admin, APIKeyAuth, user]
                    items = []
                    for item in access_items:
                        role = getattr(item, "role", None)
                        auth = getattr(item, "auth", None)
                        if role:
                            items.append(role.name)
                            access_roles_list.append(role.name)
                        elif auth:
                            items.append(auth.name)
                            access_auth_list.append(auth.name)
                    access_str = ", ".join(items)
                elif access_rules:
                    # Per-operation access: read: public create: [admin]
                    rule_strs = []
                    for rule in access_rules:
                        op = getattr(rule, "operation", "?")
                        rule_public = getattr(rule, "public_keyword", None)
                        rule_items = getattr(rule, "access_items", None)
                        rule_auth = getattr(rule, "auth_ref", None)
                        if rule_public:
                            rule_strs.append(f"{op}: public")
                        elif rule_auth:
                            rule_strs.append(f"{op}: {rule_auth.name}")
                            access_auth_list.append(rule_auth.name)
                        elif rule_items:
                            names = []
                            for item in rule_items:
                                role = getattr(item, "role", None)
                                auth = getattr(item, "auth", None)
                                if role:
                                    names.append(role.name)
                                    access_roles_list.append(role.name)
                                elif auth:
                                    names.append(auth.name)
                                    access_auth_list.append(auth.name)
                            rule_strs.append(f"{op}: [{', '.join(names)}]")
                    access_str = " / ".join(rule_strs)
                else:
                    access_str = "public"
            else:
                access_str = "public"

            # Determine stereotype and fill color based on entity type
            if entity_type == "inbound":
                stereotype = "«inbound»"
                fillcolor = "#fff3e0"
            elif entity_type == "outbound":
                stereotype = "«outbound»"
                fillcolor = "#fce4ec"
            elif is_composite:
                stereotype = "«composite»"
                fillcolor = "#c8e6c9"
            else:
                stereotype = None
                fillcolor = "#c8e6c9"

            # Build UML record-style label with vertical compartments
            # With rankdir=LR, removing outer braces makes compartments stack vertically
            if stereotype:
                header = f"{stereotype}\\n{e.name}"
            else:
                header = e.name

            # UML record label format: header|attributes|metadata (no outer braces for vertical)
            label = f"{header}|{attrs}|access: {access_str}\\l"

            dot.node(f"entity_{e.name}", label=label,
                     shape="record", style="filled", fillcolor=fillcolor)

            # Edge: Source -> Entity (UML dependency - dashed with open arrow)
            entity_source = getattr(e, "source", None)
            if entity_source:
                dot.edge(f"source_{entity_source.name}", f"entity_{e.name}",
                         label="«provides»", style="dashed", arrowhead="vee", color="#7b1fa2")

            # Edge: Parent -> Composite Entity (UML composition - filled diamond)
            for parent in parents:
                parent_entity = getattr(parent, "entity", parent)
                parent_name = parent_entity.name if hasattr(parent_entity, "name") else str(parent_entity)
                dot.edge(f"entity_{parent_name}", f"entity_{e.name}",
                         label="1", arrowtail="diamond", arrowhead="none", dir="back", color="#1976d2")

            # Edge: Entity -> Nested Entity (UML aggregation/composition)
            for attr_name, nested_name, ref_type in nested_entity_refs:
                if ref_type == "array":
                    # Aggregation with multiplicity 1..*
                    dot.edge(f"entity_{e.name}", f"entity_{nested_name}",
                             label="1..*", arrowtail="odiamond", arrowhead="none", dir="back", color="#4caf50")
                else:
                    # Composition with multiplicity 1
                    dot.edge(f"entity_{e.name}", f"entity_{nested_name}",
                             label="1", arrowtail="diamond", arrowhead="none", dir="back", color="#4caf50")

            # Edge: Role -> Entity (for role-based access)
            for role_name in access_roles_list:
                dot.edge(f"role_{role_name}", f"entity_{e.name}",
                         arrowhead="vee", style="dashed", color="#f9a825")

            # Edge: Auth -> Entity (for auth-ref access)
            for auth_name in access_auth_list:
                dot.edge(f"auth_{auth_name}", f"entity_{e.name}",
                         arrowhead="vee", style="dashed", color="#ff9800")

        # -------------------------------
        # Generated REST API Endpoints (UML Interface)
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

            # Create REST API endpoint node (UML interface style with record shape)
            api_path = f"/api/{e.name.lower()}"
            ops_str = ", ".join(ops)
            # UML interface: «interface» stereotype with operations (vertical layout)
            label = f"«interface»\\nREST API|{api_path}\\l|{ops_str}\\l"
            dot.node(f"api_{e.name}", label=label,
                     shape="record", style="filled", fillcolor="#ffe0b2")

            # Edge: Entity -> REST API (UML realization - dashed with empty triangle)
            dot.edge(f"entity_{e.name}", f"api_{e.name}",
                     arrowtail="onormal", arrowhead="none", dir="back", style="dashed", color="#ff6f00")

        # -------------------------------
        # Generated WS Endpoints (UML Interface)
        # -------------------------------
        for e in model.entities:
            entity_type = getattr(e, "flow", None)

            # WS entities need type: inbound or outbound
            if entity_type not in ("inbound", "outbound"):
                continue

            # Create WS endpoint node (UML interface style)
            ws_path = f"/ws/{e.name.lower()}"
            direction = "subscribe" if entity_type == "inbound" else "publish"
            # UML interface: «interface» stereotype with direction (vertical layout)
            label = f"«interface»\\nWS API|{ws_path}\\l|{direction}\\l"
            dot.node(f"ws_{e.name}", label=label,
                     shape="record", style="filled", fillcolor="#ffccbc")

            # Edge: Entity -> WS API (UML realization - dashed with empty triangle)
            dot.edge(f"entity_{e.name}", f"ws_{e.name}",
                     arrowtail="onormal", arrowhead="none", dir="back", style="dashed", color="#ff6f00")

        # -------------------------------
        # Components (UML Component notation)
        # -------------------------------
        if show_components:
            for c in model.components:
                comp_type = c.__class__.__name__.replace("Component", "")
                # UML component: «component» stereotype (vertical layout)
                label = f"«component»\\n{c.name}|type: {comp_type}\\l"
                dot.node(f"comp_{c.name}", label=label,
                         shape="record", style="filled", fillcolor="#f8bbd0")

                # Edge: Component -> Entity (UML dependency)
                entity_ref = getattr(c, "entity_ref", None) or getattr(c, "entity", None)
                if entity_ref:
                    entity_name = entity_ref.name if hasattr(entity_ref, "name") else str(entity_ref)
                    dot.edge(f"comp_{c.name}", f"entity_{entity_name}",
                             arrowhead="vee", style="dashed", color="#e91e63")

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