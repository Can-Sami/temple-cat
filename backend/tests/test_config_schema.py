import pytest
from pydantic import ValidationError

# Import path handled by backend/tests/conftest.py

from app.models.config import SessionConfig


def make_base():
    return {
        "system_prompt": "hello",
        "llm_temperature": 0.7,
        "llm_max_tokens": 500,
        "stt_temperature": 0.2,
        "tts_voice": "alloy",
        "tts_speed": 1.0,
        "tts_temperature": 0.1,
        "interruptibility_percentage": 70,
    }


def test_rejects_interruptibility_out_of_range():
    data = make_base()
    data["interruptibility_percentage"] = 120

    with pytest.raises(ValidationError):
        SessionConfig(**data)


def test_accepts_valid_config_and_keeps_interruptibility_percentage():
    data = make_base()
    data["interruptibility_percentage"] = 70

    cfg = SessionConfig(**data)
    assert cfg.interruptibility_percentage == 70


def test_rejects_missing_required_field():
    data = make_base()
    del data["system_prompt"]

    with pytest.raises(ValidationError):
        SessionConfig(**data)


def test_rejects_string_coercion_for_int_and_float():
    data = make_base()
    data["llm_max_tokens"] = "500"  # should not coerce to int
    data["llm_temperature"] = "1.0"  # should not coerce to float

    with pytest.raises(ValidationError):
        SessionConfig(**data)


def test_rejects_empty_tts_voice():
    data = make_base()
    data["tts_voice"] = ""

    with pytest.raises(ValidationError):
        SessionConfig(**data)


@pytest.mark.parametrize(
    "field, value",
    [
        ("llm_max_tokens", 1),
        ("llm_max_tokens", 4096),
        ("tts_speed", 0.5),
        ("tts_speed", 2.0),
        ("stt_temperature", 0.0),
        ("stt_temperature", 1.0),
        ("tts_temperature", 0.0),
        ("tts_temperature", 1.0),
        ("interruptibility_percentage", 0),
        ("interruptibility_percentage", 100),
    ],
)
def test_accepts_boundary_values(field, value):
    data = make_base()
    data[field] = value

    cfg = SessionConfig(**data)
    assert getattr(cfg, field) == value


def test_rejects_unknown_fields():
    data = make_base()
    data["unexpected_field"] = "surprise"

    with pytest.raises(ValidationError):
        SessionConfig(**data)


def test_model_validate_json_second_line_of_defense():
    """Matches how bot.py parses --config (same schema as the API)."""
    cfg = SessionConfig(**make_base())
    raw = cfg.model_dump_json()
    again = SessionConfig.model_validate_json(raw)
    assert again == cfg
