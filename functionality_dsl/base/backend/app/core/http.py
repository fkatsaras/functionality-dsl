import httpx
import asyncio

from contextlib import asynccontextmanager
from typing import AsyncIterator


DEFAULT_TIMEOUT = httpx.Timeout(connect=5.0, read=10.0, write=10.0, pool=10.0)
_IDEMPOTENT = {"GET", "HEAD", "OPTIONS"}

class RetryTransport(httpx.AsyncHTTPTransport):
    """Retry idempotent requests on connect/read timeout with exponential backoff."""
    def __init__(self, retries: int = 2, backoff: float = 0.2, **kw):
        super().__init__(**kw)
        self.retries = retries
        self.backoff = backoff

    async def handle_async_request(self, request):
        for attempt in range(self.retries + 1):
            try:
                return await super().handle_async_request(request)
            except (httpx.ConnectError, httpx.ReadTimeout):
                if request.method not in _IDEMPOTENT or attempt == self.retries:
                    raise
                await asyncio.sleep(self.backoff * (2 ** attempt))

_client: httpx.AsyncClient | None = None

@asynccontextmanager
async def lifespan_http_client() -> AsyncIterator[httpx.AsyncClient]:
    global _client
    async with httpx.AsyncClient(
        timeout=DEFAULT_TIMEOUT,
        transport=RetryTransport(),
        follow_redirects=True,
    ) as client:
        _client = client
        yield client  # closed automatically on exit

def get_http_client() -> httpx.AsyncClient:
    assert _client is not None, "HTTP client not initialized (startup not run)."
    return _client