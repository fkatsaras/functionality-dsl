"""
Logging configuration for FDSL code generation pipeline.

Usage in generator modules:
    from functionality_dsl.api.gen_logging import get_logger
    logger = get_logger(__name__)

The root logger name is "fdsl.gen". Log levels are controlled by the CLI.
"""

import logging
import sys

_LOGGER_NAME = "fdsl.gen"


def get_logger(name: str = None) -> logging.Logger:
    """
    Return a child logger under the fdsl.gen hierarchy.

    Args:
        name: Module __name__, or None for the root fdsl.gen logger.

    Returns:
        logging.Logger instance
    """
    if name is None or name == _LOGGER_NAME:
        return logging.getLogger(_LOGGER_NAME)
    # Strip package prefix for cleaner names, e.g.
    # "functionality_dsl.api.generators.core.auth_generator" -> "fdsl.gen.auth_generator"
    short = name.rsplit(".", 1)[-1]
    return logging.getLogger(f"{_LOGGER_NAME}.{short}")


def configure_gen_logging(verbose: bool = False, quiet: bool = False) -> None:
    """
    Configure the fdsl.gen logger hierarchy.

    Levels:
        --verbose / -v  -> DEBUG   (all scaffold detail)
        (default)       -> INFO    (phase headers + summary lines)
        --quiet / -q    -> WARNING (warnings and errors only)

    Args:
        verbose: Enable DEBUG-level output.
        quiet:   Suppress INFO output (WARNING+ only).
    """
    if verbose:
        level = logging.DEBUG
    elif quiet:
        level = logging.WARNING
    else:
        level = logging.INFO

    root_logger = logging.getLogger(_LOGGER_NAME)
    root_logger.setLevel(level)

    # Avoid duplicate handlers when called multiple times
    if root_logger.handlers:
        return

    handler = logging.StreamHandler(sys.stderr)
    handler.setLevel(level)
    handler.setFormatter(_GenFormatter())
    root_logger.addHandler(handler)

    # Don't propagate to the root logger (keeps output clean)
    root_logger.propagate = False


class _GenFormatter(logging.Formatter):
    """Minimal formatter: just emit the message as-is (generator code already formats tags)."""

    def format(self, record: logging.LogRecord) -> str:
        return record.getMessage()
