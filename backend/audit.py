"""Append-only audit trail of destructive operations.

Every unfollow / favorite-delete / dynamic-delete / history-clear is written as
one JSON object per line. B 站 offers no undo for any of these, so this file is
the only record of what was removed — keep it if you may need to reconstruct a
follow list or explain what a run actually did.

Failures here never propagate: an unwritable audit file must not abort a clean
that is already half-done. If the sink cannot be opened it is disabled and the
reason is logged once.
"""

from __future__ import annotations

import json
import logging
import time
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any

from .settings import settings

logger = logging.getLogger(__name__)

AUDIT_LOGGER_NAME = "bilibili_cleaner.audit"

_MAX_BYTES = 5 * 1024 * 1024
_BACKUP_COUNT = 5

_sink: logging.Logger | None = None
_initialised = False


def _build_sink() -> logging.Logger | None:
    if not settings.audit_log_enabled:
        return None
    path = Path(settings.audit_log_path).expanduser()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        handler = RotatingFileHandler(
            path, maxBytes=_MAX_BYTES, backupCount=_BACKUP_COUNT, encoding="utf-8"
        )
    except OSError as exc:
        logger.error(
            "Audit log disabled: cannot open %s (%s). Set BILI_AUDIT_LOG_PATH to a "
            "writable location or BILI_AUDIT_LOG_ENABLED=0 to silence this.",
            path,
            exc,
        )
        return None

    handler.setFormatter(logging.Formatter("%(message)s"))
    sink = logging.getLogger(AUDIT_LOGGER_NAME)
    sink.handlers = [handler]
    sink.setLevel(logging.INFO)
    # Audit records are machine-readable JSON; keep them out of the human log.
    sink.propagate = False
    logger.info("Audit log enabled at %s", path)
    return sink


def _get_sink() -> logging.Logger | None:
    global _sink, _initialised
    if not _initialised:
        _sink = _build_sink()
        _initialised = True
    return _sink


def reset_for_tests() -> None:
    """Drop the cached sink so a test can point the audit log elsewhere."""
    global _sink, _initialised
    if _sink is not None:
        for handler in _sink.handlers:
            handler.close()
        _sink.handlers = []
    _sink = None
    _initialised = False


def record(
    action: str,
    target: Any,
    *,
    ok: bool,
    error: str | None = None,
    **extra: Any,
) -> None:
    """Append one audit entry. ``action`` is a dotted verb such as
    ``following.unfollow``; ``target`` identifies what was removed."""
    sink = _get_sink()
    if sink is None:
        return
    entry: dict[str, Any] = {
        "ts": time.time(),
        "action": action,
        "target": target,
        "ok": ok,
    }
    if error:
        entry["error"] = error
    if extra:
        entry.update(extra)
    try:
        sink.info(json.dumps(entry, ensure_ascii=False, default=str))
    except Exception:  # pragma: no cover - defensive, must never break a clean
        logger.exception("Failed to write audit entry for %s", action)
