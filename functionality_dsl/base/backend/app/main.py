# app/main.py
import uuid

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from contextlib import AsyncExitStack

from app.core.config import settings
from app.api.routers import include_generated_routers
from app.core.http import lifespan_http_client
from app.core.logging import configure_logging, set_request_id


def create_app() -> FastAPI:
    
    configure_logging(level="INFO", json_mode=True)
    
    app = FastAPI(
        title=settings.APP_NAME,
        openapi_url=settings.OPENAPI_URL,
        docs_url=settings.DOCS_URL
    )

    # CORS
    origins = { *settings.BACKEND_CORS_ORIGINS, *settings.cors_origins() }
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
        resp = await call_next(request)
        # mirror id so proxies/logs correlate
        resp.headers["x-request-id"] = rid
        return resp
    
    # NOTE: For WebSocket, we set request_id inside routers on accept()

    # Lifespan resources (HTTP client, etc.)
    @app.on_event("startup")
    async def _startup():
        app.state._stack = AsyncExitStack()
        await app.state._stack.enter_async_context(lifespan_http_client())

    @app.on_event("shutdown")
    async def _shutdown():
        await app.state._stack.aclose()

    # Mount generated routers under /api
    include_generated_routers(app)

    @app.get("/healthz")
    def health():
        return {"status": "OK"}

    return app

app = create_app()
