from typing import Callable, Iterable

def _map(xs: Iterable, fn: Callable):
    if xs is None:
        raise TypeError("_map() received None")
    return [fn(x) for x in xs]

def _filter(xs: Iterable, fn: Callable):
    if xs is None:
        raise TypeError("_filter() received None")
    return [x for x in xs if fn(x)]

def _find(xs: Iterable, fn: Callable):
    if xs is None:
        raise TypeError("_find() received None")
    for x in xs:
        if fn(x):
            return x
    return None

def _any(xs: Iterable, fn: Callable):
    if xs is None:
        raise TypeError("_any() received None")
    return any(fn(x) for x in xs)

def _all(xs: Iterable, fn: Callable):
    if xs is None:
        raise TypeError("_all() received None")
    return all(fn(x) for x in xs)

def _flatten(xs: Iterable):
    if xs is None:
        raise TypeError("_flatten() received None")
    result = []
    for x in xs:
        if isinstance(x, (list, tuple)):
            result.extend(x)
        else:
            result.append(x)
    return result


DSL_COLLECTION_FUNCS = {
    "map":    (_map, (2, 2)),
    "filter": (_filter, (2, 2)),
    "find":   (_find, (2, 2)),
    "any":    (_any, (2, 2)),
    "all":    (_all, (2, 2)),
    "flatten":(_flatten, (1, 1)),
}