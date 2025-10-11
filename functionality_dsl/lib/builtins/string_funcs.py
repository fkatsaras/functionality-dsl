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

DSL_FUNCTIONS = {
    "lower": (_lower, (1, 1)),
    "upper": (_upper, (1, 1)),
    "len":   (_len,   (1, 1)),
    "split": (_split, (2, 2)),
    "join": (_join, (2, 2)),
    "trim": (_trim, (1, 1)),
    "replace": (_replace, (3, 3)),
}
