import os

import pytest

from app.services.cors_origins import cors_allow_origins_from_env


@pytest.fixture()
def clear_frontend_origin(monkeypatch):
    monkeypatch.delenv("FRONTEND_ORIGIN", raising=False)


def test_default_origin_when_unset(clear_frontend_origin):
    assert cors_allow_origins_from_env() == ["http://localhost:3000"]


def test_comma_separated_origins(monkeypatch):
    monkeypatch.setenv(
        "FRONTEND_ORIGIN",
        "http://localhost:3000, https://voice.example.com ",
    )
    assert cors_allow_origins_from_env() == [
        "http://localhost:3000",
        "https://voice.example.com",
    ]


def test_wildcard_opt_in(monkeypatch):
    monkeypatch.setenv("FRONTEND_ORIGIN", "*")
    assert cors_allow_origins_from_env() == ["*"]
