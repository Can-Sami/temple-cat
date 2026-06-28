"""Pipecat processor: emit a per-turn speaker label as an RTVI server-message (Freya 3).

Freya 3 uses Speechmatics streaming STT, which performs transcription AND speaker
diarization in one service. The Speechmatics service tags each final
``TranscriptionFrame`` with the speaker label on ``frame.user_id`` (e.g. ``"S1"``,
``"S2"``) while keeping ``frame.text`` as the plain transcript (the service's
default ``speaker_active_format`` is ``"{text}"``).

This processor mirrors ``DiarizationProcessor`` (Freya 1 / Deepgram): on each
final ``TranscriptionFrame`` it maps the Speechmatics speaker label to a 0-based
int and pushes an ``RTVIServerMessageFrame``; the already-installed
``RTVIObserver`` forwards it to the browser as ``RTVIEvent.ServerMessage``
(``{type: "speaker-transcript", speaker, text, final}``). The original frame is
always forwarded unchanged, and a malformed label can never crash the pipeline.
"""

from __future__ import annotations

import logging

from pipecat.frames.frames import Frame, InterimTranscriptionFrame, TranscriptionFrame
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor
from pipecat.processors.frameworks.rtvi import RTVIServerMessageFrame

_logger = logging.getLogger(__name__)


def speaker_label_to_index(label: object) -> int:
    """Map a Speechmatics speaker label to a 0-based speaker index.

    Speechmatics labels speakers as ``"S1"``, ``"S2"``, ... (1-based). We strip
    non-digits, subtract 1 and clamp to ``>= 0`` so ``"S1" -> 0``, ``"S2" -> 1``.
    Unknown / empty / non-numeric labels (e.g. ``""`` or ``"UU"``) fall back to 0.
    """
    digits = "".join(ch for ch in str(label or "") if ch.isdigit())
    if not digits:
        return 0
    try:
        return max(0, int(digits) - 1)
    except ValueError:
        return 0


class SpeechmaticsDiarizationProcessor(FrameProcessor):
    """Emit a typed speaker-transcript RTVI message on each final Speechmatics transcription."""

    async def process_frame(self, frame: Frame, direction: FrameDirection) -> None:
        await super().process_frame(frame, direction)

        is_final = isinstance(frame, TranscriptionFrame)
        is_interim = isinstance(frame, InterimTranscriptionFrame)
        if (is_final or is_interim) and direction == FrameDirection.DOWNSTREAM:
            try:
                speaker = speaker_label_to_index(getattr(frame, "user_id", None))
                if is_final:
                    text = frame.text or ""
                    # Diagnostic: shows the raw Speechmatics speaker label and the
                    # mapped 0-based index per finalized turn, so label drift is
                    # visible in the bot log.
                    _logger.info(
                        "diarization turn: label=%r speaker=%s text=%r",
                        getattr(frame, "user_id", None),
                        speaker,
                        text[:60],
                    )
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
                    # Live "who's talking now" off the interim — Speechmatics finals
                    # only arrive at end-of-utterance, so without this the indicator
                    # never lights up during continuous speech.
                    await self.push_frame(
                        RTVIServerMessageFrame(
                            data={"type": "speaker-active", "speaker": speaker}
                        ),
                        FrameDirection.DOWNSTREAM,
                    )
            except Exception:
                _logger.warning(
                    "speechmatics diarization speaker emit failed; passing frame through",
                    exc_info=True,
                )

        await self.push_frame(frame, direction)
