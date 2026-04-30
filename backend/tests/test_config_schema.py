import pytest
from pydantic import ValidationError

from app.models.config import SessionConfig


def test_rejects_interruptibility_out_of_range():
    data = {
        "system_prompt": "hello",
        "llm_temperature": 1.0,
        "llm_max_tokens": 500,
        "stt_temperature": 0.5,
        "tts_voice": "alloy",
        "tts_speed": 1.0,
        "tts_temperature": 0.5,
        "interruptibility_percentage": 120,
    }

    with pytest.raises(ValidationError):
        SessionConfig(**data)


def test_accepts_valid_config_and_keeps_interruptibility_percentage():
    data = {
        "system_prompt": "hello",
        "llm_temperature": 0.7,
        "llm_max_tokens": 500,
        "stt_temperature": 0.2,
        "tts_voice": "alloy",
        "tts_speed": 1.0,
        "tts_temperature": 0.1,
        "interruptibility_percentage": 70,
    }

    cfg = SessionConfig(**data)
    assert cfg.interruptibility_percentage == 70
