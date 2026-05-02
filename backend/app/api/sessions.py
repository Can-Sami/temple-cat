import asyncio
import logging
import os
import subprocess
import sys
import time
from pathlib import Path
from uuid import uuid4

import aiofiles
import aiohttp
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from app.models.config import SessionConfig
from app.models.session_response import VoiceSessionResponse
from app.services.rate_limit import session_creation_limiter_from_env
from app.services.request_identity import client_ip
from app.services.retries import daily_api_max_attempts, retry_async
from pipecat.transports.daily.utils import DailyRESTHelper, DailyRoomParams, DailyRoomProperties

router = APIRouter(prefix="/api/sessions", tags=["sessions"])

session_creation_limiter = session_creation_limiter_from_env()
_logger = logging.getLogger(__name__)

# Strong refs until drain completes; prevents GC of fire-and-forget tasks after the handler returns.
_stdout_drain_tasks: set[asyncio.Task[None]] = set()


def _retain_stdout_drain_task(task: asyncio.Task[None]) -> None:
    _stdout_drain_tasks.add(task)
    task.add_done_callback(_stdout_drain_tasks.discard)


async def _pipe_stdout_to_file(stream: asyncio.StreamReader | None, path: Path) -> None:
    if stream is None:
        return
    async with aiofiles.open(path, "ab") as log_file:
        while True:
            chunk = await stream.read(65536)
            if not chunk:
                break
            await log_file.write(chunk)


@router.post(
    "",
    response_model=VoiceSessionResponse,
    responses={
        429: {"description": "Too many session creations from this client; rate limited."},
        503: {"description": "Voice bot failed to start."},
    },
)
async def create_session(config: SessionConfig, request: Request) -> VoiceSessionResponse | JSONResponse:
    """Bootstrap a new voice session and return its ID.

    Provisions a Daily room, mints tokens, and spawns the bot subprocess.
    """
    if not session_creation_limiter.allow(client_ip(request)):
        raise HTTPException(
            status_code=429,
            detail="Too many session creations from this client; try again later.",
        )

    session_id = str(uuid4())

    daily_api_key = os.environ.get("DAILY_API_KEY", "")
    attempts = daily_api_max_attempts()

    async with aiohttp.ClientSession() as session:
        helper = DailyRESTHelper(daily_api_key=daily_api_key, aiohttp_session=session)

        room_params = DailyRoomParams(
            properties=DailyRoomProperties(
                exp=int(time.time()) + 60 * 60,  # 1 hour expiration
                eject_at_room_exp=True,
            )
        )

        room = await retry_async(
            lambda: helper.create_room(room_params),
            max_attempts=attempts,
            label="daily_create_room",
        )

        bot_token = await retry_async(
            lambda: helper.get_token(room.url, expiry_time=3600),
            max_attempts=attempts,
            label="daily_get_token_bot",
        )
        user_token = await retry_async(
            lambda: helper.get_token(room.url, expiry_time=3600),
            max_attempts=attempts,
            label="daily_get_token_user",
        )

    config_json = config.model_dump_json()

    bot_script_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "bot.py"))

    cmd = [
        sys.executable,
        bot_script_path,
        "--room-url",
        room.url,
        "--token",
        bot_token,
        "--body",
        config_json,
        "--conversation-id",
        session_id,
    ]

    log_dir = Path(os.environ.get("BOT_LOG_DIR", "/app/logs"))
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / f"bot-{session_id}.log"

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdin=subprocess.DEVNULL,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
        start_new_session=True,
        env=os.environ.copy(),
    )

    # Brief yield so import/config validation failures surface before we hand tokens to the client.
    await asyncio.sleep(0.1)
    exit_early = proc.returncode
    if exit_early is not None:
        await _pipe_stdout_to_file(proc.stdout, log_path)
        _logger.error(
            "bot subprocess exited immediately session_id=%s pid=%s exit_code=%s log_file=%s metric=bot_spawn_failure",
            session_id,
            proc.pid,
            exit_early,
            log_path,
        )
        # JSONResponse avoids FastAPI's default HTTPException ``{"detail": {...}}`` wrapping.
        return JSONResponse(
            status_code=503,
            content={
                "error": "bot_startup_failed",
                "message": "Voice bot failed to start; see server logs and bot log file for this session.",
                "session_id": session_id,
                "exit_code": exit_early,
                "log_file": str(log_path),
            },
        )

    _retain_stdout_drain_task(asyncio.create_task(_pipe_stdout_to_file(proc.stdout, log_path)))

    _logger.info(
        "spawned voice bot subprocess session_id=%s pid=%s log_file=%s metric=bot_spawn_ok",
        session_id,
        proc.pid,
        log_path,
    )

    return VoiceSessionResponse(
        session_id=session_id,
        room_url=room.url,
        token=user_token,
        bot_pid=proc.pid,
    )
