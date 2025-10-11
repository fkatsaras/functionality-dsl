# app/core/config.py
from pydantic_settings import BaseSettings
from pydantic import AnyHttpUrl
from typing import List

class Settings(BaseSettings):
    APP_NAME: str = "FunctionalityDSL Backend"
    API_PREFIX: str = "/api"
    DOCS_URL: str = "/docs"
    OPENAPI_URL: str = "/openapi.json"
    LOG_LEVEL: str = "DEBUG"
    LOG_FORMAT: str = "json"

    # CORS
    BACKEND_CORS_ORIGINS: List[AnyHttpUrl] = []
    BACKEND_CORS_RAW_ORIGINS: str = ""

    # Upstream defaults (internal proxy calls)
    SERVER_HOST: str = "localhost"
    SERVER_PORT: int = 8080

    def cors_origins(self):
        return [o.strip() for o in self.BACKEND_CORS_RAW_ORIGINS.split(",") if o.strip()]

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
