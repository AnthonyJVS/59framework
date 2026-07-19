"""Central logging configuration for the framework."""

from __future__ import annotations

import logging
import os
import sys

_FORMAT = "%(asctime)s %(levelname)-7s %(name)s: %(message)s"
_configured = False


def get_logger(name: str) -> logging.Logger:
    """Return a namespaced logger; configures the root framework handler once.

    Level is controlled by the ``LOG_LEVEL`` env var (default ``INFO``).
    """
    global _configured
    if not _configured:
        root = logging.getLogger("framework")
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter(_FORMAT))
        root.addHandler(handler)
        root.setLevel(os.environ.get("LOG_LEVEL", "INFO").upper())
        root.propagate = False
        _configured = True
    return logging.getLogger(f"framework.{name}")
