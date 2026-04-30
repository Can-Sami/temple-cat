from pydantic import BaseModel, Field


class SessionConfig(BaseModel):
    """Validated session configuration for voice AI interviews."""

    system_prompt: str = Field(..., min_length=1)
    llm_temperature: float = Field(..., ge=0.0, le=2.0)
    llm_max_tokens: int = Field(..., ge=1, le=4096)
    stt_temperature: float = Field(..., ge=0.0, le=1.0)
    tts_voice: str = Field(..., min_length=1)
    tts_speed: float = Field(..., ge=0.5, le=2.0)
    tts_temperature: float = Field(..., ge=0.0, le=1.0)
    interruptibility_percentage: int = Field(..., ge=0, le=100)
