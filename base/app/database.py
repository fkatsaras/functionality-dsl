"""
Central SQLAlchemy setup that the generated code re-uses.

- `engine`           : global Engine created from DATABASE_URL
- `SessionLocal()`   : session factory (FastAPI dependency)
- `Base`             : declarative base that every generated model inherits from
"""

from __future__ import annotations
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# --------------------------------------------------------------------------- #
# 1) connection string – default to Postgres                                  #
#    Users can still export DATABASE_URL=postgresql+psycopg://user:pass@host/db
# --------------------------------------------------------------------------- #
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg://postgres:postgres@localhost:5432/appdb",
)

connect_args: dict = {}

engine = create_engine(
    DATABASE_URL,
    echo=False,
    future=True,
    connect_args=connect_args,
)

# --------------------------------------------------------------------------- #
# 2) Session factory + declarative base                                       #
# --------------------------------------------------------------------------- #
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()