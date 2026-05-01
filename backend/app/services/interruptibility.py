from dataclasses import dataclass


@dataclass(frozen=True)
class InterruptibilityPolicy:
    min_user_speech_ms: int
    preemption_aggressiveness: str


@dataclass(frozen=True)
class VadTuning:
    """Silero / universal-aggregator VAD knobs derived from interruptibility policy.

    ``stop_secs`` maps ``min_user_speech_ms`` (end-of-utterance sensitivity).
    ``start_secs``, ``confidence``, and ``min_volume`` map ``preemption_aggressiveness``:
    higher aggression detects user speech sooner (easier to interrupt the bot).
    """

    stop_secs: float
    start_secs: float
    confidence: float
    min_volume: float


def build_interruptibility_policy(percentage: int) -> InterruptibilityPolicy:
    """Map a 0–100 interruptibility percentage to concrete voice pipeline params.

    - >= 75%: high aggressiveness, bot yields fast (100ms threshold)
    - >= 40%: medium aggressiveness (200ms threshold)
    -  < 40%: low aggressiveness, bot waits longer (300ms threshold)
    """
    if percentage >= 75:
        return InterruptibilityPolicy(min_user_speech_ms=100, preemption_aggressiveness="high")
    if percentage >= 40:
        return InterruptibilityPolicy(min_user_speech_ms=200, preemption_aggressiveness="medium")
    return InterruptibilityPolicy(min_user_speech_ms=300, preemption_aggressiveness="low")


def interruptibility_min_words_threshold(percentage: int) -> tuple[int, bool]:
    """Words required to trigger an interruption while the bot is speaking.

    Maps 100% → 1 word, 0% → ~6 words; ``allow_interruptions`` is False at 0%.
    """
    pct = max(0, min(100, int(percentage)))
    allow_interruptions = pct > 0
    min_words = max(1, round(6 * (1 - pct / 100.0)))
    return min_words, allow_interruptions


def build_vad_tuning(percentage: int) -> VadTuning:
    """Map interruptibility percentage to concrete VAD parameters (dual knob)."""
    policy = build_interruptibility_policy(percentage)
    clamped = max(100, min(300, policy.min_user_speech_ms))
    stop_secs = 0.15 + (clamped - 100) / 200 * 0.65  # 100ms bucket -> 0.15, 300ms -> 0.80

    # Second knob: how quickly user speech is confirmed when barging in (preemption).
    if policy.preemption_aggressiveness == "high":
        start_secs, confidence, min_volume = 0.12, 0.64, 0.52
    elif policy.preemption_aggressiveness == "medium":
        start_secs, confidence, min_volume = 0.20, 0.70, 0.60
    else:
        start_secs, confidence, min_volume = 0.30, 0.76, 0.68

    return VadTuning(
        stop_secs=stop_secs,
        start_secs=start_secs,
        confidence=confidence,
        min_volume=min_volume,
    )
