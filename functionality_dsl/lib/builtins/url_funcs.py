import urllib.parse
import base64
from typing import Union

def _urlEncode(s: str) -> str:
    """
    URL-encode a string (percent-encoding).

    Example: urlEncode("hello world") => "hello%20world"
    """
    if s is None:
        raise TypeError("urlEncode() received None")
    return urllib.parse.quote(str(s))

def _urlDecode(s: str) -> str:
    """
    Decode URL-encoded string.

    Example: urlDecode("hello%20world") => "hello world"
    """
    if s is None:
        raise TypeError("urlDecode() received None")
    return urllib.parse.unquote(str(s))

def _parseUrl(url: str) -> dict:
    """
    Parse URL into components.
    Returns dict with: scheme, netloc, path, params, query, fragment.

    Example: parseUrl("https://example.com:8080/path?key=value#section")
    => {"scheme": "https", "netloc": "example.com:8080", "path": "/path", ...}
    """
    if url is None:
        raise TypeError("parseUrl() received None")

    parsed = urllib.parse.urlparse(url)

    return {
        "scheme": parsed.scheme,
        "netloc": parsed.netloc,
        "hostname": parsed.hostname or "",
        "port": parsed.port or None,
        "path": parsed.path,
        "params": parsed.params,
        "query": parsed.query,
        "fragment": parsed.fragment,
        "username": parsed.username or "",
        "password": parsed.password or "",
    }

def _parseQueryString(query: str) -> dict:
    """
    Parse URL query string into dict.

    Example: parseQueryString("key1=value1&key2=value2") => {"key1": "value1", "key2": "value2"}
    """
    if query is None:
        raise TypeError("parseQueryString() received None")

    parsed = urllib.parse.parse_qs(query, keep_blank_values=True)

    # Convert lists to single values for single-valued params
    result = {}
    for key, values in parsed.items():
        if len(values) == 1:
            result[key] = values[0]
        else:
            result[key] = values

    return result

def _buildUrl(base: str, params: dict = None) -> str:
    """
    Build URL with query parameters.

    Example: buildUrl("http://api.example.com", {"q": "search", "page": 1})
    => "http://api.example.com?q=search&page=1"
    """
    if base is None:
        raise TypeError("buildUrl() received None for base")

    if params is None or len(params) == 0:
        return base

    # Convert params to query string
    query_string = urllib.parse.urlencode(params)

    # Check if base already has query params
    if '?' in base:
        separator = '&'
    else:
        separator = '?'

    return f"{base}{separator}{query_string}"

def _base64Encode(s: Union[str, bytes]) -> str:
    """
    Encode string to base64.

    Example: base64Encode("hello") => "aGVsbG8="
    """
    if s is None:
        raise TypeError("base64Encode() received None")

    if isinstance(s, str):
        s = s.encode('utf-8')

    return base64.b64encode(s).decode('ascii')

def _base64Decode(s: str) -> str:
    """
    Decode base64 string.

    Example: base64Decode("aGVsbG8=") => "hello"
    """
    if s is None:
        raise TypeError("base64Decode() received None")

    try:
        decoded_bytes = base64.b64decode(s)
        return decoded_bytes.decode('utf-8')
    except Exception as e:
        raise ValueError(f"base64Decode() invalid base64 string: {e}")

def _joinPath(*parts) -> str:
    """
    Join URL path components.

    Example: joinPath("api", "v1", "users") => "api/v1/users"
    """
    # Filter out None values
    clean_parts = [str(p) for p in parts if p is not None]

    # Remove leading/trailing slashes from parts
    normalized = []
    for i, part in enumerate(clean_parts):
        if i == 0:
            # Keep leading slash on first part
            normalized.append(part.rstrip('/'))
        elif i == len(clean_parts) - 1:
            # Keep trailing slash on last part
            normalized.append(part.lstrip('/'))
        else:
            # Strip both for middle parts
            normalized.append(part.strip('/'))

    return '/'.join(normalized)


DSL_URL_FUNCS = {
    "urlEncode":        (_urlEncode, (1, 1)),
    "urlDecode":        (_urlDecode, (1, 1)),
    "parseUrl":         (_parseUrl, (1, 1)),
    "parseQueryString": (_parseQueryString, (1, 1)),
    "buildUrl":         (_buildUrl, (1, 2)),
    "base64Encode":     (_base64Encode, (1, 1)),
    "base64Decode":     (_base64Decode, (1, 1)),
    "joinPath":         (_joinPath, (1, None)),
}
