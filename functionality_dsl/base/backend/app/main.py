# app/main.py
import uuid
import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from contextlib import AsyncExitStack

from app.core.config import settings
from app.api.routers import include_generated_routers
from app.core.http import lifespan_http_client
from app.core.logging import configure_logging, set_request_id

# Configure logging FIRST, before anything else
configure_logging(level=settings.LOG_LEVEL, json_mode=(settings.LOG_FORMAT == "json"))

logger = logging.getLogger("fdsl.main")


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        openapi_url=settings.OPENAPI_URL,
        docs_url=settings.DOCS_URL,
    )

    origins = {*settings.BACKEND_CORS_ORIGINS, *settings.cors_origins()}
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(origins),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def _rid_mw(request: Request, call_next):
        rid = request.headers.get("x-request-id") or uuid.uuid4().hex
        set_request_id(rid)
        request.state.request_id = rid
        response = await call_next(request)
        response.headers["x-request-id"] = rid
        return response

    @app.on_event("startup")
    async def _startup():
        app.state._stack = AsyncExitStack()
        await app.state._stack.enter_async_context(lifespan_http_client())

    @app.on_event("shutdown")
    async def _shutdown():
        await app.state._stack.aclose()

    include_generated_routers(app)

    @app.get("/healthz")
    def health():
        return {"status": "OK"}

    @app.get("/openapi.yaml")
    def get_openapi_yaml():
        """Serve the static OpenAPI YAML specification"""
        from pathlib import Path
        from fastapi.responses import FileResponse

        openapi_file = Path(__file__).parent / "api" / "openapi.yaml"
        if openapi_file.exists():
            return FileResponse(
                openapi_file,
                media_type="application/x-yaml",
                filename="openapi.yaml"
            )
        return {"error": "OpenAPI spec not found"}

    return app


app = create_app()