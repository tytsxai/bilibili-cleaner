from __future__ import annotations

import typer

from backend.services import TagService

from .._runtime import emit, make_client, run_async

app = typer.Typer(help="Custom following groups (B 站「关注分组」).")


@app.command("list")
def list_cmd(json_output: bool = typer.Option(True, "--json/--pretty")) -> None:
    async def run() -> None:
        async with make_client() as client:
            data = await TagService(client).list_tags()
        emit(data, json_output=json_output)

    run_async(run())


@app.command()
def create(
    name: str = typer.Argument(...),
    json_output: bool = typer.Option(True, "--json/--pretty"),
) -> None:
    async def run() -> None:
        async with make_client() as client:
            data = await TagService(client).create_tag(name)
        emit(data, json_output=json_output)

    run_async(run())


@app.command()
def delete(
    tagid: int = typer.Argument(...),
    json_output: bool = typer.Option(True, "--json/--pretty"),
) -> None:
    async def run() -> None:
        async with make_client() as client:
            data = await TagService(client).delete_tag(tagid)
        emit(data, json_output=json_output)

    run_async(run())


@app.command("add-users")
def add_users(
    mids: list[int] = typer.Argument(...),
    tagid: int | None = typer.Option(None),
    tag_name: str | None = typer.Option(None, help="Find/create by name if tagid omitted."),
    replace: bool = typer.Option(False, help="Replace existing tags instead of adding."),
    json_output: bool = typer.Option(True, "--json/--pretty"),
) -> None:
    if tagid is None and tag_name is None:
        typer.echo("Provide --tagid or --tag-name.", err=True)
        raise typer.Exit(code=1)

    async def run() -> None:
        async with make_client() as client:
            data = await TagService(client).tag_users(
                mids, tagid=tagid, tag_name=tag_name, replace=replace
            )
        emit(data, json_output=json_output)

    run_async(run())


@app.command("list-users")
def list_users(
    tagid: int = typer.Argument(...),
    page: int = typer.Option(1),
    page_size: int = typer.Option(20),
    json_output: bool = typer.Option(True, "--json/--pretty"),
) -> None:
    async def run() -> None:
        async with make_client() as client:
            data = await TagService(client).list_tag_users(
                tagid, page=page, page_size=page_size
            )
        emit(data, json_output=json_output)

    run_async(run())
