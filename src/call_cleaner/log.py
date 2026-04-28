"""Rotating file-logger setup for the cleaner."""
from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from . import paths

DEFAULT_MAX_BYTES = 1024 * 1024  # 1 MB
DEFAULT_BACKUP_COUNT = 3


def setup(
    name: str = "call_cleaner",
    logfile: Path | None = None,
    max_bytes: int = DEFAULT_MAX_BYTES,
    backup_count: int = DEFAULT_BACKUP_COUNT,
) -> logging.Logger:
    """Return a configured logger. Idempotent: returns the same logger
    on repeat calls with the same name."""
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger
    if logfile is None:
        logfile = paths.log_path()
    paths.ensure_parent(logfile)
    handler = RotatingFileHandler(
        logfile, maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8"
    )
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    )
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    return logger
