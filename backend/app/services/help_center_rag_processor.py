"""Pipecat processor: inject Help Center Q&A into LLM context per turn."""

from __future__ import annotations

import logging

from pipecat.frames.frames import LLMContextFrame
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor

from app.services.rag_env import rag_enabled_from_env
from app.services.retrieval_runtime import (
    build_help_center_context_block,
    insert_help_center_system_message,
    latest_user_query_text,
    retrieve_help_center_entries,
    strip_help_center_messages,
)

_logger = logging.getLogger(__name__)


class HelpCenterRAGProcessor(FrameProcessor):
    """On each ``LLMContextFrame``, append retrieved Help Center context as a system message."""

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        await super().process_frame(frame, direction)

        if not rag_enabled_from_env():
            await self.push_frame(frame, direction)
            return

        if isinstance(frame, LLMContextFrame) and direction == FrameDirection.DOWNSTREAM:
            try:
                ctx = frame.context
                base_messages = strip_help_center_messages(ctx.get_messages())
                ctx.set_messages(base_messages)

                query = latest_user_query_text(base_messages)
                if query:
                    entries = await retrieve_help_center_entries(query)
                    if entries:
                        block = build_help_center_context_block(entries)
                        if block:
                            ctx.set_messages(insert_help_center_system_message(base_messages, block))
            except Exception:
                _logger.warning("Help Center RAG injection failed; continuing without it", exc_info=True)

        await self.push_frame(frame, direction)
