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

    # Diarization engine selection (customer-facing names): "freya1" = Deepgram
    # streaming, "freya2" = external /diarize model, "freya3" = Speechmatics
    # streaming STT with in-stream diarization. profile tunes Freya 2 latency.
    diarization_engine: constr(strict=True, min_length=1) = Field(default="freya1")
    diarization_profile: constr(strict=True, min_length=1) = Field(default="accurate")

    # Pydantic: forbid extra/unknown fields
    class Config:
        extra = "forbid"
