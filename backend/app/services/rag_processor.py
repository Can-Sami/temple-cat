from __future__ import annotations

import logging
from typing import Any

from pipecat.frames.frames import LLMMessagesTransformFrame, TranscriptionFrame
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor

from app.services.retrieval_runtime import maybe_build_help_center_system_message

_logger = logging.getLogger(__name__)

_HELP_CENTER_PREFIX = "Help Center Context (retrieved; may be incomplete):"


class HelpCenterRAGInjector(FrameProcessor):
    """Inject per-turn help-center retrieval context into the LLM message list.

    Strategy:
    - When a finalized `TranscriptionFrame` arrives, perform retrieval for that text.
    - Emit an `LLMMessagesTransformFrame` that:
      - removes any previous help-center context system messages
      - appends the newest help-center context system message (if any)
    - Pass the original transcription frame downstream unchanged.

    This keeps RAG context scoped to "latest user turn" without unbounded growth.
    """

    def __init__(self) -> None:
        super().__init__()
        self._pending_system_message: dict[str, Any] | None = None

    async def process_frame(self, frame, direction: FrameDirection):  # type: ignore[override]
        if isinstance(frame, TranscriptionFrame) and getattr(frame, "finalized", False):
            user_text = getattr(frame, "text", "").strip()
            if user_text:
                try:
                    self._pending_system_message = await maybe_build_help_center_system_message(user_text)
                except Exception:
                    _logger.exception("rag injection failed; continuing without context")
                    self._pending_system_message = None

                await self.push_frame(
                    LLMMessagesTransformFrame(transform=self._transform_messages),
                    direction=direction,
                )

        await self.push_frame(frame, direction)

    def _transform_messages(self, messages: list[dict[str, Any]]):  # pipecat expects LLMContextMessage-compatible
        cleaned: list[dict[str, Any]] = []
        for m in messages:
            if (
                isinstance(m, dict)
                and m.get("role") == "system"
                and isinstance(m.get("content"), str)
                and m["content"].startswith(_HELP_CENTER_PREFIX)
            ):
                continue
            cleaned.append(m)

        if self._pending_system_message:
            cleaned.append(self._pending_system_message)
        return cleaned

