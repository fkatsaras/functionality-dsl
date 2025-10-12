import re

from fastapi import HTTPException

def _require(condition, message="Validation failed", status=400):
    """Raise HTTPException if condition is False."""
    if not condition:
        raise HTTPException(status_code=status, detail={"error": message})
    return True

def _validate_email(email: str):
    if email is None:
        return False
    return bool(re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", str(email)))

def _in_range(value, min_val, max_val):
    try:
        v = float(value)
        return min_val <= v <= max_val
    except Exception:
        return False

DSL_VALIDATION_FUNCS = {
    "require": (_require, (2, 3)),          # require(cond, msg, [status])
    "validate_email": (_validate_email, (1, 1)),
    "in_range": (_in_range, (3, 3)),
}
