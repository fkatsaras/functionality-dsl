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

DSL_FUNCTIONS = {
    "str":   (_tostring, (1, 1)),
    "lower": (_lower, (1, 1)),
    "upper": (_upper, (1, 1)),
    "len":   (_len,   (1, 1)),
    "split": (_split, (2, 2)),
    "join": (_join, (2, 2)),
    "trim": (_trim, (1, 1)),
    "replace": (_replace, (3, 3)),
    "sha256": (_sha256, (1, 1)),
    "sha1": (_sha1, (1, 1)),
    "md5": (_md5, (1, 1)),
}
