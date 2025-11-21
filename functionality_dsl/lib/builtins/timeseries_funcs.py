from typing import Callable, Iterable, Union

def _timeWindow(xs: Iterable, start_ts: Union[int, float], end_ts: Union[int, float], time_field: str = "ts"):
    """
    Filter array to items within time range.
    Timestamps can be Unix timestamps (seconds or milliseconds).

    Example: timeWindow(readings, now() - 3600, now(), "timestamp")
    """
    if xs is None:
        raise TypeError("_timeWindow() received None")

    result = []
    for item in xs:
        if isinstance(item, dict):
            ts = item.get(time_field)
        else:
            ts = getattr(item, time_field, None)

        if ts is not None and start_ts <= ts <= end_ts:
            result.append(item)

    return result

def _movingAvg(xs: Iterable, window: int):
    """
    Calculate moving average with specified window size.
    Returns array of same length with averaged values.

    Example: movingAvg([1, 2, 3, 4, 5], 3) => [1.0, 1.5, 2.0, 3.0, 4.0]
    """
    if xs is None:
        raise TypeError("_movingAvg() received None")
    if window <= 0:
        raise ValueError("movingAvg() window must be positive")

    xs_list = list(xs)
    if not xs_list:
        return []

    result = []
    for i in range(len(xs_list)):
        start = max(0, i - window + 1)
        window_data = xs_list[start:i + 1]
        avg = sum(window_data) / len(window_data)
        result.append(avg)

    return result

def _exponentialAvg(xs: Iterable, alpha: float):
    """
    Calculate exponential moving average (EMA).
    Alpha is the smoothing factor (0 < alpha <= 1).
    Higher alpha gives more weight to recent values.

    Example: exponentialAvg([1, 2, 3, 4, 5], 0.3)
    """
    if xs is None:
        raise TypeError("_exponentialAvg() received None")
    if not (0 < alpha <= 1):
        raise ValueError("exponentialAvg() alpha must be between 0 and 1")

    xs_list = list(xs)
    if not xs_list:
        return []

    result = [xs_list[0]]
    for i in range(1, len(xs_list)):
        ema = alpha * xs_list[i] + (1 - alpha) * result[-1]
        result.append(ema)

    return result

def _rate(xs: Iterable, value_field: str, time_field: str):
    """
    Calculate rate of change (derivative) between consecutive points.
    Returns array of rates: (value_delta / time_delta).

    Example: rate(readings, "temperature", "ts")
    """
    if xs is None:
        raise TypeError("_rate() received None")

    xs_list = list(xs)
    if len(xs_list) < 2:
        return []

    result = []
    for i in range(1, len(xs_list)):
        prev = xs_list[i - 1]
        curr = xs_list[i]

        if isinstance(prev, dict):
            prev_val = prev.get(value_field)
            prev_time = prev.get(time_field)
        else:
            prev_val = getattr(prev, value_field, None)
            prev_time = getattr(prev, time_field, None)

        if isinstance(curr, dict):
            curr_val = curr.get(value_field)
            curr_time = curr.get(time_field)
        else:
            curr_val = getattr(curr, value_field, None)
            curr_time = getattr(curr, time_field, None)

        if None in (prev_val, prev_time, curr_val, curr_time):
            result.append(None)
            continue

        time_delta = curr_time - prev_time
        if time_delta == 0:
            result.append(0)
        else:
            result.append((curr_val - prev_val) / time_delta)

    return result

def _downsample(xs: Iterable, interval: int):
    """
    Reduce sampling rate by taking every Nth item.

    Example: downsample([1, 2, 3, 4, 5, 6], 2) => [1, 3, 5]
    """
    if xs is None:
        raise TypeError("_downsample() received None")
    if interval <= 0:
        raise ValueError("downsample() interval must be positive")

    return [x for i, x in enumerate(xs) if i % interval == 0]

def _interpolate(xs: Iterable, target_count: int):
    """
    Linear interpolation to create target number of points.
    Useful for upsampling time-series data.

    Example: interpolate([1, 5], 5) => [1.0, 2.0, 3.0, 4.0, 5.0]
    """
    if xs is None:
        raise TypeError("_interpolate() received None")
    if target_count <= 0:
        raise ValueError("interpolate() target_count must be positive")

    xs_list = list(xs)
    if len(xs_list) == 0:
        return []
    if len(xs_list) == 1:
        return xs_list * target_count

    result = []
    step = (len(xs_list) - 1) / (target_count - 1)

    for i in range(target_count):
        pos = i * step
        idx = int(pos)
        frac = pos - idx

        if idx >= len(xs_list) - 1:
            result.append(xs_list[-1])
        else:
            # Linear interpolation
            val = xs_list[idx] * (1 - frac) + xs_list[idx + 1] * frac
            result.append(val)

    return result

def _deltaTime(xs: Iterable, time_field: str = "ts"):
    """
    Calculate time differences between consecutive readings.
    Returns array of deltas.

    Example: deltaTime(readings, "timestamp")
    """
    if xs is None:
        raise TypeError("_deltaTime() received None")

    xs_list = list(xs)
    if len(xs_list) < 2:
        return []

    result = []
    for i in range(1, len(xs_list)):
        prev = xs_list[i - 1]
        curr = xs_list[i]

        if isinstance(prev, dict):
            prev_time = prev.get(time_field)
        else:
            prev_time = getattr(prev, time_field, None)

        if isinstance(curr, dict):
            curr_time = curr.get(time_field)
        else:
            curr_time = getattr(curr, time_field, None)

        if prev_time is not None and curr_time is not None:
            result.append(curr_time - prev_time)
        else:
            result.append(None)

    return result

def _cumulative(xs: Iterable, field: str = None):
    """
    Calculate cumulative sum over time.
    If field is provided, extract value from object; otherwise use values directly.

    Example: cumulative([1, 2, 3, 4]) => [1, 3, 6, 10]
    Example: cumulative(readings, "value") => cumulative sum of "value" field
    """
    if xs is None:
        raise TypeError("_cumulative() received None")

    xs_list = list(xs)
    if not xs_list:
        return []

    result = []
    total = 0

    for item in xs_list:
        if field is not None:
            if isinstance(item, dict):
                val = item.get(field, 0)
            else:
                val = getattr(item, field, 0)
        else:
            val = item

        total += val
        result.append(total)

    return result

def _timeGroupBy(xs: Iterable, interval: int, time_field: str = "ts"):
    """
    Group readings into time buckets.
    Interval is in seconds.
    Returns dict where keys are bucket start timestamps.

    Example: timeGroupBy(readings, 3600, "timestamp")  # Group by hour
    """
    if xs is None:
        raise TypeError("_timeGroupBy() received None")
    if interval <= 0:
        raise ValueError("timeGroupBy() interval must be positive")

    result = {}
    for item in xs:
        if isinstance(item, dict):
            ts = item.get(time_field)
        else:
            ts = getattr(item, time_field, None)

        if ts is not None:
            # Convert to milliseconds if needed (assume > 10^10 is milliseconds)
            if ts > 10000000000:
                ts = ts / 1000

            bucket = int(ts // interval) * interval
            if bucket not in result:
                result[bucket] = []
            result[bucket].append(item)

    return result


DSL_TIMESERIES_FUNCS = {
    "timeWindow":     (_timeWindow, (3, 4)),
    "movingAvg":      (_movingAvg, (2, 2)),
    "exponentialAvg": (_exponentialAvg, (2, 2)),
    "rate":           (_rate, (3, 3)),
    "downsample":     (_downsample, (2, 2)),
    "interpolate":    (_interpolate, (2, 2)),
    "deltaTime":      (_deltaTime, (1, 2)),
    "cumulative":     (_cumulative, (1, 2)),
    "timeGroupBy":    (_timeGroupBy, (2, 3)),
}
