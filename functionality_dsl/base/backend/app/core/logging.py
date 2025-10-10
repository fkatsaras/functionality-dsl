from __future__ import annotations

import logging
import sys
import time
import contextvars

request_id_cv = contextvars.ContextVar("request_id", default="-")

class StructuredFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        ts = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(record.created))
        lvl = record.levelname.upper()
        logger_name = record.name
        msg = record.getMessage()

        # Format 
        base = f"{ts} : {lvl:<5} : {logger_name} : {msg}"

        # Append exception info if present
        if record.exc_info:
            exc_text = self.formatException(record.exc_info)
            base += f"\n{exc_text}"

        return base

def configure_logging(level: str = "INFO", *, json_mode: bool = False):
    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(getattr(logging, level.upper(), logging.INFO))

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(StructuredFormatter())
    root.addHandler(handler)

def set_request_id(value: str) -> None:
    request_id_cv.set(value)
