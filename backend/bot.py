"""
Pipecat voice bot — spawned as a subprocess by the session endpoint.

Usage:
    python bot.py --room-url <url> --token <token> --config <json>

The --config JSON must match the SessionConfig schema:
    system_prompt, llm_temperature, llm_max_tokens,
    stt_temperature, tts_voice, tts_speed, tts_temperature,
    interruptibility_percentage
"""
import argparse
import asyncio
import json
import os
import sys

from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.aggregators.llm_context import LLMContext
from pipecat.processors.aggregators.llm_response_universal import (
    LLMContextAggregatorPair,
    LLMUserAggregatorParams,
)
from pipecat.processors.frameworks.rtvi import RTVIProcessor
from pipecat.services.cartesia.tts import CartesiaTTSService
from pipecat.services.deepgram.stt import DeepgramSTTService
from pipecat.services.openai.llm import OpenAILLMService
from pipecat.transports.daily.transport import DailyParams, DailyTransport

from app.services.interruptibility import build_interruptibility_policy


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


async def run_bot(room_url: str, token: str, config: dict) -> None:
    transport = DailyTransport(
        room_url,
        token,
        "VoiceBot",
        DailyParams(audio_in_enabled=True, audio_out_enabled=True),
    )

    stt = DeepgramSTTService(
        api_key=os.environ["DEEPGRAM_API_KEY"],
    )

    llm = OpenAILLMService(
        api_key=os.environ["OPENAI_API_KEY"],
        model="gpt-4o",
        params=OpenAILLMService.InputParams(
            temperature=config["llm_temperature"],
            max_tokens=config["llm_max_tokens"],
        ),
    )

    tts = CartesiaTTSService(
        api_key=os.environ["CARTESIA_API_KEY"],
        voice_id=config["tts_voice"],
        params=CartesiaTTSService.InputParams(
            speed=config["tts_speed"],
        ),
    )

    context = LLMContext(
        messages=build_system_messages(config["system_prompt"])
    )

    vad_stop_secs = build_vad_stop_secs(config["interruptibility_percentage"])
    context_aggregator = LLMContextAggregatorPair(
        context,
        user_params=LLMUserAggregatorParams(
            vad_analyzer=SileroVADAnalyzer(params=dict(stop_secs=vad_stop_secs))
        )
    )

    # Inject RTVIProcessor to handle Pipecat client SDK events natively
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

    task = PipelineTask(pipeline, PipelineParams(allow_interruptions=True))

    @transport.event_handler("on_first_participant_joined")
    async def on_first_participant_joined(transport, participant):
        await transport.capture_participant_transcription(participant["id"])

    runner = PipelineRunner()
    await runner.run(task)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--room-url", required=True)
    parser.add_argument("--token", required=True)
    parser.add_argument("--config", required=True, help="JSON-encoded SessionConfig")
    args = parser.parse_args()

    # ensure absolute imports work by adding backend to sys.path
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

    config_data = json.loads(args.config)
    asyncio.run(run_bot(args.room_url, args.token, config_data))
