from app.services.openai_key_env import normalize_openai_api_key, openai_api_key_from_env


def test_normalize_strips_trailing_shell_redirect_char():
    assert normalize_openai_api_key("sk-proj-abc123def456>") == "sk-proj-abc123def456"


def test_normalize_strips_wrapping_double_quotes():
    assert normalize_openai_api_key('"sk-test-key"') == "sk-test-key"


def test_openai_api_key_from_env_reads_normalized(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test>")
    assert openai_api_key_from_env() == "sk-test"
