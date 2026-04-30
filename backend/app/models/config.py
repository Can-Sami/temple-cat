from pydantic import BaseModel, Field, conint, confloat, constr


class SessionConfig(BaseModel):
    """Validated session configuration for voice AI interviews."""

    system_prompt: constr(strict=True, min_length=1) = Field(...)
    llm_temperature: confloat(strict=True, ge=0.0, le=2.0) = Field(...)
    llm_max_tokens: conint(strict=True, ge=1, le=4096) = Field(...)
    stt_temperature: confloat(strict=True, ge=0.0, le=1.0) = Field(...)
    tts_voice: constr(strict=True, min_length=1) = Field(...)
    tts_speed: confloat(strict=True, ge=0.5, le=2.0) = Field(...)
    tts_temperature: confloat(strict=True, ge=0.0, le=1.0) = Field(...)
    interruptibility_percentage: conint(strict=True, ge=0, le=100) = Field(...)

    # Pydantic v1: forbid extra/unknown fields
    class Config:
        extra = "forbid"

    # Pydantic v2 compatibility: prefer ConfigDict when available
    try:
        from pydantic import ConfigDict  # type: ignore

        model_config = ConfigDict(extra="forbid")
    except Exception:
        # If ConfigDict isn't present (pydantic<2), ignore
        pass
