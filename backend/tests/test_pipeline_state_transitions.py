from app.services.pipeline import next_state


def test_state_transitions_for_standard_turn():
    assert next_state("Listening", "user_turn_closed") == "Thinking"
    assert next_state("Thinking", "tts_started") == "Speaking"
    assert next_state("Speaking", "tts_completed") == "Listening"


def test_interrupt_collapses_speaking_to_listening():
    assert next_state("Speaking", "interrupt_detected") == "Listening"


def test_invalid_transition_raises():
    import pytest
    with pytest.raises(KeyError):
        next_state("Listening", "tts_started")  # not a valid transition
