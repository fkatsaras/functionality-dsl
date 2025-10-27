"""
FDSL Built-in Validators

These validators are used with the @ decorator syntax in FDSL attributes.
They map to Pydantic Field constraints during code generation.
"""

import re
from typing import Any, List, Union
from fastapi import HTTPException


# ============================================================================
# STRING VALIDATORS
# ============================================================================

def _email(value: str) -> bool:
    """Validate email format."""
    if value is None:
        return False
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(pattern, str(value)))


def _url(value: str) -> bool:
    """Validate URL format."""
    if value is None:
        return False
    pattern = r"^https?://(?:www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b(?:[-a-zA-Z0-9()@:%_\+.~#?&/=]*)$"
    return bool(re.match(pattern, str(value)))


def _pattern(value: str, regex: str) -> bool:
    """Validate against a regex pattern."""
    if value is None:
        return False
    return bool(re.match(regex, str(value)))


def _min_length(value: str, length: int) -> bool:
    """Validate minimum string length."""
    if value is None:
        return False
    return len(str(value)) >= length


def _max_length(value: str, length: int) -> bool:
    """Validate maximum string length."""
    if value is None:
        return True  # null is allowed
    return len(str(value)) <= length


def _length(value: str, exact: int) -> bool:
    """Validate exact string length."""
    if value is None:
        return False
    return len(str(value)) == exact


def _starts_with(value: str, prefix: str) -> bool:
    """Validate string starts with prefix."""
    if value is None:
        return False
    return str(value).startswith(prefix)


def _ends_with(value: str, suffix: str) -> bool:
    """Validate string ends with suffix."""
    if value is None:
        return False
    return str(value).endswith(suffix)


def _trim(value: str) -> str:
    """Auto-trim whitespace (transformer, not validator)."""
    if value is None:
        return None
    return str(value).strip()


# ============================================================================
# NUMERIC VALIDATORS
# ============================================================================

def _min(value: Union[int, float], min_val: Union[int, float]) -> bool:
    """Validate minimum value (inclusive)."""
    if value is None:
        return False
    return float(value) >= float(min_val)


def _max(value: Union[int, float], max_val: Union[int, float]) -> bool:
    """Validate maximum value (inclusive)."""
    if value is None:
        return False
    return float(value) <= float(max_val)


def _gt(value: Union[int, float], threshold: Union[int, float]) -> bool:
    """Validate greater than (exclusive)."""
    if value is None:
        return False
    return float(value) > float(threshold)


def _lt(value: Union[int, float], threshold: Union[int, float]) -> bool:
    """Validate less than (exclusive)."""
    if value is None:
        return False
    return float(value) < float(threshold)


def _gte(value: Union[int, float], threshold: Union[int, float]) -> bool:
    """Validate greater than or equal."""
    if value is None:
        return False
    return float(value) >= float(threshold)


def _lte(value: Union[int, float], threshold: Union[int, float]) -> bool:
    """Validate less than or equal."""
    if value is None:
        return False
    return float(value) <= float(threshold)


def _positive(value: Union[int, float]) -> bool:
    """Validate value is positive (> 0)."""
    if value is None:
        return False
    return float(value) > 0


def _negative(value: Union[int, float]) -> bool:
    """Validate value is negative (< 0)."""
    if value is None:
        return False
    return float(value) < 0


def _range(value: Union[int, float], min_val: Union[int, float], max_val: Union[int, float]) -> bool:
    """Validate value is within range (inclusive)."""
    if value is None:
        return False
    v = float(value)
    return float(min_val) <= v <= float(max_val)


# ============================================================================
# LIST/ARRAY VALIDATORS
# ============================================================================

def _min_items(value: List, count: int) -> bool:
    """Validate minimum list length."""
    if value is None:
        return False
    return len(value) >= count


def _max_items(value: List, count: int) -> bool:
    """Validate maximum list length."""
    if value is None:
        return True
    return len(value) <= count


def _unique(value: List) -> bool:
    """Validate all list items are unique."""
    if value is None:
        return False
    try:
        # Try to convert to set for hashable items
        return len(value) == len(set(value))
    except TypeError:
        # For unhashable items, do manual comparison
        seen = []
        for item in value:
            if item in seen:
                return False
            seen.append(item)
        return True


def _each(value: List, validator_func) -> bool:
    """Apply validator to each item in list."""
    if value is None:
        return False
    return all(validator_func(item) for item in value)


# ============================================================================
# GENERAL VALIDATORS
# ============================================================================

def _required(value: Any) -> bool:
    """Validate value is not None/null."""
    return value is not None


def _optional(value: Any) -> bool:
    """Mark as optional (always passes, just metadata)."""
    return True


def _one_of(value: Any, options: List) -> bool:
    """Validate value is in allowed options."""
    return value in options


def _in(value: Any, options: List) -> bool:
    """Alias for one_of."""
    return value in options


# ============================================================================
# CUSTOM VALIDATION
# ============================================================================

def _validate(condition: bool, message: str = "Validation failed", status: int = 400) -> bool:
    """
    Custom validation with error message.
    Raises HTTPException if condition is False.
    """
    if not condition:
        raise HTTPException(status_code=status, detail={"error": message})
    return True


# ============================================================================
# MESSAGE OVERRIDE
# ============================================================================

def _message(value: Any, msg: str) -> bool:
    """
    Override default validation error message.
    This is metadata only, doesn't perform validation.
    """
    return True


# ============================================================================
# VALIDATOR REGISTRY
# ============================================================================

DSL_VALIDATORS = {
    # String validators
    "email": (_email, (1, 1)),
    "url": (_url, (1, 1)),
    "pattern": (_pattern, (2, 2)),
    "minLength": (_min_length, (2, 2)),
    "maxLength": (_max_length, (2, 2)),
    "length": (_length, (2, 2)),
    "startsWith": (_starts_with, (2, 2)),
    "endsWith": (_ends_with, (2, 2)),
    "trim": (_trim, (1, 1)),

    # Numeric validators
    "min": (_min, (2, 2)),
    "max": (_max, (2, 2)),
    "gt": (_gt, (2, 2)),
    "lt": (_lt, (2, 2)),
    "gte": (_gte, (2, 2)),
    "lte": (_lte, (2, 2)),
    "positive": (_positive, (1, 1)),
    "negative": (_negative, (1, 1)),
    "range": (_range, (3, 3)),

    # List validators
    "minItems": (_min_items, (2, 2)),
    "maxItems": (_max_items, (2, 2)),
    "unique": (_unique, (1, 1)),
    "each": (_each, (2, 2)),

    # General validators
    "required": (_required, (1, 1)),
    "optional": (_optional, (1, 1)),
    "oneOf": (_one_of, (2, 2)),
    "in": (_in, (2, 2)),

    # Custom validation
    "validate": (_validate, (1, 3)),  # condition, [message], [status]
    "message": (_message, (2, 2)),
}


# Create validator registry for runtime use
VALIDATOR_FUNCTIONS = {k: v[0] for k, v in DSL_VALIDATORS.items()}
VALIDATOR_SIGNATURES = {k: v[1] for k, v in DSL_VALIDATORS.items()}


# ============================================================================
# PYDANTIC FIELD MAPPING
# ============================================================================

# Map validators to Pydantic Field constraints
PYDANTIC_FIELD_MAPPING = {
    # String validators
    "minLength": "min_length",
    "maxLength": "max_length",
    "pattern": "pattern",

    # Numeric validators
    "min": "ge",  # greater than or equal
    "max": "le",  # less than or equal
    "gt": "gt",
    "lt": "lt",
    "gte": "ge",
    "lte": "le",

    # List validators
    "minItems": "min_length",
    "maxItems": "max_length",

    # Special validators that need custom handling
    "email": "email",  # Uses EmailStr type
    "url": "url",      # Uses HttpUrl type
    "positive": "gt:0",
    "negative": "lt:0",
}


# Map validators that need custom Pydantic validators
PYDANTIC_CUSTOM_VALIDATORS = [
    "email",
    "url",
    "unique",
    "each",
    "oneOf",
    "in",
    "startsWith",
    "endsWith",
    "validate",
]
