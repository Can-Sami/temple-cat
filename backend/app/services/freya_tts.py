"""Freya TTS service (OpenAI-compatible ``/audio/speech``, returns 48 kHz PCM).

A slim ``OpenAITTSService`` subclass that talks to Freya's TTS endpoint with a
raw ``httpx`` client carrying ONLY ``Authorization`` + ``Content-Type`` headers.
The OpenAI Python SDK injects ``X-Stainless-*`` headers that trip the Cloudflare
WAF in front of the cloud speech endpoint, so the synthesis request bypasses the
SDK entirely and streams raw signed-16-bit little-endian PCM back as
``TTSAudioRawFrame``s.

API surface mirrors pipecat-ai 1.1.0: ``run_tts(self, text, context_id)`` and
``TTSAudioRawFrame(audio, sample_rate, num_channels, context_id=...)``.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

import httpx
from loguru import logger
from pipecat.frames.frames import ErrorFrame, Frame, TTSAudioRawFrame
from pipecat.services.openai.tts import OpenAITTSService

# 16-bit PCM => 2 bytes per sample. Frames handed to the resampler must contain
# whole samples, so odd trailing bytes are buffered across chunk boundaries.
_SAMPLE_WIDTH = 2


class FreyaTTSService(OpenAITTSService):
    """Freya TTS over the OpenAI-compatible ``/audio/speech`` endpoint."""

    def __init__(
        self,
        *,
        api_key: str | None,
        base_url: str,
        voice: str = "alloy",
        model: str = "freya-tts",
        sample_rate: int = 48000,
        speed: float | None = None,
        **kwargs,
    ) -> None:
        super().__init__(
            api_key=api_key,
            base_url=base_url,
            sample_rate=sample_rate,
            settings=OpenAITTSService.Settings(model=model, voice=voice, speed=speed),
            **kwargs,
        )
        # Clean httpx client: only Authorization + Content-Type, no X-Stainless-*
        # headers (the OpenAI SDK adds those and the Freya WAF rejects them).
        self._http_client = httpx.AsyncClient(
            headers={
                "Authorization": f"Bearer {self._client.api_key}",
                "Content-Type": "application/json",
            },
            timeout=httpx.Timeout(30.0, connect=5.0),
        )
        # Resolve the absolute synthesis endpoint once. The Freya/KKB speech API
        # serves at exactly ``{host}/v1/audio/speech`` (verified: ``/audio/speech``
        # 404s). Normalize to one ``/v1`` regardless of how base_url was given —
        # mirrors Freya's ``doctor.py`` resolution.
        base = str(self._client.base_url).rstrip("/")
        if base.endswith("/v1"):
            base = base[: -len("/v1")]
        self._speech_url = f"{base}/v1/audio/speech"

    async def run_tts(self, text: str, context_id: str) -> AsyncGenerator[Frame, None]:
        """Synthesize ``text`` to streamed 48 kHz mono PCM audio frames.

        Yields ``TTSAudioRawFrame``s on success, or a single ``ErrorFrame`` on a
        non-200 response or transport failure.
        """
        text = " ".join(text.split())
        logger.debug(f"{self}: Generating TTS [{text}]")
        try:
            await self.start_ttfb_metrics()

            body: dict = {
                "input": text,
                "model": self._settings.model,
                "voice": self._settings.voice,
                "response_format": "pcm",
            }
            if self._settings.instructions:
                body["instructions"] = self._settings.instructions
            if self._settings.speed:
                body["speed"] = self._settings.speed

            async with self._http_client.stream("POST", self._speech_url, json=body) as r:
                if r.status_code != 200:
                    error_text = ""
                    async for chunk in r.aiter_bytes():
                        error_text += chunk.decode(errors="replace")
                    logger.error(f"{self} TTS error (status {r.status_code}): {error_text}")
                    yield ErrorFrame(error=f"TTS error (status {r.status_code}): {error_text}")
                    return

                await self.start_tts_usage_metrics(text)

                remainder = b""
                first_data = True
                async for chunk in r.aiter_bytes():
                    if not chunk:
                        continue
                    data = remainder + chunk
                    usable = len(data) - (len(data) % _SAMPLE_WIDTH)
                    remainder = data[usable:]
                    if usable <= 0:
                        continue
                    if first_data:
                        await self.stop_ttfb_metrics()
                        first_data = False
                    yield TTSAudioRawFrame(data[:usable], self.sample_rate, 1, context_id=context_id)

                # Flush any trailing whole sample left in the buffer.
                if len(remainder) >= _SAMPLE_WIDTH:
                    usable = len(remainder) - (len(remainder) % _SAMPLE_WIDTH)
                    yield TTSAudioRawFrame(
                        remainder[:usable], self.sample_rate, 1, context_id=context_id
                    )
        except Exception as e:
            logger.error(f"{self} TTS request failed: {e}")
            yield ErrorFrame(error=f"TTS request failed: {e}")

    async def close(self) -> None:
        """Release the underlying httpx client."""
        await self._http_client.aclose()
