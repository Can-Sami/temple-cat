def round_trip_latency_ms(t0_seconds: float, t1_seconds: float) -> int:
    """Calculate round-trip latency in whole milliseconds.

    Args:
        t0_seconds: Timestamp of user silence (end of user speech), in seconds.
        t1_seconds: Timestamp of first bot audio byte, in seconds.

    Returns:
        Elapsed time rounded to nearest whole millisecond.
    """
    return int(round((t1_seconds - t0_seconds) * 1000))
