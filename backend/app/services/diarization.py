"""Pure speaker-diarization helpers (stdlib only; no pipecat import).

Given a Deepgram transcription ``result`` (a dict OR an SDK object), determine
the "dominant" speaker for a turn — the speaker who owns the most words in the
top alternative — and recover the transcript text. Defensive by design: this
module never raises, so the pipeline can rely on it unconditionally.
"""

from __future__ import annotations

from typing import Any


def _get(obj: Any, key: str, default: Any = None) -> Any:
    """Read ``key`` from a mapping, or as an attribute off an SDK object."""
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _first(seq: Any) -> Any:
    """Return the first item of an indexable/iterable sequence, else ``None``."""
    if not seq:
        return None
    try:
        return seq[0]
    except (TypeError, KeyError, IndexError):
        for item in seq:
            return item
    return None


def _top_alternative(result: Any) -> Any:
    """Locate ``channel.alternatives[0]`` defensively across dict/SDK shapes."""
    channel = _get(result, "channel")
    alternatives = _get(channel, "alternatives")
    return _first(alternatives)


def dominant_speaker(result: Any) -> tuple[int, str]:
    """Return ``(speaker_index, transcript_text)`` for a Deepgram result.

    The dominant speaker owns the most words in the top alternative; ties are
    broken in favour of the earliest-appearing speaker. When no speaker/word
    data is present, returns ``(0, <best-effort text>)``. Never raises.
    """
    try:
        alternative = _top_alternative(result)
        text = _get(alternative, "transcript", "") or ""

        counts: dict[int, int] = {}
        order: list[int] = []
        for word in _get(alternative, "words") or []:
            raw_speaker = _get(word, "speaker")
            if raw_speaker is None:
                continue
            try:
                speaker = int(raw_speaker)
            except (TypeError, ValueError):
                continue
            if speaker not in counts:
                counts[speaker] = 0
                order.append(speaker)
            counts[speaker] += 1

        if not counts:
            return 0, text

        # Iterate in first-appearance order; replace only on a strictly larger
        # count, so an exact tie keeps the earliest-appearing speaker.
        best_speaker = order[0]
        for speaker in order[1:]:
            if counts[speaker] > counts[best_speaker]:
                best_speaker = speaker
        return best_speaker, text
    except Exception:
        return 0, ""
