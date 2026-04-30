from fastapi.testclient import TestClient
from app.main import app

_VALID_PAYLOAD = {
    "system_prompt": "be concise",
    "llm_temperature": 0.5,
    "llm_max_tokens": 256,
    "stt_temperature": 0.0,
    "tts_voice": "sonic",
    "tts_speed": 1.0,
    "tts_temperature": 0.3,
    "interruptibility_percentage": 70,
}


def test_create_session_returns_session_id():
    client = TestClient(app)
    res = client.post("/api/sessions", json=_VALID_PAYLOAD)
    assert res.status_code == 201
    assert "session_id" in res.json()


def test_create_session_id_is_uuid_string():
    import uuid
    client = TestClient(app)
    res = client.post("/api/sessions", json=_VALID_PAYLOAD)
    assert res.status_code == 201
    # Must be a parseable UUID
    uuid.UUID(res.json()["session_id"])


def test_create_session_rejects_invalid_payload():
    client = TestClient(app)
    bad_payload = dict(_VALID_PAYLOAD)
    bad_payload["interruptibility_percentage"] = 999  # out of range
    res = client.post("/api/sessions", json=bad_payload)
    assert res.status_code == 422
