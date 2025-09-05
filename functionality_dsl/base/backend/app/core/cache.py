import time
from typing import Any, Callable

def ttl_cache(seconds: int):
    def deco(fn: Callable):
        store = {"ts": 0.0, "val": None}
        async def wrapped(*a, **kw) -> Any:
            now = time.monotonic()
            if now - store["ts"] > seconds:
                store["val"] = await fn(*a, **kw)
                store["ts"] = now
            return store["val"]
        return wrapped
    return deco
