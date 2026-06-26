"""Unit tests for ``app.services.diarization.dominant_speaker``.

Imports only the pure module — must run without pipecat installed.
"""

from __future__ import annotations

from app.services.diarization import dominant_speaker


def _word(text: str, speaker: int | None = None) -> dict:
    word: dict = {"word": text}
    if speaker is not None:
        word["speaker"] = speaker
    return word


def _result(words: list, transcript: str = "hello world") -> dict:
    return {"channel": {"alternatives": [{"transcript": transcript, "words": words}]}}


def test_two_speakers_majority_wins():
    words = [_word("a", 0), _word("b", 1), _word("c", 1), _word("d", 1)]
    speaker, text = dominant_speaker(_result(words, "a b c d"))
    assert speaker == 1
    assert text == "a b c d"


def test_tie_breaks_to_earliest_speaker():
    # Speaker 1 appears first, speaker 0 second; both own two words -> earliest wins.
    words = [_word("a", 1), _word("b", 0), _word("c", 1), _word("d", 0)]
    speaker, _ = dominant_speaker(_result(words))
    assert speaker == 1


def test_single_speaker():
    words = [_word("a", 2), _word("b", 2), _word("c", 2)]
    speaker, _ = dominant_speaker(_result(words))
    assert speaker == 2


def test_missing_speaker_fields_returns_zero_with_text():
    words = [_word("a"), _word("b")]
    speaker, text = dominant_speaker(_result(words, "a b"))
    assert speaker == 0
    assert text == "a b"


def test_empty_and_none_result_returns_zero_empty_text():
    assert dominant_speaker(None) == (0, "")
    assert dominant_speaker({}) == (0, "")
    assert dominant_speaker({"channel": {"alternatives": []}}) == (0, "")


def test_handles_sdk_object_shape():
    class W:
        def __init__(self, speaker: int) -> None:
            self.word = "x"
            self.speaker = speaker

    class Alt:
        def __init__(self, words: list) -> None:
            self.transcript = "x y z"
            self.words = words

    class Ch:
        def __init__(self, alternatives: list) -> None:
            self.alternatives = alternatives

    class Res:
        def __init__(self, channel: "Ch") -> None:
            self.channel = channel

    result = Res(Ch([Alt([W(0), W(0), W(1)])]))
    speaker, text = dominant_speaker(result)
    assert speaker == 0
    assert text == "x y z"


def test_speaker_zero_is_a_valid_winner():
    words = [_word("a", 0), _word("b", 0), _word("c", 1)]
    speaker, _ = dominant_speaker(_result(words))
    assert speaker == 0
