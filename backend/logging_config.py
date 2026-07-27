"""Logging setup.

Without this the application loggers propagate to a root logger that uvicorn
never configures, so ``logger.info`` is silently dropped and warnings fall back
to ``logging.lastResort`` (no timestamp, no logger name). Anything we log for
troubleshooting would be invisible in production.

Call :func:`configure_logging` once at startup. It is idempotent.
"""

from __future__ import annotations

import logging
import sys

from .settings import settings

_LOG_FORMAT = "%(asctime)s %(levelname)-8s %(name)s [%(request_id)s] %(message)s"
_DATE_FORMAT = "%Y-%m-%dT%H:%M:%S%z"

_configured = False


class _RequestIdFilter(logging.Filter):
    """Guarantee every record carries a ``request_id`` so the format string
    never raises for logs emitted outside a request (startup, tasks, CLI)."""

    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "request_id"):
            record.request_id = "-"
        return True


def configure_logging(level: str | None = None) -> None:
    global _configured
    if _configured:
        return

    # stderr, not stdout: the CLI writes JSON to stdout and users pipe it into
    # jq. Docker and systemd capture both streams either way.
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter(_LOG_FORMAT, datefmt=_DATE_FORMAT))
    handler.addFilter(_RequestIdFilter())

    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level or settings.log_level)

    # uvicorn installs its own handlers; route them through ours so the whole
    # process emits one consistent format on stdout.
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        uvicorn_logger = logging.getLogger(name)
        uvicorn_logger.handlers = []
        uvicorn_logger.propagate = True

    if settings.log_requests:
        # Our middleware already logs every request with a request id and a
        # duration; uvicorn's access log would just duplicate each line.
        logging.getLogger("uvicorn.access").setLevel(logging.WARNING)

    # httpx logs every outbound request at INFO with the full URL; that is
    # noise at our request volume and can leak query params into logs.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)

    _configured = True
