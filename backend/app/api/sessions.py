import json
import os
import subprocess
import time
from uuid import uuid4

import aiohttp

from fastapi import APIRouter

from app.models.config import SessionConfig
from pipecat.transports.daily.utils import DailyRESTHelper, DailyRoomParams, DailyRoomProperties

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


@router.post("")
async def create_session(config: SessionConfig) -> dict[str, str]:
    """Bootstrap a new voice session and return its ID.

    Provisions a Daily room, mints tokens, and spawns the bot subprocess.
    """
    session_id = str(uuid4())

    daily_api_key = os.environ.get("DAILY_API_KEY", "")
    
    async with aiohttp.ClientSession() as session:
        helper = DailyRESTHelper(daily_api_key=daily_api_key, aiohttp_session=session)

        room_params = DailyRoomParams(
            properties=DailyRoomProperties(
                exp=int(time.time()) + 60 * 60,  # 1 hour expiration
            )
        )
        room = await helper.create_room(room_params)

        bot_token = await helper.get_token(room.url, expiry_time=3600)
        user_token = await helper.get_token(room.url, expiry_time=3600)

    config_json = config.model_dump_json()

    bot_script_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "bot.py"))

    cmd = [
        "python",
        bot_script_path,
        "--room-url", room.url,
        "--token", bot_token,
        "--config", config_json
    ]

    # Spawn bot as detached subprocess
    subprocess.Popen(cmd)

    return {
        "session_id": session_id,
        "room_url": room.url,
        "token": user_token
    }
