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

DSL_FUNCTIONS = {
    "lower": (_lower, (1, 1)),
    "upper": (_upper, (1, 1)),
    "len":   (_len,   (1, 1)),
}
