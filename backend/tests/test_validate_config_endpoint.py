import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch

from app.main import app


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


def test_validate_config_valid_payload():
    client = TestClient(app)
    resp = client.post("/api/validate-config", json=make_base())
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("valid") is True
    assert "message" in data and isinstance(data["message"], str)


def test_validate_config_invalid_payload_bounds():
    client = TestClient(app)
    data = make_base()
    data["interruptibility_percentage"] = 120
    resp = client.post("/api/validate-config", json=data)
    assert resp.status_code == 422


def test_validate_config_unknown_field():
    client = TestClient(app)
    data = make_base()
    data["unexpected_field"] = "surprise"
    resp = client.post("/api/validate-config", json=data)
    assert resp.status_code == 422


@patch("app.main._validate_config_limiter")
def test_validate_config_returns_429_when_rate_limited(mock_lim):
    mock_lim.allow.return_value = False
    client = TestClient(app)
    resp = client.post("/api/validate-config", json=make_base())
    assert resp.status_code == 429
