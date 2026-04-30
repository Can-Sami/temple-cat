from bot import build_system_messages, build_vad_stop_secs


def test_build_system_messages_wraps_prompt():
    msgs = build_system_messages("You are helpful")
    assert len(msgs) == 1
    assert msgs[0]["role"] == "system"
    assert msgs[0]["content"] == "You are helpful"


def test_build_vad_stop_secs_high_interruptibility():
    # High interruptibility (e.g. 90%) means the bot yields to user quickly.
    # Therefore, VAD stop_secs should be very short (close to 0.15s).
    stop_secs = build_vad_stop_secs(90)
    assert stop_secs <= 0.30


def test_build_vad_stop_secs_low_interruptibility():
    # Low interruptibility (e.g. 10%) means the bot holds the floor.
    # Therefore, VAD stop_secs should be longer (close to 0.8s).
    stop_secs = build_vad_stop_secs(10)
    assert stop_secs >= 0.55
