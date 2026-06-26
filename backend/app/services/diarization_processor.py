"""Pipecat processor: emit a per-turn speaker label as an RTVI server-message.

On each final ``TranscriptionFrame`` it reads the dominant speaker off the
Deepgram result and pushes an ``RTVIServerMessageFrame``; the already-installed
``RTVIObserver`` forwards that to the browser as ``RTVIEvent.ServerMessage``
(``{type: "speaker-transcript", speaker, text, final}``). The original frame is
always forwarded unchanged, and a malformed result can never crash the pipeline.
"""

from __future__ import annotations

import logging

from pipecat.frames.frames import Frame, TranscriptionFrame
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor
from pipecat.processors.frameworks.rtvi import RTVIServerMessageFrame

from app.services.diarization import dominant_speaker

_logger = logging.getLogger(__name__)


class DiarizationProcessor(FrameProcessor):
    """Emit a typed speaker-transcript RTVI message on each final transcription."""

    async def process_frame(self, frame: Frame, direction: FrameDirection) -> None:
        await super().process_frame(frame, direction)

        if isinstance(frame, TranscriptionFrame) and direction == FrameDirection.DOWNSTREAM:
            try:
                speaker, text = dominant_speaker(getattr(frame, "result", None))
                if not text:
                    text = frame.text or ""
                # Diagnostic: shows the raw Deepgram speaker index Deepgram assigned
                # to each finalized turn, so label drift is visible in the bot log.
                _logger.info("diarization turn: speaker=%s text=%r", speaker, text[:60])
                await self.push_frame(
                    RTVIServerMessageFrame(
                        data={
                            "type": "speaker-transcript",
                            "speaker": speaker,
                            "text": text,
                            "final": True,
                        }
                    ),
                    FrameDirection.DOWNSTREAM,
                )
            except Exception:
                _logger.warning(
                    "diarization speaker emit failed; passing frame through", exc_info=True
                )

        await self.push_frame(frame, direction)
