from app.services.interruptibility import build_interruptibility_policy


def test_high_percentage_allows_fast_preemption():
    policy = build_interruptibility_policy(90)
    assert policy.min_user_speech_ms <= 120
    assert policy.preemption_aggressiveness == "high"


def test_low_percentage_requires_longer_user_speech():
    policy = build_interruptibility_policy(10)
    assert policy.min_user_speech_ms >= 280
    assert policy.preemption_aggressiveness == "low"
