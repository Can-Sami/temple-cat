from unittest.mock import MagicMock

import pytest

from app.services import pipecat_tracing

pytest.importorskip("pipecat.utils.tracing.setup")


def test_tracing_disabled_by_default(monkeypatch):
    monkeypatch.delenv("ENABLE_TRACING", raising=False)
    assert pipecat_tracing.tracing_enabled_from_env() is False


def test_tracing_enabled(monkeypatch):
    monkeypatch.setenv("ENABLE_TRACING", "1")
    assert pipecat_tracing.tracing_enabled_from_env() is True


def test_configure_skips_when_disabled(monkeypatch):
    monkeypatch.delenv("ENABLE_TRACING", raising=False)
    assert pipecat_tracing.configure_pipecat_tracing_from_env() is False


def test_configure_calls_setup_when_enabled(monkeypatch):
    monkeypatch.setenv("ENABLE_TRACING", "1")
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://collector:4317")

    monkeypatch.setattr(pipecat_tracing, "_build_otlp_exporter", lambda: MagicMock(name="exporter"))

    import pipecat.utils.tracing.setup as setup_mod

    fake_setup = MagicMock(return_value=True)
    monkeypatch.setattr(setup_mod, "is_tracing_available", lambda: True)
    monkeypatch.setattr(setup_mod, "setup_tracing", fake_setup)

    assert pipecat_tracing.configure_pipecat_tracing_from_env() is True
    fake_setup.assert_called_once()
    kwargs = fake_setup.call_args.kwargs
    assert kwargs["service_name"] == "temple-cat-voice-bot"
    assert kwargs["console_export"] is False
