# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import AsyncExitStack

from app.core.config import settings
from app.api.routers import include_generated_routers
from app.core.http import lifespan_http_client

def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        openapi_url=settings.OPENAPI_URL,
        docs_url=settings.DOCS_URL
    )

    # CORS
    origins = set(settings.BACKEND_CORS_ORIGINS) | set(settings.BACKEND_CORS_RAW_ORIGINS)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(origins),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

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
