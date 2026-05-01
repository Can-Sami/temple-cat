"""
Pipecat voice bot — spawned as a subprocess by the session endpoint.

Usage:
    python bot.py --room-url <url> --token <token> --config <json> [--conversation-id <uuid>]

OpenTelemetry (optional): set ENABLE_TRACING=1 and OTLP env vars; see .env.example and DEPLOY.md.

The --config JSON must match the SessionConfig schema:
    system_prompt, llm_temperature, llm_max_tokens,
    stt_temperature, tts_voice, tts_speed, tts_temperature,
    interruptibility_percentage

STT / TTS \"temperature\" (0–1 from the UI):
    Deepgram STT has no sampling temperature; we map stt_temperature to
    endpointing (silence ms before finalizing), per Pipecat Deepgram settings.
    Cartesia Sonic has no temperature knob; we map tts_temperature to
    generation volume on Sonic-3 (GenerationConfig), or legacy emotion presets.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys
from typing import Any

_logger = logging.getLogger(__name__)


def _configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        force=True,
    )

from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.audio.vad.vad_analyzer import VADParams
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.aggregators.llm_context import LLMContext
from pipecat.processors.aggregators.llm_response_universal import (
    LLMContextAggregatorPair,
    LLMUserAggregatorParams,
)
from pipecat.processors.frameworks.rtvi import RTVIObserver, RTVIProcessor
from pipecat.services.cartesia.tts import CartesiaTTSService
from pipecat.services.deepgram.stt import DeepgramSTTService
from pipecat.services.openai.llm import OpenAILLMService
from pipecat.transports.daily.transport import DailyParams, DailyTransport

from app.services.interruptibility import build_interruptibility_policy
from app.services.pipecat_tracing import configure_pipecat_tracing_from_env, tracing_enabled_from_env

AUDIO_IN_HZ = 16000
AUDIO_OUT_HZ = 24000


def _model_fields(cls: type) -> Any:
    """Pydantic v2 ``model_fields`` or v1 ``__fields__``."""
    return getattr(cls, "model_fields", None) or getattr(cls, "__fields__", {})


def build_daily_params() -> DailyParams:
    """Daily transport audio IO; input rate omitted on older Pipecat builds."""
    kwargs: dict[str, Any] = {
        "audio_in_enabled": True,
        "audio_out_enabled": True,
        "audio_out_sample_rate": AUDIO_OUT_HZ,
    }
    if "audio_in_sample_rate" in _model_fields(DailyParams):
        kwargs["audio_in_sample_rate"] = AUDIO_IN_HZ
    return DailyParams(**kwargs)


def build_system_messages(system_prompt: str) -> list[dict]:
    """Wrap the user-supplied prompt as an OpenAI system message."""
    return [{"role": "system", "content": system_prompt}]


def build_vad_stop_secs(interruptibility_percentage: int) -> float:
    """Map interruptibility % to Silero VAD stop_secs.

    High interruptibility -> short stop_secs (bot yields to user quickly).
    Low interruptibility  -> long stop_secs  (bot holds the floor).
    """
    policy = build_interruptibility_policy(interruptibility_percentage)
    # Map min_user_speech_ms linearly to VAD stop_secs range [0.15, 0.80]
    # policy.min_user_speech_ms is in [100, 300] from our interruptibility service
    clamped = max(100, min(300, policy.min_user_speech_ms))
    return 0.15 + (clamped - 100) / 200 * 0.65  # maps 100->0.15, 300->0.80


def stt_endpointing_ms(stt_temperature: float) -> int:
    """Map UI STT temperature [0, 1] to Deepgram endpointing (silence ms).

    Lower temperature -> longer endpointing (fewer aggressive phrase cuts).
    Higher temperature -> shorter endpointing (snappier finalization).
    """
    t = max(0.0, min(1.0, float(stt_temperature)))
    # 0 -> 450 ms, 1 -> 80 ms
    return int(round(450.0 - t * 370.0))


def build_cartesia_input_params(config: dict[str, Any]) -> CartesiaTTSService.InputParams:
    """Build Cartesia params for both Sonic-3 (GenerationConfig) and legacy InputParams."""
    InputParams = CartesiaTTSService.InputParams
    speed = float(config["tts_speed"])
    tts_temp = max(0.0, min(1.0, float(config["tts_temperature"])))
    volume = max(0.5, min(2.0, 0.7 + 0.55 * tts_temp))

    field_names = _model_fields(InputParams)
    if "generation_config" in field_names:
        from pipecat.services.cartesia.tts import GenerationConfig

        return InputParams(
            generation_config=GenerationConfig(speed=speed, volume=volume),
        )

    # Legacy Cartesia (e.g. sonic-2): categorical speed + optional emotion list
    def speed_preset(s: float) -> str:
        if s < 0.9:
            return "slow"
        if s > 1.1:
            return "fast"
        return "normal"

    kwargs: dict[str, Any] = {}
    if "speed" in field_names:
        kwargs["speed"] = speed_preset(speed)
    if "emotion" in field_names:
        kwargs["emotion"] = ["excited"] if tts_temp >= 0.5 else []
    return InputParams(**kwargs)


def build_pipeline_params(*, tracing: bool) -> PipelineParams:
    """Pipeline-wide audio rates; allow_interruptions when supported by this Pipecat version."""
    base: dict[str, Any] = {"audio_in_sample_rate": AUDIO_IN_HZ, "audio_out_sample_rate": AUDIO_OUT_HZ}
    if tracing:
        base["enable_metrics"] = True
        base["enable_usage_metrics"] = True
    if "allow_interruptions" in _model_fields(PipelineParams):
        base["allow_interruptions"] = True
    return PipelineParams(**base)


async def run_bot(
    room_url: str,
    token: str,
    config: dict[str, Any],
    *,
    conversation_id: str | None,
) -> None:
    _logger.info(
        "starting voice bot interruptibility=%s%%",
        config.get("interruptibility_percentage"),
    )

    tracing_on = tracing_enabled_from_env()
    otel_ready = configure_pipecat_tracing_from_env() if tracing_on else False

    transport = DailyTransport(
        room_url,
        token,
        "VoiceBot",
        build_daily_params(),
    )

    stt = DeepgramSTTService(
        api_key=os.environ["DEEPGRAM_API_KEY"],
        sample_rate=AUDIO_IN_HZ,
        settings=DeepgramSTTService.Settings(
            endpointing=stt_endpointing_ms(config["stt_temperature"]),
        ),
    )

    llm = OpenAILLMService(
        api_key=os.environ["OPENAI_API_KEY"],
        settings=OpenAILLMService.Settings(
            model="gpt-4o",
            temperature=config["llm_temperature"],
            max_tokens=config["llm_max_tokens"],
        ),
    )

    voice_name = config["tts_voice"]
    voice_map = {
        "sonic": "79a125e8-cd45-4c13-8a67-188112f4dd22",
        "alloy": "79a125e8-cd45-4c13-8a67-188112f4dd22",  # fallback
        "katie": "f786b574-daa5-4673-aa0c-cbe3e8534c02",
        "kiefer": "228fca29-3a0a-435c-8728-5cb483251068",
        "tessa": "6ccbfb76-1fc6-48f7-b71d-91ac6298247b",
        "kyle": "c961b81c-a935-4c17-bfb3-ba2239de8c2f",
    }
    voice_uuid = voice_map.get(voice_name.lower(), voice_name)

    tts = CartesiaTTSService(
        api_key=os.environ["CARTESIA_API_KEY"],
        voice_id=voice_uuid,
        sample_rate=AUDIO_OUT_HZ,
        params=build_cartesia_input_params(config),
    )

    context = LLMContext(messages=build_system_messages(config["system_prompt"]))

    vad_stop_secs = build_vad_stop_secs(config["interruptibility_percentage"])
    context_aggregator = LLMContextAggregatorPair(
        context,
        user_params=LLMUserAggregatorParams(
            vad_analyzer=SileroVADAnalyzer(params=VADParams(stop_secs=vad_stop_secs)),
        ),
    )

    rtvi = RTVIProcessor()

    pipeline = Pipeline(
        [
            transport.input(),
            rtvi,
            stt,
            context_aggregator.user(),
            llm,
            tts,
            transport.output(),
            context_aggregator.assistant(),
        ]
    )

    task_kw: dict[str, Any] = {
        "pipeline": pipeline,
        "params": build_pipeline_params(tracing=tracing_on),
        "observers": [RTVIObserver(rtvi=rtvi)],
    }
    if tracing_on and otel_ready:
        task_kw["enable_tracing"] = True
        task_kw["enable_turn_tracking"] = True
        if conversation_id:
            task_kw["conversation_id"] = conversation_id
            task_kw["additional_span_attributes"] = {"session.id": conversation_id}
    elif tracing_on and not otel_ready:
        _logger.warning(
            "ENABLE_TRACING set but OpenTelemetry did not initialize; running without Pipecat traces"
        )

    task = PipelineTask(**task_kw)

    @transport.event_handler("on_first_participant_joined")
    async def on_first_participant_joined(transport, participant):
        await transport.capture_participant_transcription(participant["id"])

    @transport.event_handler("on_client_disconnected")
    async def on_client_disconnected(transport, participant):
        await task.cancel()

    runner = PipelineRunner(handle_sigint=True)
    await runner.run(task)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--room-url", required=True)
    parser.add_argument("--token", required=True)
    parser.add_argument("--config", required=True, help="JSON-encoded SessionConfig")
    parser.add_argument(
        "--conversation-id",
        default=None,
        help="Session id for OTEL conversation_id / span attributes (recommended when tracing)",
    )
    args = parser.parse_args()

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

    _configure_logging()
    config_data = json.loads(args.config)
    asyncio.run(
        run_bot(
            args.room_url,
            args.token,
            config_data,
            conversation_id=args.conversation_id,
        )
    )
