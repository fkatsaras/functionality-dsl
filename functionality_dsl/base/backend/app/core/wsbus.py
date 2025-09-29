import asyncio
import logging
from typing import Any, Dict, Set, Optional
from fastapi import WebSocket

logger = logging.getLogger("fdsl.wsbus")

# global registry of buses
_buses: Dict[str, "WSBus"] = {}


class WSBus:
    def __init__(self, name: str, keep_last: bool = True):
        self.name = name
        self.keep_last = keep_last
        self.last_message: Optional[Any] = None
        self.subscribers: Set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def publish(self, msg: Any):
        """Broadcast message to all subscribers and optionally store last message."""
        async with self._lock:
            if self.keep_last:
                self.last_message = msg
            await self._broadcast(msg)

    async def _broadcast(self, msg: Any):
        """Send message to all connected subscribers."""
        dead = []
        for ws in list(self.subscribers):
            try:
                await ws.send_json(msg)
            except Exception as ex:
                logger.debug("broadcast_failed", extra={
                    "bus": self.name,
                    "err": repr(ex)
                })
                dead.append(ws)
        
        # Clean up dead connections
        for ws in dead:
            self.subscribers.discard(ws)
        
        if dead:
            logger.debug("removed_dead_clients", extra={
                "bus": self.name,
                "removed": len(dead),
                "remaining": len(self.subscribers)
            })

    async def add_ws(self, ws: WebSocket):
        """Register a subscriber and send last message if available."""
        async with self._lock:
            self.subscribers.add(ws)
            
            # Send latest snapshot to new subscriber
            if self.keep_last and self.last_message is not None:
                try:
                    await ws.send_json(self.last_message)
                    logger.debug("sent_last_message", extra={
                        "bus": self.name,
                        "subscriber": id(ws)
                    })
                except Exception as ex:
                    logger.debug("failed_send_last", extra={
                        "bus": self.name,
                        "err": repr(ex)
                    })
                    self.subscribers.discard(ws)

    async def remove_ws(self, ws: WebSocket):
        """Unregister a subscriber."""
        async with self._lock:
            self.subscribers.discard(ws)
            logger.debug("subscriber_removed", extra={
                "bus": self.name,
                "remaining": len(self.subscribers)
            })


def get_bus(name: str, keep_last: bool = True) -> WSBus:
    """Get or create a message bus by name."""
    if name not in _buses:
        _buses[name] = WSBus(name, keep_last=keep_last)
    return _buses[name]