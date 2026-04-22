"""Centralized logging configuration for PopHealth Observatory."""

from __future__ import annotations

import logging
import os
from typing import TextIO

_LOGGER_NAME = "pophealth_observatory"
_DEFAULT_LEVEL = "INFO"
_DEFAULT_FORMAT = "%(asctime)s level=%(levelname)s logger=%(name)s message=%(message)s"


def _normalize_level(level_name: str | None) -> int:
    candidate = (level_name or _DEFAULT_LEVEL).upper()
    level = getattr(logging, candidate, None)
    if isinstance(level, int):
        return level
    return logging.INFO


def configure_logging(level: str | None = None, stream: TextIO | None = None) -> logging.Logger:
    """Configure package logging in an idempotent, notebook-safe way.

    Parameters
    ----------
    level : str | None
        Logging level name. If omitted, reads LOGLEVEL from environment.
    stream : TextIO | None
        Optional stream for log output (primarily for tests).

    Returns
    -------
    logging.Logger
        Configured package logger.
    """
    logger = logging.getLogger(_LOGGER_NAME)
    resolved_level = _normalize_level(level or os.getenv("LOGLEVEL", _DEFAULT_LEVEL))
    logger.setLevel(resolved_level)

    if not logger.handlers:
        handler = logging.StreamHandler(stream)
        handler.setFormatter(logging.Formatter(_DEFAULT_FORMAT))
        logger.addHandler(handler)

    # Avoid duplicate output from root logger handlers in notebooks/apps.
    logger.propagate = False
    return logger
