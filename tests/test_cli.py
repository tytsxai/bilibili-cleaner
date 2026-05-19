from __future__ import annotations

import json
import os
from pathlib import Path

import httpx
import pytest
import respx
from typer.testing import CliRunner

from backend.api.auth import NAV_URL as AUTH_NAV_URL
from backend.api.relation import FOLLOWINGS_URL, MODIFY_URL
from backend.api.relation_tag import LIST_TAGS_URL
from backend.cli import credentials
from backend.cli.main import app

CSRF = "csrf-token"


@pytest.fixture
def isolated_creds(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Redirect credentials storage and env vars to an isolated temp dir."""
    cred_path = tmp_path / "credentials.json"
    monkeypatch.setenv("BILI_CREDENTIALS_PATH", str(cred_path))
    monkeypatch.delenv("BILI_SESSDATA", raising=False)
    monkeypatch.delenv("BILI_JCT", raising=False)
    monkeypatch.delenv("BILI_MID", raising=False)
    return cred_path


@pytest.fixture
def saved_creds(isolated_creds: Path) -> Path:
    credentials.save(
        credentials.Credentials(
            sessdata="sess", bili_jct=CSRF, mid=42, uname="tester"
        )
    )
    return isolated_creds


def test_cli_help_runs(isolated_creds: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "bilibili-cleaner" in result.output


def test_cli_followings_requires_credentials(isolated_creds: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["followings", "list", "--mid", "1"])
    assert result.exit_code == 1
    assert "credentials" in result.stderr.lower() or "credentials" in result.output.lower()


def test_cli_credentials_round_trip(isolated_creds: Path) -> None:
    credentials.save(
        credentials.Credentials(sessdata="s1", bili_jct="j1", mid=7, uname="u")
    )
    loaded = credentials.load()
    assert loaded is not None
    assert loaded.sessdata == "s1"
    assert loaded.mid == 7


def test_cli_credentials_env_overrides(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BILI_CREDENTIALS_PATH", str(tmp_path / "creds.json"))
    monkeypatch.setenv("BILI_SESSDATA", "env-sess")
    monkeypatch.setenv("BILI_JCT", "env-jct")
    monkeypatch.setenv("BILI_MID", "999")
    loaded = credentials.load()
    assert loaded is not None
    assert loaded.sessdata == "env-sess"
    assert loaded.mid == 999


def test_cli_credentials_clear(isolated_creds: Path) -> None:
    credentials.save(credentials.Credentials(sessdata="s", bili_jct="j"))
    assert credentials.load() is not None
    assert credentials.clear()
    assert credentials.load() is None
    assert not credentials.clear()


def test_cli_me(saved_creds: Path) -> None:
    runner = CliRunner()
    with respx.mock() as router:
        router.get(AUTH_NAV_URL).mock(
            return_value=httpx.Response(
                200, json={"code": 0, "data": {"isLogin": True, "mid": 42, "uname": "tester"}}
            )
        )
        result = runner.invoke(app, ["me", "--json"])
    assert result.exit_code == 0
    body = json.loads(result.stdout)
    assert body["mid"] == 42
    assert body["uname"] == "tester"


def test_cli_followings_list_uses_saved_mid(saved_creds: Path) -> None:
    runner = CliRunner()
    with respx.mock() as router:
        router.get(FOLLOWINGS_URL).mock(
            return_value=httpx.Response(
                200,
                json={
                    "code": 0,
                    "data": {"list": [{"mid": 1, "uname": "a"}], "total": 1},
                },
            )
        )
        result = runner.invoke(app, ["followings", "list", "--page-size", "10"])
    assert result.exit_code == 0
    body = json.loads(result.stdout)
    assert body["total"] == 1
    assert len(body["items"]) == 1


def test_cli_followings_unfollow(saved_creds: Path) -> None:
    runner = CliRunner()
    with respx.mock() as router:
        router.post(MODIFY_URL).mock(
            return_value=httpx.Response(200, json={"code": 0, "data": {}})
        )
        result = runner.invoke(app, ["followings", "unfollow", "1", "2"])
    assert result.exit_code == 0
    body = json.loads(result.stdout)
    assert body["ok"] == 2
    assert body["total"] == 2


def test_cli_tag_list(saved_creds: Path) -> None:
    runner = CliRunner()
    with respx.mock() as router:
        router.get(LIST_TAGS_URL).mock(
            return_value=httpx.Response(
                200,
                json={"code": 0, "data": [{"tagid": 0, "name": "默认", "count": 10}]},
            )
        )
        result = runner.invoke(app, ["tag", "list"])
    assert result.exit_code == 0
    body = json.loads(result.stdout)
    assert body[0]["name"] == "默认"


def test_cli_logout(saved_creds: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["logout"])
    assert result.exit_code == 0
    assert credentials.load() is None
