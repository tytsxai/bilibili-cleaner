from __future__ import annotations

import typer

from backend.services import FollowingService

from .. import credentials
from .._runtime import emit, make_client, run_async

app = typer.Typer(help="List / inspect / unfollow following accounts.")


def _resolve_mid(explicit: int | None) -> int:
    if explicit is not None:
        return explicit
    creds = credentials.load()
    if creds and creds.mid:
        return creds.mid
    typer.echo(
        "No mid given. Pass --mid or run `bilibili-cleaner auth login` first.",
        err=True,
    )
    raise typer.Exit(code=1)


@app.command("list")
def list_cmd(
    mid: int | None = typer.Option(
        None, help="The owning account's mid; defaults to logged-in user."
    ),
    page: int = typer.Option(1),
    page_size: int = typer.Option(50, min=1, max=50),
    with_detail: bool = typer.Option(False, help="Also fetch profile + latest video (slower)."),
    concurrency: int = typer.Option(3, min=1, max=10),
    json_output: bool = typer.Option(True, "--json/--pretty"),
) -> None:
    """List one page of followings, optionally enriched with profile + stat + last video."""
    real_mid = _resolve_mid(mid)

    async def run() -> None:
        async with make_client() as client:
            service = FollowingService(client)
            data = await service.list_page(real_mid, page=page, page_size=page_size)
            items = data.get("list") if isinstance(data, dict) else []
            items = [i for i in items if isinstance(i, dict)] if isinstance(items, list) else []
            if with_detail and items:
                details = await service.enrich(
                    [int(i["mid"]) for i in items if "mid" in i],
                    concurrency=concurrency,
                )
                by_mid = {d["mid"]: d for d in details}
                for item in items:
                    if "mid" in item:
                        item["detail"] = by_mid.get(int(item["mid"]))
            payload = {
                "page": page,
                "page_size": page_size,
                "total": data.get("total") if isinstance(data, dict) else None,
                "items": items,
            }
        emit(payload, json_output=json_output)

    run_async(run())


@app.command()
def all(
    mid: int | None = typer.Option(None),
    with_detail: bool = typer.Option(False),
    concurrency: int = typer.Option(3, min=1, max=10),
    json_output: bool = typer.Option(True, "--json/--pretty"),
) -> None:
    """Stream every following across all pages as a flat JSON array."""
    real_mid = _resolve_mid(mid)

    async def run() -> None:
        async with make_client() as client:
            service = FollowingService(client)
            collected: list[dict] = []
            async for item in service.iter_all(real_mid):
                collected.append(item)
            if with_detail and collected:
                details = await service.enrich(
                    [int(i["mid"]) for i in collected if "mid" in i],
                    concurrency=concurrency,
                )
                by_mid = {d["mid"]: d for d in details}
                for item in collected:
                    if "mid" in item:
                        item["detail"] = by_mid.get(int(item["mid"]))
        emit(collected, json_output=json_output)

    run_async(run())


@app.command()
def detail(
    target_mid: int = typer.Argument(..., help="The mid of the UP to inspect."),
    json_output: bool = typer.Option(True, "--json/--pretty"),
) -> None:
    """Profile + stat + latest video for a single UP."""

    async def run() -> None:
        async with make_client() as client:
            data = await FollowingService(client).get_detail(target_mid)
        emit(data, json_output=json_output)

    run_async(run())


@app.command()
def unfollow(
    mids: list[int] = typer.Argument(..., help="One or more mids to unfollow."),
    json_output: bool = typer.Option(True, "--json/--pretty"),
) -> None:
    """Unfollow the given mids (sequential, rate-limited)."""

    async def run() -> None:
        async with make_client() as client:
            result = await FollowingService(client).unfollow_many(mids)
        emit(result, json_output=json_output)

    run_async(run())


@app.command()
def clear(
    mid: int | None = typer.Option(None),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation."),
    json_output: bool = typer.Option(True, "--json/--pretty"),
) -> None:
    """Unfollow EVERY following on the account. Irreversible."""
    real_mid = _resolve_mid(mid)
    if not yes:
        if not typer.confirm(f"Unfollow ALL accounts for mid={real_mid}?"):
            raise typer.Abort()

    async def run() -> None:
        async with make_client() as client:
            result = await FollowingService(client).clear_all(real_mid)
        emit(result, json_output=json_output)

    run_async(run())
