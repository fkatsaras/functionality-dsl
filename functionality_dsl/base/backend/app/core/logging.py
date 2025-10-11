# app/core/logging.py
from __future__ import annotations

import logging
import sys
import time
import contextvars
import os
import re


class CLIColorCodes:
    GREEN = "\033[32m"
    RED = "\033[31m"
    YELLOW = "\033[33m"
    ORANGE = "\033[38;5;208m"
    CYAN = "\033[36m"
    RESET = "\033[0m"


request_id_cv = contextvars.ContextVar("request_id", default="-")


class StructuredFormatter(logging.Formatter):
    USE_COLOR = sys.stdout.isatty() or os.getenv("FORCE_COLOR") == "1"

    TAG_COLORS = {
        "ERROR": CLIColorCodes.RED,
        "REQUEST": CLIColorCodes.YELLOW,
        "FETCH": CLIColorCodes.ORANGE,
        "DEPENDENCY": CLIColorCodes.CYAN,
        "TRANSFORM": CLIColorCodes.CYAN,
        "COMPUTE": CLIColorCodes.GREEN,
        "SUCCESS": CLIColorCodes.GREEN,
        "CONTEXT": CLIColorCodes.ORANGE,
        "FORWARD": CLIColorCodes.YELLOW,
        "PAYLOAD": CLIColorCodes.CYAN,
        "INLINE": CLIColorCodes.CYAN,
        "SHAPE": CLIColorCodes.CYAN,
        "RESULT": CLIColorCodes.GREEN,
    }

    TAG_REGEX = re.compile(r"\[([A-Z_]+)\]")

    def format(self, record: logging.LogRecord) -> str:
        ts = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(record.created))
        lvl = record.levelname.upper()
        logger_name = record.name
        msg = record.getMessage()
        
        # Include request ID if available
        rid = request_id_cv.get()
        rid_str = f" [{rid[:8]}]" if rid != "-" else ""

        # Color only tags if supported
        if self.USE_COLOR:
            msg = self._colorize_tags(msg)

        base = f"{ts} : {lvl:<5} : {logger_name}{rid_str} : {msg}"

        if record.exc_info:
            base += f"\n{self.formatException(record.exc_info)}"

        return base

    def _colorize_tags(self, msg: str) -> str:
        """Replaces recognized tags like [ERROR] with colored equivalents."""

        def replace_tag(match: re.Match) -> str:
            tag = match.group(1)
            color = self.TAG_COLORS.get(tag, CLIColorCodes.RESET)
            return f"{color}[{tag}]{CLIColorCodes.RESET}"

        return self.TAG_REGEX.sub(replace_tag, msg)


def configure_logging(level: str = "INFO", *, json_mode: bool = False):
    """Configure logging for the entire application."""
    # Convert string level to numeric
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    
    # Configure root logger
    root = logging.getLogger()
    root.handlers.clear()  # remove any existing handlers
    root.setLevel(numeric_level)

    # Create console handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(numeric_level)
    handler.setFormatter(StructuredFormatter())
    root.addHandler(handler)

    # Configure specific loggers
    # Set uvicorn loggers to WARNING to reduce noise (unless DEBUG is requested)
    uvicorn_level = numeric_level if numeric_level == logging.DEBUG else logging.WARNING
    logging.getLogger("uvicorn").setLevel(uvicorn_level)
    logging.getLogger("uvicorn.error").setLevel(uvicorn_level)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)  # Always WARNING for access logs
    
    # Set httpx to INFO minimum (to see HTTP requests)
    httpx_level = max(numeric_level, logging.INFO)
    logging.getLogger("httpx").setLevel(httpx_level)
    
    # Keep fastapi at INFO minimum
    logging.getLogger("fastapi").setLevel(max(numeric_level, logging.INFO))
    
    # Ensure all fdsl.router.* loggers inherit from root
    logging.getLogger("fdsl").setLevel(numeric_level)
    
    # Log the configuration (do this at the end to ensure handler is attached)
    logger = logging.getLogger("fdsl.core")
    logger.info(f"[CONFIG] Logging initialized: level={level.upper()}")


def set_request_id(value: str) -> None:
    request_id_cv.set(value)