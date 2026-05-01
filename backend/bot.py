"""
Pipecat voice bot — spawned as a subprocess by the session endpoint.

Usage:
    python bot.py --room-url <url> --token <token> --body <json> [--conversation-id <uuid>]

    ``--config`` is a deprecated alias for ``--body`` (Pipecat ``DailyRunnerArguments.body``).

OpenTelemetry (optional): set ENABLE_TRACING=1 and OTLP env vars; see .env.example and DEPLOY.md.

Help Center RAG (optional): when RAG_ENABLED=1 (default in Compose), each user turn retrieves top Q&A
from Qdrant and injects a second system message before the LLM (see DEPLOY.md §8).

The session JSON (``--body`` / ``--config``) must match the SessionConfig schema:
    system_prompt, llm_temperature, llm_max_tokens,
    stt_temperature, tts_voice, tts_speed, tts_temperature,
    interruptibility_percentage

STT / TTS \"temperature\" (0–1 from the UI):
    Deepgram STT has no sampling temperature; we map stt_temperature to
    endpointing (silence ms before finalizing), per Pipecat Deepgram settings.
    Cartesia Sonic-3 exposes generation guidance via GenerationConfig; we map
    tts_temperature to volume (and keep explicit speed from the UI).
"""
from __future__ import annotations

import argparse
import asyncio
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
from pipecat.runner.types import DailyRunnerArguments
from pipecat.services.cartesia.tts import CartesiaTTSService, GenerationConfig
from pipecat.services.deepgram.stt import DeepgramSTTService
from pipecat.services.openai.llm import OpenAILLMService
from pipecat.transports.daily.transport import DailyParams, DailyTransport
from pipecat.turns.user_start import MinWordsUserTurnStartStrategy, VADUserTurnStartStrategy
from pipecat.turns.user_turn_strategies import UserTurnStrategies

from app.models.config import SessionConfig
from app.services.help_center_rag_processor import HelpCenterRAGProcessor
from app.services.openai_key_env import normalize_openai_api_key
from app.services.interruptibility import build_vad_tuning, interruptibility_min_words_threshold
from app.services.pipecat_tracing import configure_pipecat_tracing_from_env, tracing_enabled_from_env

AUDIO_IN_HZ = 16000
AUDIO_OUT_HZ = 24000


def build_daily_params() -> DailyParams:
    """Daily transport audio IO (Pipecat DailyParams / TransportParams)."""
    return DailyParams(
        audio_in_enabled=True,
        audio_out_enabled=True,
        audio_in_sample_rate=AUDIO_IN_HZ,
        audio_out_sample_rate=AUDIO_OUT_HZ,
    )


def build_vad_stop_secs(interruptibility_percentage: int) -> float:
    """Map interruptibility % to Silero VAD ``stop_secs`` (end-of-speech sensitivity)."""
    return build_vad_tuning(interruptibility_percentage).stop_secs


def stt_endpointing_ms(stt_temperature: float) -> int:
    """Map UI STT temperature [0, 1] to Deepgram endpointing (silence ms).

    Lower temperature -> longer endpointing (fewer aggressive phrase cuts).
    Higher temperature -> shorter endpointing (snappier finalization).
    """
    t = max(0.0, min(1.0, float(stt_temperature)))
    # 0 -> 450 ms, 1 -> 80 ms
    return int(round(450.0 - t * 370.0))


def build_cartesia_input_params(config: SessionConfig) -> CartesiaTTSService.InputParams:
    """Cartesia Sonic-3 generation guidance via GenerationConfig (pipecat-ai 1.1.x)."""
    speed = float(config.tts_speed)
    tts_temp = max(0.0, min(1.0, float(config.tts_temperature)))
    volume = max(0.5, min(2.0, 0.7 + 0.55 * tts_temp))
    return CartesiaTTSService.InputParams(
        generation_config=GenerationConfig(speed=speed, volume=volume),
    )


def build_pipeline_params(*, conversation_id: str | None, session_config_json: str | None) -> PipelineParams:
    """Pipeline-wide audio sample rates; metrics/TTFB always on for RTVI (tracing adds OTLP)."""
    meta: dict[str, Any] = {}
    if conversation_id:
        meta["session_id"] = conversation_id
    if session_config_json:
        meta["session_config"] = session_config_json

    return PipelineParams(
        audio_in_sample_rate=AUDIO_IN_HZ,
        audio_out_sample_rate=AUDIO_OUT_HZ,
        enable_metrics=True,
        enable_usage_metrics=True,
        report_only_initial_ttfb=True,
        start_metadata=meta,
    )


def build_user_turn_strategies(interruptibility_percentage: int) -> UserTurnStrategies:
    """Map interruptibility % to Pipecat user-turn strategies (min words + VAD; no raw transcription short-circuit)."""
    min_words, allow_interruptions = interruptibility_min_words_threshold(interruptibility_percentage)
    return UserTurnStrategies(
        start=[
            MinWordsUserTurnStartStrategy(
                min_words=min_words,
                enable_interruptions=allow_interruptions,
            ),
            VADUserTurnStartStrategy(enable_interruptions=allow_interruptions),
        ],
        stop=None,
    )


def build_voice_pipeline_task(
    room_url: str,
    token: str,
    config: SessionConfig,
    *,
    conversation_id: str | None,
    tracing_on: bool,
    otel_ready: bool,
) -> tuple[DailyTransport, PipelineTask]:
    """Wire Pipecat processors into a ``PipelineTask`` (handlers and runner are ``run_bot``'s job)."""
    vad = build_vad_tuning(config.interruptibility_percentage)
    turn_strategies = build_user_turn_strategies(config.interruptibility_percentage)
    min_words, allow_interrupt = interruptibility_min_words_threshold(config.interruptibility_percentage)
    _logger.info(
        "starting voice bot interruptibility=%s%% min_words_interrupt=%s allow_interruptions=%s "
        "vad_stop_secs=%.3f vad_start_secs=%.3f preemption=start_vol/conf=%.2f/%.2f",
        config.interruptibility_percentage,
        min_words,
        allow_interrupt,
        vad.stop_secs,
        vad.start_secs,
        vad.min_volume,
        vad.confidence,
    )

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
            endpointing=stt_endpointing_ms(config.stt_temperature),
        ),
    )

    llm = OpenAILLMService(
        api_key=normalize_openai_api_key(os.environ["OPENAI_API_KEY"]),
        settings=OpenAILLMService.Settings(
            model="gpt-4o",
            system_instruction=config.system_prompt,
            temperature=config.llm_temperature,
            max_completion_tokens=config.llm_max_tokens,
        ),
    )

    voice_name = config.tts_voice
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

    context = LLMContext(messages=[])

    context_aggregator = LLMContextAggregatorPair(
        context,
        user_params=LLMUserAggregatorParams(
            user_turn_strategies=turn_strategies,
            vad_analyzer=SileroVADAnalyzer(
                params=VADParams(
                    stop_secs=vad.stop_secs,
                    start_secs=vad.start_secs,
                    confidence=vad.confidence,
                    min_volume=vad.min_volume,
                ),
            ),
        ),
    )

    rtvi = RTVIProcessor()
    help_center_rag = HelpCenterRAGProcessor()

    pipeline = Pipeline(
        [
            transport.input(),
            rtvi,
            stt,
            context_aggregator.user(),
            help_center_rag,
            llm,
            tts,
            transport.output(),
            context_aggregator.assistant(),
        ]
    )

    task_kw: dict[str, Any] = {
        "pipeline": pipeline,
        "params": build_pipeline_params(
            conversation_id=conversation_id,
            session_config_json=config.model_dump_json(),
        ),
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
    return transport, task


async def run_bot(runner_args: DailyRunnerArguments, *, conversation_id: str | None) -> None:
    """Run the voice bot using Pipecat runner-style session arguments (Daily room + JSON body)."""
    config = SessionConfig.model_validate(runner_args.body or {})

    tracing_on = tracing_enabled_from_env()
    otel_ready = configure_pipecat_tracing_from_env() if tracing_on else False

    transport, task = build_voice_pipeline_task(
        runner_args.room_url,
        runner_args.token or "",
        config,
        conversation_id=conversation_id,
        tracing_on=tracing_on,
        otel_ready=otel_ready,
    )

    @transport.event_handler("on_first_participant_joined")
    async def on_first_participant_joined(transport, participant):
        await transport.capture_participant_transcription(participant["id"])

    @transport.event_handler("on_client_disconnected")
    async def on_client_disconnected(transport, participant):
        await task.cancel()

    runner = PipelineRunner(handle_sigint=True)
    await runner.run(task)


if __name__ == "__main__":
    import json

    from pydantic import ValidationError

    parser = argparse.ArgumentParser()
    parser.add_argument("--room-url", required=True)
    parser.add_argument("--token", required=True)
    parser.add_argument(
        "--body",
        default=None,
        help="JSON object: SessionConfig fields (DailyRunnerArguments.body / Pipecat runner canonical)",
    )
    parser.add_argument(
        "--config",
        default=None,
        help="Deprecated alias for --body (JSON-encoded SessionConfig)",
    )
    parser.add_argument(
        "--conversation-id",
        default=None,
        help="Session id for OTEL conversation_id / span attributes (recommended when tracing)",
    )
    args = parser.parse_args()

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

    _configure_logging()
    payload = args.body or args.config
    if not payload:
        _logger.error("subprocess requires --body or --config")
        sys.exit(2)
    try:
        body = json.loads(payload)
        SessionConfig.model_validate(body)
    except (json.JSONDecodeError, ValidationError) as exc:
        _logger.error("invalid SessionConfig JSON in subprocess: %s", exc)
        sys.exit(2)

    runner_args = DailyRunnerArguments(room_url=args.room_url, token=args.token, body=body)
    asyncio.run(run_bot(runner_args, conversation_id=args.conversation_id))
