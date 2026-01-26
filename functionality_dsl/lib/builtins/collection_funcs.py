from typing import Callable, Iterable, Any
from functools import reduce as py_reduce

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

def _any(xs: Iterable):
    if xs is None:
        raise TypeError("_any() received None")
    return any(bool(x) for x in xs)


def _all(xs: Iterable):
    if xs is None:
        raise TypeError("_all() received None")
    return all(bool(x) for x in xs)

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

def _reduce(xs: Iterable, fn: Callable, initial=None):
    """
    Reduce array to single value using accumulator function.
    Similar to JavaScript's Array.reduce()

    Example: reduce([1, 2, 3], (acc, x) -> acc + x, 0) => 6
    """
    if xs is None:
        raise TypeError("_reduce() received None")
    xs_list = list(xs)
    if initial is None:
        if not xs_list:
            raise ValueError("reduce() of empty sequence with no initial value")
        return py_reduce(fn, xs_list)
    return py_reduce(fn, xs_list, initial)

def _groupBy(xs: Iterable, fn: Callable):
    """
    Group array items by key extracted via function.
    Returns dict where keys are group identifiers.

    Example: groupBy(users, u -> u["role"]) => {"admin": [...], "user": [...]}
    """
    if xs is None:
        raise TypeError("_groupBy() received None")
    result = {}
    for x in xs:
        key = fn(x)
        if key not in result:
            result[key] = []
        result[key].append(x)
    return result

def _sortBy(xs: Iterable, fn: Callable):
    """
    Sort array by key extracted via function.

    Example: sortBy(products, p -> p["price"])
    """
    if xs is None:
        raise TypeError("_sortBy() received None")
    return sorted(xs, key=fn)

def _unique(xs: Iterable):
    """
    Remove duplicate values from array (preserves order).

    Example: unique([1, 2, 2, 3, 1]) => [1, 2, 3]
    """
    if xs is None:
        raise TypeError("_unique() received None")
    seen = set()
    result = []
    for x in xs:
        # Handle unhashable types (dicts, lists)
        try:
            if x not in seen:
                seen.add(x)
                result.append(x)
        except TypeError:
            # For unhashable types, do linear search
            if x not in result:
                result.append(x)
    return result

def _uniqueBy(xs: Iterable, fn: Callable):
    """
    Remove duplicates by key extracted via function.

    Example: uniqueBy(users, u -> u["email"])
    """
    if xs is None:
        raise TypeError("_uniqueBy() received None")
    seen = set()
    result = []
    for x in xs:
        key = fn(x)
        try:
            if key not in seen:
                seen.add(key)
                result.append(x)
        except TypeError:
            # For unhashable keys, do linear search
            keys = [fn(item) for item in result]
            if key not in keys:
                result.append(x)
    return result

def _chunk(xs: Iterable, size: int):
    """
    Split array into chunks of specified size.

    Example: chunk([1, 2, 3, 4, 5], 2) => [[1, 2], [3, 4], [5]]
    """
    if xs is None:
        raise TypeError("_chunk() received None")
    if size <= 0:
        raise ValueError("chunk() size must be positive")
    xs_list = list(xs)
    return [xs_list[i:i + size] for i in range(0, len(xs_list), size)]

def _concat(*arrays):
    """
    Concatenate multiple arrays into one.

    Example: concat([1, 2], [3, 4], [5]) => [1, 2, 3, 4, 5]
    """
    result = []
    for arr in arrays:
        if arr is None:
            continue
        if not isinstance(arr, (list, tuple)):
            raise TypeError(f"concat() expects arrays, got {type(arr).__name__}")
        result.extend(arr)
    return result


DSL_COLLECTION_FUNCS = {
    "map":      (_map, (2, 2)),
    "filter":   (_filter, (2, 2)),
    "find":     (_find, (2, 2)),
    "any":      (_any, (1, 1)),
    "all":      (_all, (1, 1)),
    "flatten":  (_flatten, (1, 1)),
    "reduce":   (_reduce, (2, 3)),
    "groupBy":  (_groupBy, (2, 2)),
    "sortBy":   (_sortBy, (2, 2)),
    "unique":   (_unique, (1, 1)),
    "uniqueBy": (_uniqueBy, (2, 2)),
    "chunk":    (_chunk, (2, 2)),
    "concat":   (_concat, (1, None)),
}