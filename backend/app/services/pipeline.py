# Deterministic state transition table for the voice bot pipeline.
# States: "Listening" | "Thinking" | "Speaking"
# Events: "user_turn_closed" | "tts_started" | "tts_completed" | "interrupt_detected"

_TRANSITIONS: dict[tuple[str, str], str] = {
    ("Listening", "user_turn_closed"): "Thinking",
    ("Thinking", "tts_started"): "Speaking",
    ("Speaking", "tts_completed"): "Listening",
    ("Speaking", "interrupt_detected"): "Listening",
}


def next_state(current: str, event: str) -> str:
    """Return the next bot state given the current state and an event.

    Raises:
        KeyError: If (current, event) is not a defined transition.
            Callers should treat this as a programming error — only valid
            events for the current state should be emitted.
    """
    return _TRANSITIONS[(current, event)]
