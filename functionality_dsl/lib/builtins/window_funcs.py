from typing import Callable, Iterable

def _window(xs: Iterable, size: int, step: int = 1):
    """
    Create sliding windows over array.
    Size is window size, step is how many elements to skip between windows.

    Example: window([1, 2, 3, 4, 5], 3, 1) => [[1,2,3], [2,3,4], [3,4,5]]
    Example: window([1, 2, 3, 4, 5], 2, 2) => [[1,2], [3,4]]
    """
    if xs is None:
        raise TypeError("_window() received None")
    if size <= 0:
        raise ValueError("window() size must be positive")
    if step <= 0:
        raise ValueError("window() step must be positive")

    xs_list = list(xs)
    result = []

    for i in range(0, len(xs_list) - size + 1, step):
        result.append(xs_list[i:i + size])

    return result

def _tumblingWindow(xs: Iterable, size: int):
    """
    Create non-overlapping (tumbling) windows.
    Same as window(xs, size, size).

    Example: tumblingWindow([1, 2, 3, 4, 5, 6], 2) => [[1,2], [3,4], [5,6]]
    """
    return _window(xs, size, size)

def _distinctCount(xs: Iterable, field: str = None) -> int:
    """
    Count distinct/unique values.
    If field provided, counts distinct values of that field.

    Example: distinctCount([1, 2, 2, 3, 1]) => 3
    Example: distinctCount(users, "email") => count of unique emails
    """
    if xs is None:
        raise TypeError("_distinctCount() received None")

    seen = set()
    for item in xs:
        if field is not None:
            if isinstance(item, dict):
                val = item.get(field)
            else:
                val = getattr(item, field, None)
        else:
            val = item

        # Handle unhashable types
        try:
            seen.add(val)
        except TypeError:
            # For unhashable types, do linear search
            if val not in [v for v in seen]:
                seen.add(str(val))  # Convert to string for hashing

    return len(seen)

def _topN(xs: Iterable, n: int, key_fn: Callable = None):
    """
    Get top N elements (largest values).
    If key_fn provided, sorts by that key.

    Example: topN([1, 5, 3, 9, 2], 3) => [9, 5, 3]
    Example: topN(products, 3, p -> p["price"]) => 3 most expensive products
    """
    if xs is None:
        raise TypeError("_topN() received None")
    if n < 0:
        raise ValueError("topN() n must be non-negative")

    xs_list = list(xs)

    if key_fn is not None:
        sorted_xs = sorted(xs_list, key=key_fn, reverse=True)
    else:
        sorted_xs = sorted(xs_list, reverse=True)

    return sorted_xs[:n]

def _bottomN(xs: Iterable, n: int, key_fn: Callable = None):
    """
    Get bottom N elements (smallest values).
    If key_fn provided, sorts by that key.

    Example: bottomN([1, 5, 3, 9, 2], 3) => [1, 2, 3]
    Example: bottomN(products, 3, p -> p["price"]) => 3 cheapest products
    """
    if xs is None:
        raise TypeError("_bottomN() received None")
    if n < 0:
        raise ValueError("bottomN() n must be non-negative")

    xs_list = list(xs)

    if key_fn is not None:
        sorted_xs = sorted(xs_list, key=key_fn)
    else:
        sorted_xs = sorted(xs_list)

    return sorted_xs[:n]

def _sample(xs: Iterable, n: int):
    """
    Randomly sample n elements from array (without replacement).

    Example: sample([1, 2, 3, 4, 5], 3) => [2, 5, 1] (random)
    """
    if xs is None:
        raise TypeError("_sample() received None")
    if n < 0:
        raise ValueError("sample() n must be non-negative")

    import random
    xs_list = list(xs)

    if n >= len(xs_list):
        return xs_list.copy()

    return random.sample(xs_list, n)

def _partition(xs: Iterable, predicate: Callable):
    """
    Partition array into two arrays: [matching, not_matching].

    Example: partition([1, 2, 3, 4, 5], x -> x > 3) => [[4, 5], [1, 2, 3]]
    """
    if xs is None:
        raise TypeError("_partition() received None")

    matching = []
    not_matching = []

    for item in xs:
        if predicate(item):
            matching.append(item)
        else:
            not_matching.append(item)

    return [matching, not_matching]


DSL_WINDOW_FUNCS = {
    "window":          (_window, (2, 3)),
    "tumblingWindow":  (_tumblingWindow, (2, 2)),
    "distinctCount":   (_distinctCount, (1, 2)),
    "topN":            (_topN, (2, 3)),
    "bottomN":         (_bottomN, (2, 3)),
    "sample":          (_sample, (2, 2)),
    "partition":       (_partition, (2, 2)),
}
