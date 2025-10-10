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
    }

    TAG_REGEX = re.compile(r"\[([A-Z_]+)\]")

    def format(self, record: logging.LogRecord) -> str:
        ts = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(record.created))
        lvl = record.levelname.upper()
        logger_name = record.name
        msg = record.getMessage()

        # Color only tags if supported
        if self.USE_COLOR:
            msg = self._colorize_tags(msg)

        base = f"{ts} : {lvl:<5} : {logger_name} : {msg}"

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
    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(getattr(logging, level.upper(), logging.INFO))

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(StructuredFormatter())
    root.addHandler(handler)


def set_request_id(value: str) -> None:
    request_id_cv.set(value)
