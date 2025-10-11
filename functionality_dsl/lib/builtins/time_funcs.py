import time

def _now() -> int:
    """Current time in ms."""
    return int(time.time() * 1000)

DSL_FUNCTIONS = {
    "now": (_now, (0, 0)),
}
