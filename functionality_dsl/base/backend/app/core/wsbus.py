import asyncio
import logging
from typing import Any, Dict, Set, Optional
from fastapi import WebSocket

logger = logging.getLogger("fdsl.wsbus")

# global registry of buses
_buses: Dict[str, "WSBus"] = {}


class WSBus:
    def __init__(self, name: str, keep_last: bool = True, content_type: str = "application/json", message_type: str = "object"):
        self.name = name
        self.keep_last = keep_last
        self.content_type = content_type  # Content type for serialization
        self.message_type = message_type  # Message type (object, string, array, etc.)
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
        """Send message to all connected subscribers using appropriate content type."""
        from app.core.content_handler import ContentTypeHandler

        dead = []

        for ws in list(self.subscribers):
            try:
                # Serialize message according to content type
                await self._send_message(ws, msg, self.content_type)
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

    async def _send_message(self, ws: WebSocket, msg: Any, content_type: str):
        """Send message via WebSocket using appropriate format for content type."""
        from app.core.content_handler import ContentTypeHandler

        # PRIMITIVE_TYPES that need unwrapping
        PRIMITIVE_TYPES = ['string', 'number', 'integer', 'boolean', 'array', 'binary']

        # Unwrap primitive messages (extract from wrapper entity)
        unwrapped_msg = msg
        if self.message_type in PRIMITIVE_TYPES and isinstance(msg, dict) and len(msg) > 0:
            # Extract first value from wrapper entity
            unwrapped_msg = next(iter(msg.values()), None)
            logger.debug(f"[WSBUS] Unwrapped {self.message_type} message from wrapper entity")

        # Send based on content type
        if ContentTypeHandler.is_binary(content_type):
            # Binary data
            if isinstance(unwrapped_msg, (bytes, bytearray)):
                await ws.send_bytes(bytes(unwrapped_msg))
            elif isinstance(msg, dict):
                # Fallback: extract from dict if unwrapping didn't work
                binary_data = next(iter(msg.values()), b"")
                if isinstance(binary_data, (bytes, bytearray)):
                    await ws.send_bytes(bytes(binary_data))
            else:
                logger.warning(f"[WSBUS] Expected binary data, got {type(unwrapped_msg)}")
                await ws.send_bytes(b"")

        elif content_type == "text/plain":
            # Plain text
            await ws.send_text(str(unwrapped_msg))

        else:
            # JSON (default)
            # For object types, send the full dict; for primitives, send unwrapped value
            if self.message_type == "object":
                await ws.send_json(msg)  # Keep object as-is
            else:
                await ws.send_json(unwrapped_msg)  # Send unwrapped primitive

    async def add_ws(self, ws: WebSocket):
        """Register a subscriber and send last message if available."""
        async with self._lock:
            self.subscribers.add(ws)

            # Send latest snapshot to new subscriber
            if self.keep_last and self.last_message is not None:
                try:
                    await self._send_message(ws, self.last_message, self.content_type)
                    logger.debug("sent_last_message", extra={
                        "bus": self.name,
                        "subscriber": id(ws),
                        "content_type": self.content_type
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


def get_bus(name: str, keep_last: bool = True, content_type: str = "application/json", message_type: str = "object") -> WSBus:
    """Get or create a message bus by name with specified content type and message type."""
    if name not in _buses:
        _buses[name] = WSBus(name, keep_last=keep_last, content_type=content_type, message_type=message_type)
    return _buses[name]