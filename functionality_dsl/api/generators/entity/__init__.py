"""
Entity-centric generators for NEW SYNTAX (v2 - entity exposure).

DESIGN PHILOSOPHY:
==================
REST and WebSocket are treated symmetrically:
- Both use `operations:` to define behavior (REST: list/read/create/update/delete, WS: subscribe/publish)
- Both auto-generate paths from entity names (no manual URIs)
- Both support entity transformations (parent entities with computed attributes)
- Sources declare connection only (REST: url, WS: channel)

SEPARATION OF CONCERNS:
=======================
1. router_generator.py       - Generates REST API routers (FastAPI)
2. websocket_router_generator.py - Generates WebSocket routers (FastAPI WebSocket)
3. service_generator.py       - Generates service layer (shared by REST and WS)

REST Flow:
----------
Entity -> operations: [list, read, create, update, delete]
-> router_generator -> FastAPI HTTP endpoints
-> service_generator -> Service methods (CRUD)
-> source client -> External REST API

WebSocket Flow:
--------------
Entity -> operations: [subscribe, publish]
-> websocket_router_generator -> FastAPI WebSocket endpoints
-> service_generator -> Service methods (message transformation)
-> source client -> External WebSocket connection
"""

from .router_generator import generate_entity_router
from .service_generator import generate_entity_service
from .websocket_router_generator import generate_entity_websocket_router

__all__ = [
    "generate_entity_router",
    "generate_entity_service",
    "generate_entity_websocket_router",
]
