from __future__ import annotations

import typer

from backend.services import HistoryService

from .._runtime import emit, make_client, run_async

app = typer.Typer(help="Watch history list / delete / clear.")


@app.command("list")
def list_cmd(
    max_id: int = typer.Option(0, help="Cursor from prior cursor.max"),
    business: str = typer.Option(""),
    view_at: int = typer.Option(0),
    page_size: int = typer.Option(20, min=1, max=30),
    type_: str = typer.Option("all", "--type"),
    json_output: bool = typer.Option(True, "--json/--pretty"),
) -> None:
    async def run() -> None:
        async with make_client() as client:
            data = await HistoryService(client).list_page(
                max_id=max_id,
                business=business,
                view_at=view_at,
                page_size=page_size,
                type_=type_,
            )
        emit(data, json_output=json_output)

    run_async(run())


@app.command()
def delete(
    kid: str = typer.Argument(..., help="e.g. archive_12345"),
    json_output: bool = typer.Option(True, "--json/--pretty"),
) -> None:
    async def run() -> None:
        async with make_client() as client:
            data = await HistoryService(client).delete(kid)
        emit(data, json_output=json_output)

    run_async(run())


@app.command()
def clear(
    yes: bool = typer.Option(False, "--yes", "-y"),
    json_output: bool = typer.Option(True, "--json/--pretty"),
) -> None:
    if not yes and not typer.confirm("Wipe ALL watch history?"):
        raise typer.Abort()

    async def run() -> None:
        async with make_client() as client:
            data = await HistoryService(client).clear()
        emit({"cleared": True, "raw": data}, json_output=json_output)

    run_async(run())
