import importlib
import pkgutil

from fastapi import FastAPI


def include_generated_routers(app: FastAPI, prefix: str = "/api", package: str = "app.api.routers.generated") -> None:
    """
    Import every module in `app.api.routers.generated` that defines `router`,
    and include it under the given prefix.
    """
    
    try:
        pkg = importlib.import_module(package)
    except ModuleNotFoundError:
        return
    
    for m in pkgutil.iter_modules(pkg.__path__, prefix=package + '.'):
        module = importlib.import_module(m.name)
        router = getattr(module, "router", None)
        if router is not None:
            app.include_router(router=router, prefix="")    # routers already have prefixes