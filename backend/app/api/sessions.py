import logging
import os
import subprocess
import sys
import time
from pathlib import Path
from uuid import uuid4

import aiohttp
from fastapi import APIRouter, HTTPException, Request

from app.models.config import SessionConfig
from app.services.rate_limit import session_creation_limiter_from_env
from app.services.request_identity import client_ip
from app.services.retries import daily_api_max_attempts, retry_async
from pipecat.transports.daily.utils import DailyRESTHelper, DailyRoomParams, DailyRoomProperties

router = APIRouter(prefix="/api/sessions", tags=["sessions"])

session_creation_limiter = session_creation_limiter_from_env()
_logger = logging.getLogger(__name__)


@router.post("")
async def create_session(config: SessionConfig, request: Request) -> dict[str, str]:
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
        "--config",
        config_json,
    ]

    log_dir = Path(os.environ.get("BOT_LOG_DIR", "/app/logs"))
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / f"bot-{session_id}.log"
    log_fd = os.open(str(log_path), os.O_APPEND | os.O_CREAT | os.O_WRONLY, 0o644)
    try:
        proc = subprocess.Popen(
            cmd,
            stdin=subprocess.DEVNULL,
            stdout=log_fd,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
    finally:
        os.close(log_fd)

    _logger.info(
        "spawned voice bot subprocess session_id=%s pid=%s log_file=%s",
        session_id,
        proc.pid,
        log_path,
    )

    return {
        "session_id": session_id,
        "room_url": room.url,
        "token": user_token,
    }
