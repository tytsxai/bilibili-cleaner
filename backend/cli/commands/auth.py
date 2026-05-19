from __future__ import annotations

import asyncio

import typer

from backend.api import AuthApi, BiliApiClient

from .. import credentials
from .._runtime import emit, make_client, run_async

app = typer.Typer(help="QR-code login / logout / session check.")


def _extract_cookies(data: dict) -> tuple[str | None, str | None]:
    sess = None
    jct = None
    url = data.get("url")
    if isinstance(url, str) and "?" in url:
        from urllib.parse import parse_qs, urlparse

        qs = parse_qs(urlparse(url).query)
        sess = qs.get("SESSDATA", [None])[0]
        jct = qs.get("bili_jct", [None])[0]
    return sess, jct


@app.command()
def login(poll_interval: float = typer.Option(2.0, help="Seconds between QR poll attempts.")) -> None:
    """Generate a QR code, print it as ASCII, and poll until the user
    scans + confirms in the B 站 mobile app. Saves SESSDATA / bili_jct to
    ``~/.bilibili-cleaner/credentials.json``."""

    async def run() -> None:
        async with BiliApiClient(qps=1.5) as client:
            api = AuthApi(client)
            url, key = await api.generate_qrcode()
            try:
                import qrcode

                qr = qrcode.QRCode(border=1)
                qr.add_data(url)
                qr.make()
                qr.print_ascii(invert=True)
            except Exception:
                typer.echo("[qr render failed — scan this URL in the B 站 app instead]")
                typer.echo(url)
            typer.echo("Waiting for scan…")
            while True:
                data = await api.poll_qrcode(key)
                code = data.get("code")
                if code == 0:
                    sess, jct = _extract_cookies(data)
                    if not sess or not jct:
                        typer.echo("Login OK but cookies missing in response", err=True)
                        raise typer.Exit(code=1)
                    me = await AuthApi(BiliApiClient(sessdata=sess, bili_jct=jct)).get_self_info()
                    creds = credentials.Credentials(
                        sessdata=sess,
                        bili_jct=jct,
                        mid=me.get("mid"),
                        uname=me.get("uname"),
                    )
                    path = credentials.save(creds)
                    typer.echo(f"Logged in as {creds.uname} (mid={creds.mid}). Saved to {path}.")
                    return
                if code == 86038:
                    typer.echo("QR code expired. Re-run `login`.", err=True)
                    raise typer.Exit(code=1)
                await asyncio.sleep(poll_interval)

    run_async(run())


@app.command()
def logout() -> None:
    """Forget the saved credentials."""
    if credentials.clear():
        typer.echo("Credentials cleared.")
    else:
        typer.echo("No saved credentials.")


@app.command()
def me(json_output: bool = typer.Option(True, "--json/--pretty")) -> None:
    """Verify the saved session and print the current user info."""

    async def run() -> None:
        async with make_client() as client:
            data = await AuthApi(client).get_self_info()
        emit(data, json_output=json_output)

    run_async(run())
