from dataclasses import dataclass


@dataclass(frozen=True)
class InterruptibilityPolicy:
    min_user_speech_ms: int
    preemption_aggressiveness: str


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
