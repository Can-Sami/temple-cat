import asyncio
import json
import subprocess
import sys
from contextlib import ExitStack
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def _bot_log_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("BOT_LOG_DIR", str(tmp_path))


VALID_PAYLOAD = {
    "system_prompt": "You are a friendly voice assistant.",
    "llm_temperature": 0.7,
    "llm_max_tokens": 256,
    "stt_temperature": 0.0,
    "tts_voice": "sonic",
    "tts_speed": 1.0,
    "tts_temperature": 0.3,
    "interruptibility_percentage": 70,
}


def _configure_create_subprocess_mock(mock_exec: AsyncMock, *, returncode: int | None, pid: int = 4242):
    proc = MagicMock()
    proc.pid = pid
    proc.returncode = returncode
    stdout = MagicMock()
    stdout.read = AsyncMock(return_value=b"")
    proc.stdout = stdout

    async def _fake(*_args, **_kwargs):
        await asyncio.sleep(0)
        return proc

    mock_exec.side_effect = _fake
    return proc


def test_create_session_provisions_room_and_spawns_bot(client):
    with ExitStack() as stack:
        mock_limiter = stack.enter_context(patch("app.api.sessions.session_creation_limiter"))
        mock_subprocess_exec = stack.enter_context(
            patch("app.api.sessions.asyncio.create_subprocess_exec", new_callable=AsyncMock)
        )
        mock_helper_cls = stack.enter_context(patch("app.api.sessions.DailyRESTHelper"))

        mock_helper = MagicMock()
        mock_helper_cls.return_value = mock_helper
        mock_limiter.allow.return_value = True

        future_room = asyncio.Future()
        future_room.set_result(MagicMock(url="https://mock.daily.co/room123"))
        mock_helper.create_room.return_value = future_room

        future_bot_token = asyncio.Future()
        future_bot_token.set_result("bot-token-abc")
        future_user_token = asyncio.Future()
        future_user_token.set_result("user-token-xyz")
        mock_helper.get_token.side_effect = [future_bot_token, future_user_token]

        mock_proc = _configure_create_subprocess_mock(mock_subprocess_exec, returncode=None)

        response = client.post("/api/sessions", json=VALID_PAYLOAD)
        assert response.status_code == 200

        data = response.json()
        assert "session_id" in data
        assert data["room_url"] == "https://mock.daily.co/room123"
        assert data["token"] == "user-token-xyz"
        assert data["bot_pid"] == mock_proc.pid

        mock_subprocess_exec.assert_called_once()
        cmd = list(mock_subprocess_exec.call_args[0])
        kw = mock_subprocess_exec.call_args[1]
        assert cmd[0] == sys.executable
        assert "bot.py" in cmd[1]
        assert kw.get("start_new_session") is True
        assert kw.get("stdin") == subprocess.DEVNULL
        assert kw.get("stdout") == asyncio.subprocess.PIPE
        assert kw.get("stderr") == subprocess.STDOUT
        assert "--room-url" in cmd
        assert "https://mock.daily.co/room123" in cmd
        assert "--token" in cmd
        assert "bot-token-abc" in cmd
        assert "--config" in cmd

        config_str = cmd[cmd.index("--config") + 1]
        config_data = json.loads(config_str)
        assert config_data["system_prompt"] == "You are a friendly voice assistant."

        assert "--conversation-id" in cmd
        assert cmd[cmd.index("--conversation-id") + 1] == data["session_id"]


def test_create_session_returns_429_when_rate_limited(client):
    with ExitStack() as stack:
        mock_limiter = stack.enter_context(patch("app.api.sessions.session_creation_limiter"))
        mock_subprocess_exec = stack.enter_context(
            patch("app.api.sessions.asyncio.create_subprocess_exec", new_callable=AsyncMock)
        )
        mock_helper_cls = stack.enter_context(patch("app.api.sessions.DailyRESTHelper"))

        mock_limiter.allow.return_value = False
        response = client.post("/api/sessions", json=VALID_PAYLOAD)
        assert response.status_code == 429
        mock_helper_cls.assert_not_called()
        mock_subprocess_exec.assert_not_called()


def test_create_session_retries_daily_create_room(client):
    import aiohttp

    with ExitStack() as stack:
        mock_limiter = stack.enter_context(patch("app.api.sessions.session_creation_limiter"))
        mock_subprocess_exec = stack.enter_context(
            patch("app.api.sessions.asyncio.create_subprocess_exec", new_callable=AsyncMock)
        )
        mock_helper_cls = stack.enter_context(patch("app.api.sessions.DailyRESTHelper"))

        mock_limiter.allow.return_value = True
        mock_helper = MagicMock()
        mock_helper_cls.return_value = mock_helper

        attempt = {"n": 0}

        async def flaky_create_room(_params):
            await asyncio.sleep(0)
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

        _configure_create_subprocess_mock(mock_subprocess_exec, returncode=None)

        response = client.post("/api/sessions", json=VALID_PAYLOAD)
        assert response.status_code == 200
        assert attempt["n"] == 2
        mock_subprocess_exec.assert_called_once()


def test_create_session_503_when_bot_exits_immediately(client):
    with ExitStack() as stack:
        mock_limiter = stack.enter_context(patch("app.api.sessions.session_creation_limiter"))
        mock_subprocess_exec = stack.enter_context(
            patch("app.api.sessions.asyncio.create_subprocess_exec", new_callable=AsyncMock)
        )
        mock_helper_cls = stack.enter_context(patch("app.api.sessions.DailyRESTHelper"))

        mock_limiter.allow.return_value = True
        mock_helper = MagicMock()
        mock_helper_cls.return_value = mock_helper

        future_room = asyncio.Future()
        future_room.set_result(MagicMock(url="https://mock.daily.co/room123"))
        mock_helper.create_room.return_value = future_room

        future_bot_token = asyncio.Future()
        future_bot_token.set_result("bot-token-abc")
        future_user_token = asyncio.Future()
        future_user_token.set_result("user-token-xyz")
        mock_helper.get_token.side_effect = [future_bot_token, future_user_token]

        _configure_create_subprocess_mock(mock_subprocess_exec, returncode=1, pid=999)

        response = client.post("/api/sessions", json=VALID_PAYLOAD)
        assert response.status_code == 503
        body = response.json()
        assert body.get("error") == "bot_startup_failed"
        assert body.get("exit_code") == 1
        assert "session_id" in body
