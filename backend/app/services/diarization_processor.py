"""Pipecat processor: emit a per-turn speaker label as an RTVI server-message.

On each final ``TranscriptionFrame`` it reads the dominant speaker off the
Deepgram result and pushes an ``RTVIServerMessageFrame``; the already-installed
``RTVIObserver`` forwards that to the browser as ``RTVIEvent.ServerMessage``
(``{type: "speaker-transcript", speaker, text, final}``). The original frame is
always forwarded unchanged, and a malformed result can never crash the pipeline.
"""

from __future__ import annotations

import logging

from pipecat.frames.frames import Frame, InterimTranscriptionFrame, TranscriptionFrame
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor
from pipecat.processors.frameworks.rtvi import RTVIServerMessageFrame

from app.services.diarization import dominant_speaker

_logger = logging.getLogger(__name__)


class DiarizationProcessor(FrameProcessor):
    """Emit speaker labels as RTVI messages: a final ``speaker-transcript`` per
    finalized turn, plus a live ``speaker-active`` off each interim so the
    diarization indicator lights up immediately (Deepgram finals only arrive
    after endpointing silence)."""

    async def process_frame(self, frame: Frame, direction: FrameDirection) -> None:
        await super().process_frame(frame, direction)

        is_final = isinstance(frame, TranscriptionFrame)
        is_interim = isinstance(frame, InterimTranscriptionFrame)
        if (is_final or is_interim) and direction == FrameDirection.DOWNSTREAM:
            try:
                speaker, text = dominant_speaker(getattr(frame, "result", None))
                if not text:
                    text = frame.text or ""
                if is_final:
                    # Diagnostic: shows the raw Deepgram speaker index per finalized
                    # turn, so label drift is visible in the bot log.
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
                else:
                    # Live "who's talking now" — no text, so the full-assistant
                    # transcript never sees partial spam; only the indicator reacts.
                    await self.push_frame(
                        RTVIServerMessageFrame(
                            data={"type": "speaker-active", "speaker": speaker}
                        ),
                        FrameDirection.DOWNSTREAM,
                    )
            except Exception:
                _logger.warning(
                    "diarization speaker emit failed; passing frame through", exc_info=True
                )

        await self.push_frame(frame, direction)
