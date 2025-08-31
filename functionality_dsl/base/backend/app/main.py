from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.routers import include_generated_routers


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
    
    # Mount generated routers under /api
    include_generated_routers(app)
    
    @app.get("/healthz")
    def health():
        return {"status": "OK"}
    
    return app

app = create_app()