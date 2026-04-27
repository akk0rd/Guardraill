"""
SIEM-ready JSON logging configuration.

Every log record — both operational and audit — is emitted as a single-line
JSON object to stdout.  Log shippers (Filebeat, Fluentd, Logstash, Vector)
can forward these lines directly to Elasticsearch, Splunk, QRadar, Sentinel,
or any other SIEM without transformation.

Usage
-----
Call ``setup_logging()`` once at application startup (done in app/main.py).
After that, all loggers in the process emit JSON automatically.

Environment variables
---------------------
LOG_LEVEL   INFO (default) | DEBUG | WARNING | ERROR
"""

import json
import logging
import os
import sys
from datetime import datetime, timezone
from typing import Any

# Standard LogRecord attributes that must NOT be re-emitted as extra fields.
_STDLIB_ATTRS: frozenset = frozenset(
    {
        "args", "created", "exc_info", "exc_text", "filename", "funcName",
        "levelname", "levelno", "lineno", "message", "module", "msecs",
        "msg", "name", "pathname", "process", "processName",
        "relativeCreated", "stack_info", "taskName", "thread", "threadName",
    }
)


class SiemJsonFormatter(logging.Formatter):
    """
    Formats every LogRecord as a single-line JSON object.

    Fixed top-level fields (always present):
        @timestamp, level, logger, message

    Extra fields passed via ``logging.info(..., extra={...})`` or bound with
    ``logging.LoggerAdapter`` are merged at the top level so SIEM field
    extractors don't need to dig into nested objects.
    """

    def format(self, record: logging.LogRecord) -> str:
        # Render exception traceback into the message if present
        if record.exc_info:
            record.exc_text = self.formatException(record.exc_info)

        obj: dict[str, Any] = {
            "@timestamp": datetime.fromtimestamp(
                record.created, tz=timezone.utc
            ).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        if record.exc_text:
            obj["exception"] = record.exc_text

        # Merge caller-supplied extra fields at top level
        for key, value in record.__dict__.items():
            if key not in _STDLIB_ATTRS and not key.startswith("_"):
                obj[key] = value

        return json.dumps(obj, default=str, ensure_ascii=False)


def setup_logging(level: str | None = None) -> None:
    """
    Replace the root logger's handlers with a single JSON-to-stdout handler.

    Parameters
    ----------
    level:
        Override log level.  Defaults to the ``LOG_LEVEL`` env var or INFO.
    """
    level = level or os.getenv("LOG_LEVEL", "INFO")
    numeric_level = getattr(logging, level.upper(), logging.INFO)

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(SiemJsonFormatter())

    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(numeric_level)

    # Quiet noisy third-party loggers.
    # presidio-analyzer emits WARNING for every entity type that has no
    # recognizer in the requested language (e.g. ES_NIE, IT_PASSPORT when
    # language="en"). These are expected and not actionable.
    for noisy in (
        "uvicorn.access",
        "uvicorn.error",
        "presidio_analyzer",   # underscore variant
        "presidio-analyzer",   # hyphen variant (actual runtime name)
    ):
        logging.getLogger(noisy).setLevel(logging.ERROR)
