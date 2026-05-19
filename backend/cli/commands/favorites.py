from __future__ import annotations

import typer

from backend.services import FavoriteService

from .. import credentials
from .._runtime import emit, make_client, run_async

app = typer.Typer(help="Inspect and selectively delete favorites.")


def _resolve_mid(explicit: int | None) -> int:
    if explicit is not None:
        return explicit
    creds = credentials.load()
    if creds and creds.mid:
        return creds.mid
    typer.echo("No mid given. Pass --mid or login first.", err=True)
    raise typer.Exit(code=1)


@app.command()
def folders(
    mid: int | None = typer.Option(None),
    json_output: bool = typer.Option(True, "--json/--pretty"),
) -> None:
    real_mid = _resolve_mid(mid)

    async def run() -> None:
        async with make_client() as client:
            data = await FavoriteService(client).list_folders(real_mid)
        emit(data, json_output=json_output)

    run_async(run())


@app.command()
def items(
    media_id: int = typer.Argument(...),
    page: int = typer.Option(1),
    page_size: int = typer.Option(20, min=1, max=40),
    keyword: str = typer.Option(""),
    order: str = typer.Option("mtime"),
    json_output: bool = typer.Option(True, "--json/--pretty"),
) -> None:
    """List items in a folder (one page)."""

    async def run() -> None:
        async with make_client() as client:
            data = await FavoriteService(client).list_items(
                media_id, page=page, page_size=page_size, keyword=keyword, order=order
            )
        emit(data, json_output=json_output)

    run_async(run())


@app.command()
def delete(
    media_id: int = typer.Argument(...),
    resource_ids: list[int] = typer.Argument(..., help="Video aids; type defaults to 2."),
    json_output: bool = typer.Option(True, "--json/--pretty"),
) -> None:
    """Remove specific videos from a folder."""

    async def run() -> None:
        async with make_client() as client:
            result = await FavoriteService(client).delete_resources(media_id, resource_ids)
        emit(result, json_output=json_output)

    run_async(run())


@app.command()
def clear(
    mid: int | None = typer.Option(None),
    yes: bool = typer.Option(False, "--yes", "-y"),
    json_output: bool = typer.Option(True, "--json/--pretty"),
) -> None:
    """Empty every favorite folder."""
    real_mid = _resolve_mid(mid)
    if not yes and not typer.confirm(f"Delete ALL favorites for mid={real_mid}?"):
        raise typer.Abort()

    async def run() -> None:
        async with make_client() as client:
            result = await FavoriteService(client).clear_all(real_mid)
        emit(result, json_output=json_output)

    run_async(run())
