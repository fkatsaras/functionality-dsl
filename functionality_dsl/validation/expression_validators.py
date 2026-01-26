"""
Expression-level validation for FDSL.

This module contains validation functions for expressions used in entity attributes,
parameters, error/event conditions, etc.
"""

from collections import deque
from textx import get_children_of_type, get_location, TextXSemanticError

from functionality_dsl.lib.compiler.expr_compiler import compile_expr_to_python
from functionality_dsl.lib.builtins.registry import DSL_FUNCTION_SIG


# ------------------------------------------------------------------------------
# Constants
RESERVED = {'in', 'for', 'if', 'else', 'not', 'and', 'or'}
SKIP_KEYS = {"parent", "parent_ref", "parent_obj", "model", "_tx_fqn", "_tx_position"}


# ------------------------------------------------------------------------------
# Tree traversal utilities

def _is_node(x):
    """Check if x is a textX node (not a primitive type)."""
    return hasattr(x, "__class__") and not isinstance(
        x, (str, int, float, bool, list, dict, tuple)
    )


def _walk(node):
    """
    DFS over a textX node graph; ignores parent/model backrefs and primitives.
    Also descends into lists, tuples and dicts.
    """
    if node is None:
        return
    seen = set()
    stack = deque([node])

    def push(obj):
        if obj is None:
            return
        if _is_node(obj):
            stack.append(obj)
        elif isinstance(obj, (list, tuple)):
            for it in obj:
                push(it)
        elif isinstance(obj, dict):
            for it in obj.values():
                push(it)

    while stack:
        n = stack.pop()
        nid = id(n)
        if nid in seen:
            continue
        seen.add(nid)
        yield n
        for k, v in vars(n).items():
            if k in SKIP_KEYS or v is None:
                continue
            push(v)


def _as_id_str(x):
    """Extract identifier string from various node types."""
    if x is None:
        return None
    if isinstance(x, str):
        return x
    for attr in ("name", "obj_name", "value", "ID"):
        v = getattr(x, attr, None)
        if isinstance(v, str):
            return v
    try:
        s = str(x)
        return s if "<" not in s else None
    except Exception:
        return None


# ------------------------------------------------------------------------------
# Expression analysis helpers

def _loop_var_names(expr) -> set[str]:
    """
    Extract loop variable names from lambdas.
    These should not be flagged as unknown references.
    """
    names: set[str] = set()

    for n in _walk(expr):
        cname = n.__class__.__name__

        if cname == "LambdaExpr":
            if getattr(n, "param", None):  # Single parameter
                nm = _as_id_str(n.param)
                if nm:
                    names.add(nm)
            elif getattr(n, "params", None):  # Tuple parameter
                for v in getattr(n.params, "vars", []):
                    nm = _as_id_str(v)
                    if nm:
                        names.add(nm)

    return names


def _collect_refs(expr, loop_vars: set[str] | None = None):
    """
    Collect references (alias, attr) from expressions.
    Skip loop vars so that `x` in `[... for x in ...]` is not flagged as unknown.
    """
    lvs = loop_vars or set()

    for n in _walk(expr):
        nname = n.__class__.__name__

        if nname == "Ref":
            alias_raw = getattr(n, "alias", None)
            alias = _as_id_str(alias_raw)
            if alias in lvs:
                continue  # loop var, ignore
            yield alias, getattr(n, "attr", None), n

        elif nname == "PostfixExpr":
            base = n.base
            tails = list(getattr(n, "tails", []) or [])

            if getattr(base, "var", None) is not None:
                alias_raw = base.var
                alias = _as_id_str(alias_raw)

                if not alias or alias in RESERVED or alias in lvs:
                    continue  # skip reserved/loop vars

                # If there are tails, extract the first member/param access
                if tails:
                    first = tails[0]
                    if getattr(first, "member", None) is not None:
                        attr_name = getattr(first.member, "name", None)
                        if not attr_name:
                            attr_name = "__jsonpath__"
                    elif getattr(first, "param", None) is not None:
                        # Path parameter access with '@' - mark as special
                        attr_name = f"@{getattr(first.param, 'name', None)}"
                    else:
                        # if the first tail is an index, treat as jsonpath
                        attr_name = "__jsonpath__"
                else:
                    # No tails = bare identifier reference
                    attr_name = None

                yield alias, attr_name, n


def _collect_bare_vars(expr, loop_vars: set[str] | None = None):
    """
    Collect bare variable references (Var nodes that are NOT part of PostfixExpr with tails).
    These are truly bare identifiers without attribute access.
    PostfixExpr with base.var AND tails (like Entity.attr) should NOT be caught here.
    PostfixExpr with base.var but NO tails (like bare EntityB) SHOULD be caught.
    """
    lvs = loop_vars or set()
    constants = {"None", "null", "True", "False", "true", "false"}

    # Collect Var nodes that are part of PostfixExpr WITH tails (these have attribute access, so OK)
    # Only skip vars that have actual member/index access (non-empty tails)
    postfix_base_vars_with_access = set()
    for n in _walk(expr):
        if n.__class__.__name__ == "PostfixExpr":
            tails = getattr(n, "tails", None) or []
            # Only mark as having access if there are actual tails (attribute/index access)
            if tails:
                base = getattr(n, "base", None)
                if base and getattr(base, "var", None) is not None:
                    var_name = _as_id_str(base.var)
                    if var_name:
                        postfix_base_vars_with_access.add(id(base.var))  # Track by object ID

    # Now collect bare Var nodes that are NOT part of PostfixExpr with tails
    for n in _walk(expr):
        nname = n.__class__.__name__

        if nname == "Var":
            var_name = getattr(n, "name", None)
            # Skip if:
            # - It's a loop var
            # - It's a reserved word
            # - It's a constant
            # - It's part of a PostfixExpr WITH tails (Entity.attr syntax)
            if (var_name and
                var_name not in lvs and
                var_name not in RESERVED and
                var_name not in constants and
                id(n) not in postfix_base_vars_with_access):
                yield var_name, n


def _collect_calls(expr):
    """Collect function calls from an expression."""
    for n in _walk(expr):
        if n.__class__.__name__ == "Call":
            fname = getattr(n, "func", None)
            argc = len(getattr(n, "args", []) or [])
            yield fname, argc, n


def _validate_func(name, argc, node):
    """Validate function call arity and semantic constraints."""
    if name not in DSL_FUNCTION_SIG:
        raise TextXSemanticError(f"Unknown function '{name}'.", **get_location(node))

    min_arity, max_arity = DSL_FUNCTION_SIG[name]
    if argc < min_arity or (max_arity is not None and argc > max_arity):
        if max_arity is None:
            expect = f"at least {min_arity}"
        elif max_arity == min_arity:
            expect = f"{min_arity}"
        else:
            expect = f"{min_arity}..{max_arity}"
        raise TextXSemanticError(
            f"Function '{name}' expects {expect} args, got {argc}.",
            **get_location(node),
        )


def _build_validation_context(model, current_entity, loop_vars: set[str], current_attr_idx: int = -1) -> dict:
    """
    Build a validation context dictionary containing all valid identifiers
    that can be referenced in expressions.

    Args:
        model: The FDSL model
        current_entity: The entity being validated (for parent references)
        loop_vars: Lambda parameter names (scoped to the expression)
        current_attr_idx: Index of the current attribute being validated (for forward-ref checking)

    Returns:
        Dict mapping identifier names to True (for quick lookup)
        Also includes metadata keys prefixed with '_' for validation logic
    """
    context = {}

    # Add all entity names
    for entity in get_children_of_type("Entity", model):
        context[entity.name] = True

    # Add all endpoint names (REST + WS)
    for endpoint in get_children_of_type("EndpointREST", model):
        context[endpoint.name] = True
    for endpoint in get_children_of_type("EndpointWS", model):
        context[endpoint.name] = True

    # Add all source names (REST + WS)
    for source in get_children_of_type("SourceREST", model):
        context[source.name] = True
    for source in get_children_of_type("SourceWS", model):
        context[source.name] = True

    # Add parent entity names and aliases (for inheritance)
    if current_entity:
        from functionality_dsl.validation.entity_validators import _get_parent_refs, _get_parent_alias
        parent_refs = _get_parent_refs(current_entity)
        for parent_ref in parent_refs:
            # Add both the entity name AND the alias
            context[parent_ref.entity.name] = True
            alias = _get_parent_alias(parent_ref)
            context[alias] = True  # Add alias too

    # Add loop variables (lambda parameters)
    for var in loop_vars:
        context[var] = True

    # Add metadata for forward-reference checking (prefixed with '_')
    if current_entity:
        context['_current_entity_name'] = current_entity.name
        context['_current_attr_idx'] = current_attr_idx

        # Build attribute position map for the current entity
        entity_attrs = getattr(current_entity, "attributes", []) or []
        attr_positions = {attr.name: idx for idx, attr in enumerate(entity_attrs)}
        context['_entity_attrs'] = attr_positions

    return context
