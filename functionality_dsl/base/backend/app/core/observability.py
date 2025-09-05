import time
import uuid
import logging

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("app")
logger.setLevel(logging.INFO)

class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        rid = request.headers.get("x-request-id") or str(uuid.uuid4())
        start = time.perf_counter()
        response = await call_next(request)
        dur_ms = (time.perf_counter() - start) * 1000
        response.headers["x-request-id"] = rid
        logger.info("%s %s %s %.1fms", request.method, request.url.path, response.status_code, dur_ms)
        return response
