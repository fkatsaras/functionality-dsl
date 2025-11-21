import re
import json
from fastapi import HTTPException

def _require(condition, message="Validation failed", status=400):
    """Raise HTTPException if condition is False."""
    if not condition:
        raise HTTPException(status_code=status, detail={"error": message})
    return True

def _validate_email(email: str):
    """
    Validate email address format.

    Example: validate_email("user@example.com") => True
    """
    if email is None:
        return False
    return bool(re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", str(email)))

def _in_range(value, min_val, max_val):
    """
    Check if numeric value is in range (inclusive).

    Example: in_range(5, 1, 10) => True
    """
    try:
        v = float(value)
        return min_val <= v <= max_val
    except Exception:
        return False

def _validate_url(url: str) -> bool:
    """
    Validate URL format.

    Example: validate_url("https://example.com") => True
    """
    if url is None:
        return False

    # Basic URL pattern
    pattern = r'^https?://[^\s/$.?#].[^\s]*$'
    return bool(re.match(pattern, str(url), re.IGNORECASE))

def _validate_phone(phone: str) -> bool:
    """
    Validate phone number format (supports various formats).
    Accepts: +1-234-567-8900, (123) 456-7890, 123.456.7890, etc.

    Example: validate_phone("+1-234-567-8900") => True
    """
    if phone is None:
        return False

    # Remove common separators
    cleaned = re.sub(r'[\s\-\.\(\)]', '', str(phone))

    # Check if it's a valid phone number (10-15 digits, optional + prefix)
    pattern = r'^\+?[0-9]{10,15}$'
    return bool(re.match(pattern, cleaned))

def _validate_json(json_str: str) -> bool:
    """
    Validate if string is valid JSON.

    Example: validate_json('{"key": "value"}') => True
    """
    if json_str is None:
        return False

    try:
        json.loads(str(json_str))
        return True
    except (json.JSONDecodeError, ValueError):
        return False

def _validate_regex(s: str, pattern: str) -> bool:
    """
    Validate if string matches regex pattern.

    Example: validate_regex("abc123", "^[a-z]+[0-9]+$") => True
    """
    if s is None:
        return False

    try:
        return bool(re.match(pattern, str(s)))
    except re.error:
        return False

def _validate_uuid(uuid_str: str) -> bool:
    """
    Validate UUID format (UUID v4).

    Example: validate_uuid("123e4567-e89b-12d3-a456-426614174000") => True
    """
    if uuid_str is None:
        return False

    pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
    return bool(re.match(pattern, str(uuid_str), re.IGNORECASE))

def _validate_ipv4(ip: str) -> bool:
    """
    Validate IPv4 address format.

    Example: validate_ipv4("192.168.1.1") => True
    """
    if ip is None:
        return False

    pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
    if not re.match(pattern, str(ip)):
        return False

    # Check each octet is 0-255
    parts = str(ip).split('.')
    return all(0 <= int(part) <= 255 for part in parts)

def _validate_ipv6(ip: str) -> bool:
    """
    Validate IPv6 address format (basic validation).

    Example: validate_ipv6("2001:0db8:85a3:0000:0000:8a2e:0370:7334") => True
    """
    if ip is None:
        return False

    # Basic IPv6 pattern
    pattern = r'^([0-9a-f]{0,4}:){7}[0-9a-f]{0,4}$'
    return bool(re.match(pattern, str(ip), re.IGNORECASE))

def _validate_port(port) -> bool:
    """
    Validate port number (1-65535).

    Example: validate_port(8080) => True
    """
    try:
        p = int(port)
        return 1 <= p <= 65535
    except (ValueError, TypeError):
        return False

def _validate_length(s: str, min_len: int = 0, max_len: int = None) -> bool:
    """
    Validate string length is within range.

    Example: validate_length("hello", 1, 10) => True
    """
    if s is None:
        return False

    length = len(str(s))

    if max_len is not None:
        return min_len <= length <= max_len
    else:
        return length >= min_len

DSL_VALIDATION_FUNCS = {
    "require":          (_require, (2, 3)),
    "validate_email":   (_validate_email, (1, 1)),
    "validate_url":     (_validate_url, (1, 1)),
    "validate_phone":   (_validate_phone, (1, 1)),
    "validate_json":    (_validate_json, (1, 1)),
    "validate_regex":   (_validate_regex, (2, 2)),
    "validate_uuid":    (_validate_uuid, (1, 1)),
    "validate_ipv4":    (_validate_ipv4, (1, 1)),
    "validate_ipv6":    (_validate_ipv6, (1, 1)),
    "validate_port":    (_validate_port, (1, 1)),
    "validate_length":  (_validate_length, (1, 3)),
    "in_range":         (_in_range, (3, 3)),
}
