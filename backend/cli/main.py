from __future__ import annotations

import typer

from backend.logging_config import configure_logging

from .commands import auth as auth_cmd
from .commands import dynamics as dynamics_cmd
from .commands import favorites as favorites_cmd
from .commands import followings as followings_cmd
from .commands import history as history_cmd
from .commands import tag as tag_cmd
from .commands import users as users_cmd

app = typer.Typer(
    name="bilibili-cleaner",
    help=(
        "Inspect and clean a Bilibili account. All commands emit JSON by "
        "default (override with --pretty). Auth via `bilibili-cleaner auth login`."
    ),
    no_args_is_help=True,
)

# The CLI drives the same service layer as the API, which logs per-item failures
# at WARNING. Without this those warnings would vanish and a partially-failed
# bulk delete would look clean. Logs go to stderr, so piping stdout into jq
# still works; silence them with BILI_LOG_LEVEL=ERROR.
configure_logging()

app.add_typer(auth_cmd.app, name="auth")
app.add_typer(users_cmd.app, name="users")
app.add_typer(followings_cmd.app, name="followings")
app.add_typer(favorites_cmd.app, name="favorites")
app.add_typer(dynamics_cmd.app, name="dynamics")
app.add_typer(history_cmd.app, name="history")
app.add_typer(tag_cmd.app, name="tag")


# Shortcuts so `bilibili-cleaner me` works without `auth me`.
@app.command(help="Alias of `auth me` — verify session and print user info.")
def me(json_output: bool = typer.Option(True, "--json/--pretty")) -> None:
    auth_cmd.me(json_output=json_output)


@app.command(help="Alias of `auth login`.")
def login(poll_interval: float = typer.Option(2.0)) -> None:
    auth_cmd.login(poll_interval=poll_interval)


@app.command(help="Alias of `auth logout`.")
def logout() -> None:
    auth_cmd.logout()


if __name__ == "__main__":
    app()
