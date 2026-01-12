# app/main.py
import uuid
import logging
from fastapi import FastAPI, Request, Response, Cookie
from fastapi.middleware.cors import CORSMiddleware
from contextlib import AsyncExitStack
from typing import Optional

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

    # Register auth routes if auth module exists
    try:
        from app.core.auth import (
            login_handler, logout_handler, me_handler,
            LoginRequest, LoginResponse, LogoutResponse,
            get_current_user, TokenPayload, SESSION_COOKIE_NAME
        )
        from fastapi import Depends

        @app.post("/auth/login", response_model=LoginResponse, tags=["Auth"])
        async def login(request: LoginRequest, response: Response):
            """Login and create a session"""
            return await login_handler(request, response)

        @app.post("/auth/logout", response_model=LogoutResponse, tags=["Auth"])
        async def logout(response: Response, session_id: Optional[str] = Cookie(None)):
            """Logout and clear session"""
            return await logout_handler(response, session_id)

        @app.get("/auth/me", tags=["Auth"])
        async def me(user: TokenPayload = Depends(get_current_user)):
            """Get current user info"""
            return await me_handler(user)

        logger.info("Auth routes registered: /auth/login, /auth/logout, /auth/me")
    except ImportError as e:
        logger.debug(f"No auth module found - skipping auth routes: {e}")

    @app.get("/")
    def root():
        """API root with links to documentation"""
        return {
            "status": "OK",
            "message": "FDSL-generated API",
            "docs": {
                "openapi": {
                    "interactive": settings.DOCS_URL or "/docs",
                    "spec": "/openapi.yaml"
                },
                "asyncapi": {
                    "interactive": "/asyncapi",
                    "spec": "/asyncapi.yaml"
                }
            }
        }

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

    @app.get("/asyncapi.yaml", include_in_schema=False)
    def get_asyncapi_yaml():
        """Serve the static AsyncAPI YAML specification"""
        from pathlib import Path
        from fastapi.responses import FileResponse

        asyncapi_file = Path(__file__).parent / "api" / "asyncapi.yaml"
        if asyncapi_file.exists():
            return FileResponse(
                asyncapi_file,
                media_type="application/x-yaml",
                filename="asyncapi.yaml"
            )
        return {"error": "AsyncAPI spec not found"}

    @app.get("/asyncapi", include_in_schema=False)
    def get_asyncapi_docs():
        """Serve interactive AsyncAPI documentation (similar to /docs for OpenAPI)"""
        from pathlib import Path

        from fastapi.responses import FileResponse

        template_file = Path(__file__).parent / "templates" / "asyncapi.html"
        if template_file.exists():
            return FileResponse(template_file, media_type="text/html")
        return {"error": "AsyncAPI documentation template not found"}

    return app


app = create_app()