"""Hour-close aware sleep schedule for 1h live bots."""

from __future__ import annotations

HOUR_MS = 3_600_000


def sleep_sec_for_tf(
    now_ms: int,
    *,
    step_ms: int,
    last_closed_ts_ms: int | None,
    dense_poll_sec: float = 5.0,
    idle_poll_sec: float = 60.0,
    pre_close_sec: float = 45.0,
    post_close_sec: float = 180.0,
) -> float:
    if step_ms <= 0:
        return float(idle_poll_sec)
    bar_open = (int(now_ms) // step_ms) * step_ms
    next_close = bar_open + step_ms
    ms_to_close = next_close - int(now_ms)
    ms_since_close = int(now_ms) - bar_open
    expected = bar_open - step_ms  # last fully closed open

    missing = last_closed_ts_ms is None or int(last_closed_ts_ms) < expected
    in_pre = 0 <= ms_to_close <= int(pre_close_sec * 1000)
    in_post = 0 <= ms_since_close <= int(post_close_sec * 1000)

    if in_pre or (in_post and missing) or (missing and ms_since_close <= int(post_close_sec * 1000)):
        return float(dense_poll_sec)
    if missing:
        return min(float(idle_poll_sec), 15.0)
    wake_before = max(1.0, ms_to_close / 1000.0 - pre_close_sec)
    return float(min(idle_poll_sec, wake_before))
