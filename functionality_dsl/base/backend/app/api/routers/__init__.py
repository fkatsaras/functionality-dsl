from fastapi import FastAPI
import pkgutil
import importlib
import app.api.routers as _pkg

def include_generated_routers(app: FastAPI):
    """
    Auto-import every module in app.api.routers that defines `router`
    and include it as-is (modules already define their own prefixes).
    """
    for _, mod_name, _ in pkgutil.iter_modules(_pkg.__path__):
        # skip __init__.py and any non-.py files, but no prefix filter
        mod = importlib.import_module(f"{_pkg.__name__}.{mod_name}")
        router = getattr(mod, "router", None)
        if router is not None:
            app.include_router(router)