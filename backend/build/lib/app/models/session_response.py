from pydantic import BaseModel


class VoiceSessionResponse(BaseModel):
    """Credentials returned to the browser after provisioning Daily + spawning the bot."""

    session_id: str
    room_url: str
    token: str
    bot_pid: int
