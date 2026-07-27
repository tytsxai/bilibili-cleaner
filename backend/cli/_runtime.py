from __future__ import annotations

import asyncio
import json
import sys
from collections.abc import AsyncIterator, Awaitable
from contextlib import asynccontextmanager
from typing import Any, TypeVar

import typer

from backend.api import BiliApiClient

from . import credentials

DEFAULT_QPS = 1.5

T = TypeVar("T")


def require_credentials() -> credentials.Credentials:
    creds = credentials.load()
    if creds is None:
        typer.echo(
            "No credentials found. Run `bilibili-cleaner login` or set "
            "BILI_SESSDATA / BILI_JCT env vars.",
            err=True,
        )
        raise typer.Exit(code=1)
    return creds


@asynccontextmanager
async def make_client(qps: float | None = DEFAULT_QPS) -> AsyncIterator[BiliApiClient]:
    creds = require_credentials()
    async with BiliApiClient(
        sessdata=creds.sessdata,
        bili_jct=creds.bili_jct,
        qps=qps,
    ) as client:
        yield client


def run_async(coro: Awaitable[T]) -> T:
    return asyncio.run(coro)


def emit(obj: Any, *, json_output: bool = True) -> None:
    """Print ``obj`` as JSON (default) for machine consumers, or as a pretty
    repr if ``json_output=False``. AI agents should leave the default on."""
    if json_output:
        json.dump(obj, sys.stdout, ensure_ascii=False, indent=2, default=str)
        sys.stdout.write("\n")
    else:
        typer.echo(repr(obj))
