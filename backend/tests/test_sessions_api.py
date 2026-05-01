import asyncio
import json
import subprocess
import sys
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(autouse=True)
def _bot_log_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("BOT_LOG_DIR", str(tmp_path))


client = TestClient(app)

VALID_PAYLOAD = {
    "system_prompt": "You are a friendly voice assistant.",
    "llm_temperature": 0.7,
    "llm_max_tokens": 256,
    "stt_temperature": 0.0,
    "tts_voice": "sonic",
    "tts_speed": 1.0,
    "tts_temperature": 0.3,
    "interruptibility_percentage": 70
}


@patch("app.api.sessions.session_creation_limiter")
@patch("app.api.sessions.subprocess.Popen")
@patch("app.api.sessions.DailyRESTHelper")
def test_create_session_provisions_room_and_spawns_bot(mock_helper_cls, mock_popen, mock_limiter):
    # Mock DailyRESTHelper behavior
    mock_helper = MagicMock()
    mock_helper_cls.return_value = mock_helper
    mock_limiter.allow.return_value = True

    # Mock async create_room to return a url
    future_room = asyncio.Future()
    future_room.set_result(MagicMock(url="https://mock.daily.co/room123"))
    mock_helper.create_room.return_value = future_room

    # Mock async get_token to return bot token, then user token
    future_bot_token = asyncio.Future()
    future_bot_token.set_result("bot-token-abc")
    future_user_token = asyncio.Future()
    future_user_token.set_result("user-token-xyz")
    mock_helper.get_token.side_effect = [future_bot_token, future_user_token]

    response = client.post("/api/sessions", json=VALID_PAYLOAD)
    assert response.status_code == 200
    
    data = response.json()
    assert "session_id" in data
    assert data["room_url"] == "https://mock.daily.co/room123"
    assert data["token"] == "user-token-xyz"

    # Verify bot was spawned as subprocess with correct arguments
    mock_popen.assert_called_once()
    cmd = mock_popen.call_args[0][0]
    popen_kw = mock_popen.call_args[1]
    assert cmd[0] == sys.executable
    assert "bot.py" in cmd[1]
    assert popen_kw.get("start_new_session") is True
    assert popen_kw.get("stdin") == subprocess.DEVNULL
    assert isinstance(popen_kw.get("stdout"), int)
    assert popen_kw.get("stderr") == subprocess.STDOUT
    assert "--room-url" in cmd
    assert "https://mock.daily.co/room123" in cmd
    assert "--token" in cmd
    assert "bot-token-abc" in cmd
    assert "--config" in cmd
    
    # Verify config payload passed to bot matches
    config_str = cmd[cmd.index("--config") + 1]
    config_data = json.loads(config_str)
    assert config_data["system_prompt"] == "You are a friendly voice assistant."

    assert "--conversation-id" in cmd
    assert cmd[cmd.index("--conversation-id") + 1] == data["session_id"]


@patch("app.api.sessions.session_creation_limiter")
@patch("app.api.sessions.subprocess.Popen")
@patch("app.api.sessions.DailyRESTHelper")
def test_create_session_returns_429_when_rate_limited(mock_helper_cls, mock_popen, mock_limiter):
    mock_limiter.allow.return_value = False
    response = client.post("/api/sessions", json=VALID_PAYLOAD)
    assert response.status_code == 429
    mock_helper_cls.assert_not_called()
    mock_popen.assert_not_called()


@patch("app.api.sessions.session_creation_limiter")
@patch("app.api.sessions.subprocess.Popen")
@patch("app.api.sessions.DailyRESTHelper")
def test_create_session_retries_daily_create_room(mock_helper_cls, mock_popen, mock_limiter):
    import aiohttp

    mock_limiter.allow.return_value = True
    mock_helper = MagicMock()
    mock_helper_cls.return_value = mock_helper

    attempt = {"n": 0}

    async def flaky_create_room(_params):
        attempt["n"] += 1
        if attempt["n"] < 2:
            raise aiohttp.ClientConnectionError("transient")
        return MagicMock(url="https://mock.daily.co/room123")

    mock_helper.create_room.side_effect = flaky_create_room

    future_bot_token = asyncio.Future()
    future_bot_token.set_result("bot-token-abc")
    future_user_token = asyncio.Future()
    future_user_token.set_result("user-token-xyz")
    mock_helper.get_token.side_effect = [future_bot_token, future_user_token]

    response = client.post("/api/sessions", json=VALID_PAYLOAD)
    assert response.status_code == 200
    assert attempt["n"] == 2
    mock_popen.assert_called_once()
