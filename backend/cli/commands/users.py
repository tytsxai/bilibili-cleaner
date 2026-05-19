from __future__ import annotations

import typer

from backend.api import UserApi

from .._runtime import emit, make_client, run_async

app = typer.Typer(help="Public UP profile / stat / video lookups.")


@app.command()
def info(
    target_mid: int = typer.Argument(...),
    json_output: bool = typer.Option(True, "--json/--pretty"),
) -> None:
    """`/x/space/wbi/acc/info` — profile metadata for a single UP."""

    async def run() -> None:
        async with make_client() as client:
            data = await UserApi(client).get_info(target_mid)
        emit(data, json_output=json_output)

    run_async(run())


@app.command()
def stat(
    target_mid: int = typer.Argument(...),
    json_output: bool = typer.Option(True, "--json/--pretty"),
) -> None:
    """Follower / following counts."""

    async def run() -> None:
        async with make_client() as client:
            data = await UserApi(client).get_stat(target_mid)
        emit(data, json_output=json_output)

    run_async(run())


@app.command()
def videos(
    target_mid: int = typer.Argument(...),
    page: int = typer.Option(1),
    page_size: int = typer.Option(30, min=1, max=50),
    order: str = typer.Option("pubdate", help="pubdate | click | stow"),
    json_output: bool = typer.Option(True, "--json/--pretty"),
) -> None:
    """List recent video uploads of a UP."""

    async def run() -> None:
        async with make_client() as client:
            data = await UserApi(client).get_videos(
                target_mid, pn=page, ps=page_size, order=order
            )
        emit(data, json_output=json_output)

    run_async(run())
