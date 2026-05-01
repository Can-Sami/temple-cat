"""Assembly checks for the Pipecat voice pipeline (mocked services, no network)."""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest

pytest.importorskip("pipecat.pipeline.pipeline")

from pipecat.services.deepgram.stt import DeepgramSTTService
from pipecat.services.openai.llm import OpenAILLMService

from bot import build_voice_pipeline_task
from bot import (
    AUDIO_IN_HZ,
    AUDIO_OUT_HZ,
    build_cartesia_input_params,
    build_daily_params,
    build_pipeline_params,
)
from app.models.config import SessionConfig


def _minimal_session_config(**overrides) -> SessionConfig:
    base = dict(
        system_prompt="You are a test bot.",
        llm_temperature=0.7,
        llm_max_tokens=256,
        stt_temperature=0.5,
        tts_voice="sonic",
        tts_speed=1.0,
        tts_temperature=0.6,
        interruptibility_percentage=50,
    )
    base.update(overrides)
    return SessionConfig.model_validate(base)


def test_build_daily_params_matches_transport_contract():
    dp = build_daily_params()
    assert dp.audio_in_enabled is True
    assert dp.audio_out_enabled is True
    assert dp.audio_in_sample_rate == AUDIO_IN_HZ
    assert dp.audio_out_sample_rate == AUDIO_OUT_HZ


def test_build_pipeline_params_metrics_only_when_tracing():
    off = build_pipeline_params(tracing=False)
    assert off.enable_metrics is False
    assert off.enable_usage_metrics is False
    assert off.audio_in_sample_rate == AUDIO_IN_HZ
    assert off.audio_out_sample_rate == AUDIO_OUT_HZ

    on = build_pipeline_params(tracing=True)
    assert on.enable_metrics is True
    assert on.enable_usage_metrics is True


def test_build_cartesia_input_params_uses_generation_config():
    cfg = _minimal_session_config(tts_speed=1.1, tts_temperature=1.0)
    params = build_cartesia_input_params(cfg)
    assert params.generation_config is not None
    assert params.generation_config.speed == pytest.approx(1.1)
    assert params.generation_config.volume == pytest.approx(1.25)


@pytest.fixture
def voice_env(monkeypatch):
    monkeypatch.setenv("DEEPGRAM_API_KEY", "dg-test")
    monkeypatch.setenv("OPENAI_API_KEY", "oa-test")
    monkeypatch.setenv("CARTESIA_API_KEY", "ca-test")


def test_build_voice_pipeline_task_processor_order_and_daily_params(voice_env):
    """Daily transport + linear pipeline order matches production wiring."""
    cfg = _minimal_session_config()

    mock_transport_in = MagicMock(name="transport_in")
    mock_transport_out = MagicMock(name="transport_out")
    mock_transport = MagicMock(name="DailyTransport_instance")
    mock_transport.input.return_value = mock_transport_in
    mock_transport.output.return_value = mock_transport_out

    mock_stt = MagicMock(name="DeepgramSTT")
    mock_llm = MagicMock(name="OpenAILLM")
    mock_tts = MagicMock(name="CartesiaTTS")

    mock_agg = MagicMock(name="aggregator_pair")
    mock_user = MagicMock(name="user_agg")
    mock_assistant = MagicMock(name="assistant_agg")
    mock_agg.user.return_value = mock_user
    mock_agg.assistant.return_value = mock_assistant

    mock_rtvi = MagicMock(name="RTVIProcessor")

    mock_pipeline_inst = MagicMock(name="pipeline")

    mock_dg_cls = MagicMock(return_value=mock_stt)
    mock_dg_cls.Settings = DeepgramSTTService.Settings

    mock_llm_cls = MagicMock(return_value=mock_llm)
    mock_llm_cls.Settings = OpenAILLMService.Settings

    with patch("bot.DailyTransport", return_value=mock_transport) as mock_daily_cls:
        with patch("bot.DeepgramSTTService", mock_dg_cls):
            with patch("bot.OpenAILLMService", mock_llm_cls):
                with patch("bot.CartesiaTTSService", return_value=mock_tts) as mock_ct_cls:
                    with patch("bot.SileroVADAnalyzer", return_value=MagicMock()):
                        with patch("bot.LLMContextAggregatorPair") as mock_pair_cls:
                            mock_pair_cls.return_value = mock_agg
                            with patch("bot.RTVIProcessor", return_value=mock_rtvi):
                                with patch("bot.Pipeline", return_value=mock_pipeline_inst) as mock_pipeline_cls:
                                    with patch("bot.PipelineTask") as mock_task_cls:
                                        mock_task_cls.return_value = MagicMock(name="PipelineTask")
                                        transport, task = build_voice_pipeline_task(
                                            "https://example.daily.co/r",
                                            "tok",
                                            cfg,
                                            conversation_id=None,
                                            tracing_on=False,
                                            otel_ready=False,
                                        )

    assert transport is mock_transport
    assert task is mock_task_cls.return_value

    mock_daily_cls.assert_called_once()
    room_url, token, bot_name, daily_params = mock_daily_cls.call_args[0]
    assert room_url == "https://example.daily.co/r"
    assert token == "tok"
    assert bot_name == "VoiceBot"
    assert daily_params.audio_in_sample_rate == AUDIO_IN_HZ
    assert daily_params.audio_out_sample_rate == AUDIO_OUT_HZ

    mock_dg_cls.assert_called_once()
    dg_kw = mock_dg_cls.call_args.kwargs
    assert dg_kw["sample_rate"] == AUDIO_IN_HZ
    assert dg_kw["api_key"] == os.environ["DEEPGRAM_API_KEY"]
    assert dg_kw["settings"].endpointing > 0

    mock_llm_cls.assert_called_once()
    llm_settings = mock_llm_cls.call_args.kwargs["settings"]
    assert llm_settings.model == "gpt-4o"
    assert llm_settings.temperature == cfg.llm_temperature

    mock_ct_cls.assert_called_once()
    ct_kw = mock_ct_cls.call_args.kwargs
    assert ct_kw["sample_rate"] == AUDIO_OUT_HZ
    assert ct_kw["params"].generation_config is not None

    processors = mock_pipeline_cls.call_args[0][0]
    assert processors == [
        mock_transport_in,
        mock_rtvi,
        mock_stt,
        mock_user,
        mock_llm,
        mock_tts,
        mock_transport_out,
        mock_assistant,
    ]


def test_build_voice_pipeline_task_tracing_passes_otel_flags(voice_env):
    cfg = _minimal_session_config()

    mock_transport = MagicMock()
    mock_transport.input.return_value = MagicMock()
    mock_transport.output.return_value = MagicMock()

    mock_dg_tr = MagicMock(return_value=MagicMock())
    mock_dg_tr.Settings = DeepgramSTTService.Settings
    mock_llm_tr = MagicMock(return_value=MagicMock())
    mock_llm_tr.Settings = OpenAILLMService.Settings

    with patch("bot.DailyTransport", return_value=mock_transport):
        with patch("bot.DeepgramSTTService", mock_dg_tr):
            with patch("bot.OpenAILLMService", mock_llm_tr):
                with patch("bot.CartesiaTTSService", return_value=MagicMock()):
                    with patch("bot.SileroVADAnalyzer", return_value=MagicMock()):
                        with patch("bot.LLMContextAggregatorPair") as mock_pair_cls:
                            inner = MagicMock()
                            inner.user.return_value = MagicMock()
                            inner.assistant.return_value = MagicMock()
                            mock_pair_cls.return_value = inner
                            with patch("bot.RTVIProcessor", return_value=MagicMock()):
                                with patch("bot.Pipeline", return_value=MagicMock()):
                                    with patch("bot.PipelineTask") as mock_task_cls:
                                        mock_task_cls.return_value = MagicMock()
                                        build_voice_pipeline_task(
                                            "https://x",
                                            "t",
                                            cfg,
                                            conversation_id="sess-1",
                                            tracing_on=True,
                                            otel_ready=True,
                                        )

    kwargs = mock_task_cls.call_args.kwargs
    assert kwargs["enable_tracing"] is True
    assert kwargs["enable_turn_tracking"] is True
    assert kwargs["conversation_id"] == "sess-1"
    assert kwargs["additional_span_attributes"] == {"session.id": "sess-1"}
