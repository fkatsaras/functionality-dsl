"""Header normalization and authentication utilities."""

import base64
import re


def normalize_headers(obj):
    """Convert headers from various formats to list of (key, value) tuples."""
    headers = getattr(obj, "headers", None)
    if not headers:
        return []

    normalized = []

    # Handle list of header objects
    if isinstance(headers, list):
        for h in headers:
            key = getattr(h, "key", None)
            value = getattr(h, "value", None)
            if key and value is not None:
                normalized.append((key, value))
        return normalized

    # Handle string format "key1: value1; key2: value2"
    if isinstance(headers, str):
        parts = [p.strip() for p in re.split(r"[;,]", headers) if p.strip()]
        for part in parts:
            if ":" in part:
                key, value = part.split(":", 1)
                normalized.append((key.strip(), value.strip()))
        return normalized

    return normalized


def build_auth_headers(source):
    """Generate authentication headers based on source or endpoint auth config."""
    auth = getattr(source, "auth", None)
    if not auth:
        return []

    auth_kind = getattr(auth, "kind", "").lower()

    # Bearer token
    if auth_kind == "bearer":
        token = getattr(auth, "token", "")
        if token.startswith("env:"):
            import os
            token = os.getenv(token.split(":", 1)[1], "")
        return [("Authorization", f"Bearer {token}")]

    # Basic auth
    if auth_kind == "basic":
        username = getattr(auth, "username", "")
        password = getattr(auth, "password", "")
        if username.startswith("env:"):
            import os
            username = os.getenv(username.split(":", 1)[1], "")
        if password.startswith("env:"):
            import os
            password = os.getenv(password.split(":", 1)[1], "")
        credentials = f"{username}:{password}"
        encoded = base64.b64encode(credentials.encode()).decode()
        return [("Authorization", f"Basic {encoded}")]

    # API key
    if auth_kind == "api_key":
        key = getattr(auth, "key", "")
        value = getattr(auth, "value", "")
        location = getattr(auth, "location", "header")
        if value.startswith("env:"):
            import os
            value = os.getenv(value.split(":", 1)[1], "")
        if location == "header":
            return [(key, value)]
        else:
            # Query param injection marker
            return [("__queryparam__", f"{key}={value}")]

    return []
