def _tostring(x) -> str:
    if x is None:
        raise TypeError("_tostring() received None")
    return str(x)

def _lower(x) -> str:
    if x is None:
        raise TypeError("_lower() received None")
    return str(x).lower()

def _upper(x) -> str:
    if x is None:
        raise TypeError("_upper() received None")
    return str(x).upper()

def _len(x) -> int:
    if x is None:
        raise TypeError("_len() received None")
    return len(x)

def _split(s: str, delim: str):
    if s is None:
        raise TypeError("_split() received None")
    return str(s).split(delim)

def _join(xs, delim: str):
    if xs is None:
        raise TypeError("_join() received None")
    return str(delim).join(map(str, xs))

def _trim(s: str):
    if s is None:
        raise TypeError("_trim() received None")
    return str(s).strip()

def _replace(s: str, old: str, new: str):
    if s is None:
        raise TypeError("_replace() received None")
    return str(s).replace(old, new)

def _sha256(s: str) -> str:
    """Hash a string using SHA-256. Returns hex digest."""
    import hashlib
    if s is None:
        raise TypeError("_sha256() received None")
    return hashlib.sha256(str(s).encode('utf-8')).hexdigest()

def _sha1(s: str) -> str:
    """Hash a string using SHA-1. Returns hex digest."""
    import hashlib
    if s is None:
        raise TypeError("_sha1() received None")
    return hashlib.sha1(str(s).encode('utf-8')).hexdigest()

def _md5(s: str) -> str:
    """Hash a string using MD5. Returns hex digest."""
    import hashlib
    if s is None:
        raise TypeError("_md5() received None")
    return hashlib.md5(str(s).encode('utf-8')).hexdigest()

def _match(s: str, pattern: str) -> bool:
    """
    Test if string matches regex pattern.

    Example: match("hello123", "\\w+\\d+") => True
    """
    import re
    if s is None:
        raise TypeError("_match() received None")
    return bool(re.search(pattern, str(s)))

def _extract(s: str, pattern: str, group: int = 0) -> str:
    """
    Extract regex group from string.
    Group 0 returns full match, 1+ returns capture groups.

    Example: extract("Price: $25.99", "\\$(\\d+\\.\\d+)", 1) => "25.99"
    """
    import re
    if s is None:
        raise TypeError("_extract() received None")

    match = re.search(pattern, str(s))
    if match:
        return match.group(group)
    return ""

def _padLeft(s: str, length: int, char: str = " ") -> str:
    """
    Pad string on the left to reach target length.

    Example: padLeft("42", 5, "0") => "00042"
    """
    if s is None:
        raise TypeError("_padLeft() received None")
    s_str = str(s)
    if len(char) != 1:
        raise ValueError("padLeft() char must be single character")
    return s_str.rjust(length, char)

def _padRight(s: str, length: int, char: str = " ") -> str:
    """
    Pad string on the right to reach target length.

    Example: padRight("42", 5, "0") => "42000"
    """
    if s is None:
        raise TypeError("_padRight() received None")
    s_str = str(s)
    if len(char) != 1:
        raise ValueError("padRight() char must be single character")
    return s_str.ljust(length, char)

def _truncate(s: str, length: int, suffix: str = "...") -> str:
    """
    Truncate string to max length and add suffix.

    Example: truncate("Hello world", 8, "...") => "Hello..."
    """
    if s is None:
        raise TypeError("_truncate() received None")
    s_str = str(s)
    if len(s_str) <= length:
        return s_str
    return s_str[:length - len(suffix)] + suffix

def _slugify(s: str) -> str:
    """
    Convert string to URL-safe slug (lowercase, hyphens, alphanumeric).

    Example: slugify("Hello World 123!") => "hello-world-123"
    """
    import re
    if s is None:
        raise TypeError("_slugify() received None")

    s_str = str(s).lower()
    # Replace non-alphanumeric with hyphens
    s_str = re.sub(r'[^a-z0-9]+', '-', s_str)
    # Remove leading/trailing hyphens
    s_str = s_str.strip('-')
    return s_str

def _camelCase(s: str) -> str:
    """
    Convert string to camelCase.

    Example: camelCase("hello_world") => "helloWorld"
    Example: camelCase("Hello World") => "helloWorld"
    """
    import re
    if s is None:
        raise TypeError("_camelCase() received None")

    s_str = str(s)
    # Split on non-alphanumeric
    words = re.split(r'[^a-zA-Z0-9]+', s_str)
    # Filter empty strings
    words = [w for w in words if w]

    if not words:
        return ""

    # First word lowercase, rest title case
    return words[0].lower() + ''.join(w.capitalize() for w in words[1:])

def _snakeCase(s: str) -> str:
    """
    Convert string to snake_case.

    Example: snakeCase("HelloWorld") => "hello_world"
    Example: snakeCase("Hello World") => "hello_world"
    """
    import re
    if s is None:
        raise TypeError("_snakeCase() received None")

    s_str = str(s)
    # Insert underscore before capitals (for camelCase)
    s_str = re.sub(r'([a-z0-9])([A-Z])', r'\1_\2', s_str)
    # Replace non-alphanumeric with underscore
    s_str = re.sub(r'[^a-zA-Z0-9]+', '_', s_str)
    # Lowercase and remove duplicate underscores
    s_str = s_str.lower()
    s_str = re.sub(r'_+', '_', s_str)
    # Remove leading/trailing underscores
    return s_str.strip('_')

def _capitalize(s: str) -> str:
    """
    Capitalize first character of string.

    Example: capitalize("hello") => "Hello"
    """
    if s is None:
        raise TypeError("_capitalize() received None")
    s_str = str(s)
    return s_str.capitalize()

def _title(s: str) -> str:
    """
    Convert string to title case (capitalize each word).

    Example: title("hello world") => "Hello World"
    """
    if s is None:
        raise TypeError("_title() received None")
    return str(s).title()

DSL_FUNCTIONS = {
    "str":        (_tostring, (1, 1)),
    "lower":      (_lower, (1, 1)),
    "upper":      (_upper, (1, 1)),
    "len":        (_len,   (1, 1)),
    "split":      (_split, (2, 2)),
    "join":       (_join, (2, 2)),
    "trim":       (_trim, (1, 1)),
    "replace":    (_replace, (3, 3)),
    "sha256":     (_sha256, (1, 1)),
    "sha1":       (_sha1, (1, 1)),
    "md5":        (_md5, (1, 1)),
    "match":      (_match, (2, 2)),
    "extract":    (_extract, (2, 3)),
    "padLeft":    (_padLeft, (2, 3)),
    "padRight":   (_padRight, (2, 3)),
    "truncate":   (_truncate, (2, 3)),
    "slugify":    (_slugify, (1, 1)),
    "camelCase":  (_camelCase, (1, 1)),
    "snakeCase":  (_snakeCase, (1, 1)),
    "capitalize": (_capitalize, (1, 1)),
    "title":      (_title, (1, 1)),
}
