from __future__ import annotations

import logging
from pythonjsonlogger.json import JsonFormatter

from app.config import get_settings


def configure_logging() -> None:
    settings = get_settings()
    root = logging.getLogger()
    root.setLevel(settings.log_level.upper())

    if not root.handlers:
        handler = logging.StreamHandler()
        formatter = JsonFormatter(
            "%(asctime)s %(levelname)s %(name)s %(message)s %(request_id)s %(path)s %(method)s %(status_code)s %(duration_ms)s"
        )
        handler.setFormatter(formatter)
        root.addHandler(handler)
    else:
        for h in root.handlers:
            if h.formatter is None:
                h.setFormatter(JsonFormatter())
