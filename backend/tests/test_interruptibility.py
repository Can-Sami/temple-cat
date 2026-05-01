from app.services.interruptibility import build_interruptibility_policy, build_vad_tuning


def test_high_percentage_allows_fast_preemption():
    policy = build_interruptibility_policy(90)
    assert policy.min_user_speech_ms <= 120
    assert policy.preemption_aggressiveness == "high"


def test_low_percentage_requires_longer_user_speech():
    policy = build_interruptibility_policy(10)
    assert policy.min_user_speech_ms >= 280
    assert policy.preemption_aggressiveness == "low"


def test_vad_tuning_maps_preemption_aggressiveness():
    """High aggressiveness = faster user-speech confirmation (lower start_secs, volume gate)."""
    high = build_vad_tuning(90)
    low = build_vad_tuning(10)
    assert high.start_secs < low.start_secs
    assert high.min_volume < low.min_volume
    assert high.confidence <= low.confidence
    assert high.stop_secs < low.stop_secs


def test_vad_tuning_medium_splits_the_difference():
    mid = build_vad_tuning(50)
    hi = build_vad_tuning(80)
    lo = build_vad_tuning(20)
    assert hi.start_secs <= mid.start_secs <= lo.start_secs
