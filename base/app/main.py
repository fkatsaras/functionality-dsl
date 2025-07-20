from fastapi import FastAPI
from .database import Base, engine

app = FastAPI(title="FDSL Generated App")

# ---------------------------------------------------------------------------
# Create tables the moment the service boots.
# ---------------------------------------------------------------------------
Base.metadata.create_all(bind=engine)

# ---------------------------------------------------------------------------
# Include the router file that code-gen will drop next to this module.
# ---------------------------------------------------------------------------
try:
    from .router import router as generated_router 
    app.include_router(generated_router)
except ImportError:
    # First run, before code generation, or the DSL had no endpoints yet.
    pass