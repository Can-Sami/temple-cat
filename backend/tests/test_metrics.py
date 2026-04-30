from app.services.metrics import round_trip_latency_ms


def test_round_trip_latency_from_t0_to_t1():
    assert round_trip_latency_ms(10.0, 10.245) == 245


def test_round_trip_latency_whole_seconds():
    assert round_trip_latency_ms(5.0, 6.0) == 1000


def test_round_trip_latency_sub_millisecond_rounds():
    # 0.0004 seconds = 0.4ms → rounds to 0ms
    assert round_trip_latency_ms(0.0, 0.0004) == 0


def test_round_trip_latency_zero_gap():
    assert round_trip_latency_ms(3.5, 3.5) == 0
