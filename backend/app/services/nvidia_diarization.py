"""Freya 2 diarization — per-turn speaker labels from the external /diarize model.

Unlike Freya 1 (Deepgram streaming, speaker rides on the transcript), this model
is a batch endpoint: POST an audio file, get speaker segments back. To keep
speaker identity stable across turns, we accumulate the user's mic audio for the
whole call and re-diarize the running audio on each finalized turn, taking the
speaker of the most recent segment as the current turn's speaker.

Two cooperating processors share one session buffer:
  - NvidiaAudioCapture  → placed BEFORE the STT service, buffers user PCM.
  - NvidiaSpeakerEmitter → placed AFTER the STT service, fires on each final
    TranscriptionFrame, diarizes the running audio, emits an RTVI server-message
    in the same shape Freya 1 uses ({type:"speaker-transcript", speaker, text}).
"""

from __future__ import annotations

import asyncio
import io
import logging
import wave

import httpx
from pipecat.frames.frames import Frame, InputAudioRawFrame, TranscriptionFrame
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor
from pipecat.processors.frameworks.rtvi import RTVIServerMessageFrame

_logger = logging.getLogger(__name__)

# Streaming/latency presets → /diarize form params. Names are customer-facing
# ("Fast/Balanced/Accurate"); the values are the model's chunk/context knobs.
DIARIZE_PROFILES: dict[str, dict[str, str]] = {
    "fast": {  # ultra-low latency (~0.32s) — snappiest, loosest separation
        "chunk_len": "3", "chunk_right_context": "1",
        "fifo_len": "188", "spkcache_update_period": "144", "spkcache_len": "188",
    },
    "balanced": {  # low latency (~1.04s)
        "chunk_len": "6", "chunk_right_context": "7",
        "fifo_len": "188", "spkcache_update_period": "144", "spkcache_len": "188",
    },
    "accurate": {  # high latency look-ahead — cleanest, still fast to compute
        "chunk_len": "124", "chunk_right_context": "1",
        "fifo_len": "124", "spkcache_update_period": "124", "spkcache_len": "188",
    },
}


class NvidiaDiarSession:
    """Accumulates the user's mic PCM for the whole call (16-bit mono)."""

    def __init__(self, sample_rate: int) -> None:
        self.sample_rate = sample_rate
        self._pcm = bytearray()

    def add(self, audio: bytes) -> None:
        self._pcm.extend(audio)

    def has_speech_worth_sending(self) -> bool:
        # >~0.5s of audio buffered (2 bytes/sample, mono).
        return len(self._pcm) > self.sample_rate

    def wav_bytes(self) -> bytes:
        buf = io.BytesIO()
        with wave.open(buf, "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(self.sample_rate)
            w.writeframes(bytes(self._pcm))
        return buf.getvalue()


class NvidiaAudioCapture(FrameProcessor):
    """Buffers user input audio into the shared session. Place BEFORE the STT service."""

    def __init__(self, session: NvidiaDiarSession) -> None:
        super().__init__()
        self._session = session

    async def process_frame(self, frame: Frame, direction: FrameDirection) -> None:
        await super().process_frame(frame, direction)
        if isinstance(frame, InputAudioRawFrame):
            self._session.add(frame.audio)
        await self.push_frame(frame, direction)


class NvidiaSpeakerEmitter(FrameProcessor):
    """On each final transcription, diarize the running audio and emit the current
    turn's speaker over RTVI. Place AFTER the STT service."""

    def __init__(self, session: NvidiaDiarSession, *, url: str, profile: str = "accurate") -> None:
        super().__init__()
        self._session = session
        self._url = url
        self._params = DIARIZE_PROFILES.get(profile, DIARIZE_PROFILES["accurate"])
        self._client = httpx.AsyncClient(timeout=httpx.Timeout(30.0, connect=5.0))
        self._tasks: set[asyncio.Task] = set()

    async def process_frame(self, frame: Frame, direction: FrameDirection) -> None:
        await super().process_frame(frame, direction)
        if (
            isinstance(frame, TranscriptionFrame)
            and direction == FrameDirection.DOWNSTREAM
            and (frame.text or "").strip()
            and self._url
            and self._session.has_speech_worth_sending()
        ):
            task = asyncio.create_task(self._diarize_and_emit(frame.text))
            self._tasks.add(task)
            task.add_done_callback(self._tasks.discard)
        await self.push_frame(frame, direction)

    async def _diarize_and_emit(self, text: str) -> None:
        try:
            wav = self._session.wav_bytes()
            resp = await self._client.post(
                self._url,
                files={"file": ("turn.wav", wav, "audio/wav")},
                data=self._params,
            )
            if resp.status_code != 200:
                _logger.warning("nvidia diarize HTTP %s: %s", resp.status_code, resp.text[:200])
                return
            segments = resp.json().get("segments", [])
            if not segments:
                return
            # Current turn = the latest segment (max end time).
            latest = max(segments, key=lambda s: s.get("end", 0.0))
            speaker_label = str(latest.get("speaker", "speaker_0"))
            try:
                speaker = int(speaker_label.rsplit("_", 1)[-1])
            except ValueError:
                speaker = 0
            await self.push_frame(
                RTVIServerMessageFrame(
                    data={"type": "speaker-transcript", "speaker": speaker, "text": text, "final": True}
                ),
                FrameDirection.DOWNSTREAM,
            )
        except Exception:
            _logger.warning("nvidia diarize/emit failed; turn shown without speaker", exc_info=True)

    async def cleanup(self) -> None:
        for task in list(self._tasks):
            task.cancel()
        await self._client.aclose()
        await super().cleanup()
