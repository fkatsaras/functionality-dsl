from pydantic import BaseSettings, AnyHttpUrl
from typing import List

class Settings(BaseSettings):
    APP_NAME: str = "FunctionalityDSL Backend"
    API_PREFIX: str = "/api"
    DOCS_URL: str = "/docs"
    OPENAPI_URL: str = "/openapi.json"
    
    # CORS
    BACKEND_CORS_ORIGINS: List[AnyHttpUrl] = []
    BACKEND_CORS_RAW_ORIGINS: List[str] = ["http://localhost:3000"]
    
    # Upstream defaults (internall proxy calls)
    SERVER_HOST: str = "localhost"
    SERVER_PORT: int = 8080
    
    class Config:
        env_file = ".env"
        
settings = Settings() 