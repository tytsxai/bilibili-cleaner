"""Runtime configuration read from environment variables.

Everything here has a working default, so an operator can run the service with
zero configuration. Values are read once at import time; restart the process to
pick up changes. Kept deliberately small — no config files, no framework.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

ENV_PREFIX = "BILI_"


def _env(name: str) -> str | None:
    value = os.environ.get(ENV_PREFIX + name)
    if value is None:
        return None
    value = value.strip()
    return value or None


def _float(name: str, default: float, *, minimum: float | None = None) -> float:
    raw = _env(name)
    if raw is None:
        return default
    try:
        value = float(raw)
    except ValueError:
        return default
    if minimum is not None and value < minimum:
        return default
    return value


def _int(name: str, default: int, *, minimum: int | None = None) -> int:
    raw = _env(name)
    if raw is None:
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    if minimum is not None and value < minimum:
        return default
    return value


def _bool(name: str, default: bool) -> bool:
    raw = _env(name)
    if raw is None:
        return default
    return raw.lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    """Process-wide tunables.

    ``api_qps`` is the single most important knob: it caps the request rate
    against B 站 for the whole process. Raising it increases the chance of
    triggering risk control (-352 / 412).
    """

    api_qps: float
    http_timeout: float
    max_retries: int
    retry_base_delay: float

    log_level: str
    log_requests: bool

    max_running_tasks: int
    max_finished_tasks: int
    max_task_errors: int
    shutdown_grace_seconds: float

    audit_log_enabled: bool
    audit_log_path: str


def load_settings() -> Settings:
    return Settings(
        api_qps=_float("API_QPS", 1.5, minimum=0.01),
        http_timeout=_float("HTTP_TIMEOUT", 10.0, minimum=0.1),
        max_retries=_int("MAX_RETRIES", 3, minimum=0),
        retry_base_delay=_float("RETRY_BASE_DELAY", 1.0, minimum=0.0),
        log_level=(_env("LOG_LEVEL") or "INFO").upper(),
        log_requests=_bool("LOG_REQUESTS", True),
        max_running_tasks=_int("MAX_RUNNING_TASKS", 4, minimum=1),
        max_finished_tasks=_int("MAX_FINISHED_TASKS", 200, minimum=1),
        max_task_errors=_int("MAX_TASK_ERRORS", 200, minimum=1),
        shutdown_grace_seconds=_float("SHUTDOWN_GRACE_SECONDS", 5.0, minimum=0.0),
        audit_log_enabled=_bool("AUDIT_LOG_ENABLED", True),
        audit_log_path=_env("AUDIT_LOG_PATH") or "data/audit.jsonl",
    )


settings = load_settings()
