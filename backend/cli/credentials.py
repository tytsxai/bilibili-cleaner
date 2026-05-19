from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

DEFAULT_PATH = Path.home() / ".bilibili-cleaner" / "credentials.json"


@dataclass
class Credentials:
    sessdata: str
    bili_jct: str
    mid: int | None = None
    uname: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "sessdata": self.sessdata,
            "bili_jct": self.bili_jct,
            "mid": self.mid,
            "uname": self.uname,
        }


def credentials_path() -> Path:
    override = os.environ.get("BILI_CREDENTIALS_PATH")
    return Path(override) if override else DEFAULT_PATH


def load() -> Credentials | None:
    """Load credentials. Priority:
    1. env vars BILI_SESSDATA + BILI_JCT (always wins if both present)
    2. JSON file at $BILI_CREDENTIALS_PATH or ~/.bilibili-cleaner/credentials.json
    """
    env_sess = os.environ.get("BILI_SESSDATA")
    env_jct = os.environ.get("BILI_JCT")
    if env_sess and env_jct:
        return Credentials(
            sessdata=env_sess,
            bili_jct=env_jct,
            mid=_try_int(os.environ.get("BILI_MID")),
            uname=os.environ.get("BILI_UNAME"),
        )
    path = credentials_path()
    if not path.exists():
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    if not isinstance(raw, dict):
        return None
    sess = raw.get("sessdata")
    jct = raw.get("bili_jct")
    if not sess or not jct:
        return None
    return Credentials(
        sessdata=str(sess),
        bili_jct=str(jct),
        mid=_try_int(raw.get("mid")),
        uname=raw.get("uname"),
    )


def save(creds: Credentials) -> Path:
    path = credentials_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(creds.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    try:
        path.chmod(0o600)
    except OSError:
        pass
    return path


def clear() -> bool:
    path = credentials_path()
    if path.exists():
        path.unlink()
        return True
    return False


def _try_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
