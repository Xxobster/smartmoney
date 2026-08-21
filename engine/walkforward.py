"""Nested walk-forward with purge and embargo."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator, List, Optional, Sequence, Tuple

import numpy as np
import yaml

from paths import CONFIG_DIR


@dataclass(frozen=True)
class Fold:
    fold_id: int
    train_start_ms: int
    train_end_ms: int  # exclusive
    test_start_ms: int
    test_end_ms: int  # exclusive
    purge_ms: int
    embargo_ms: int


def _load_search() -> dict:
    with open(CONFIG_DIR / "search_space.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def ms_per_bar(timeframe: str) -> int:
    return {
        "1m": 60_000,
        "5m": 300_000,
        "15m": 900_000,
        "1h": 3_600_000,
        "4h": 14_400_000,
        "1d": 86_400_000,
    }[timeframe]


def build_outer_folds(
    data_start_ms: int,
    data_end_ms: int,
    execution_tf: str = "15m",
    cfg: Optional[dict] = None,
) -> List[Fold]:
    search = cfg or _load_search()
    outer = search["outer_folds"]
    n = int(outer["count"])
    min_train_days = int(outer["min_train_days"])
    test_days = int(outer["test_days"])
    purge_bars = int(outer["purge_bars_execution_tf"])
    embargo_bars = int(outer["embargo_bars_execution_tf"])
    bar = ms_per_bar(execution_tf)
    purge_ms = purge_bars * bar
    embargo_ms = embargo_bars * bar
    day = 86_400_000
    scheme = str(outer.get("scheme", "expanding"))

    folds: List[Fold] = []
    if scheme == "expanding_from_end":
        # Place the N test windows at the end of the research calendar
        total_test = n * test_days * day
        first_test_start = data_end_ms - total_test
        earliest_train_end_needed = data_start_ms + min_train_days * day
        if first_test_start < earliest_train_end_needed:
            # Shrink test_days to fit
            available = max(data_end_ms - earliest_train_end_needed, day)
            test_days = max(int(available / (n * day)), 1)
            first_test_start = data_end_ms - n * test_days * day
        for i in range(n):
            test_start = first_test_start + i * test_days * day
            test_end = min(test_start + test_days * day, data_end_ms)
            train_end = test_start - purge_ms
            train_start = data_start_ms
            if train_end <= train_start or test_end <= test_start:
                continue
            folds.append(
                Fold(
                    fold_id=i,
                    train_start_ms=train_start,
                    train_end_ms=train_end,
                    test_start_ms=test_start,
                    test_end_ms=test_end,
                    purge_ms=purge_ms,
                    embargo_ms=embargo_ms,
                )
            )
        return folds

    # Default: expanding from start (Gen1)
    first_test_start = data_start_ms + min_train_days * day
    total_test = n * test_days * day
    if first_test_start + total_test > data_end_ms:
        available = max(data_end_ms - first_test_start, day)
        test_days = max(int(available / (n * day)), 1)

    for i in range(n):
        test_start = first_test_start + i * test_days * day
        test_end = min(test_start + test_days * day, data_end_ms)
        train_end = test_start - purge_ms
        train_start = data_start_ms
        if train_end <= train_start or test_end <= test_start:
            continue
        folds.append(
            Fold(
                fold_id=i,
                train_start_ms=train_start,
                train_end_ms=train_end,
                test_start_ms=test_start,
                test_end_ms=test_end,
                purge_ms=purge_ms,
                embargo_ms=embargo_ms,
            )
        )
    return folds


def build_inner_folds(
    train_start_ms: int,
    train_end_ms: int,
    execution_tf: str = "15m",
    cfg: Optional[dict] = None,
) -> List[Fold]:
    search = cfg or _load_search()
    inner = search["inner_folds"]
    n = int(inner["count"])
    purge_bars = int(inner["purge_bars_execution_tf"])
    embargo_bars = int(inner["embargo_bars_execution_tf"])
    bar = ms_per_bar(execution_tf)
    purge_ms = purge_bars * bar
    embargo_ms = embargo_bars * bar

    span = train_end_ms - train_start_ms
    if span <= 0 or n < 1:
        return []
    # Expanding inner: split train span into n test slices after 50% warm-up
    warm = train_start_ms + span // 2
    remaining = train_end_ms - warm
    slice_len = max(remaining // n, bar)
    folds: List[Fold] = []
    for i in range(n):
        test_start = warm + i * slice_len
        test_end = min(test_start + slice_len, train_end_ms)
        tr_end = test_start - purge_ms
        if tr_end <= train_start_ms or test_end <= test_start:
            continue
        folds.append(
            Fold(
                fold_id=i,
                train_start_ms=train_start_ms,
                train_end_ms=tr_end,
                test_start_ms=test_start,
                test_end_ms=test_end,
                purge_ms=purge_ms,
                embargo_ms=embargo_ms,
            )
        )
    return folds


def fold_seed(root_seed: int, fold_id: int, trial_id: int = 0) -> int:
    """Deterministic per-fold/trial seed from one recorded root seed."""
    return int((root_seed * 1_000_003 + fold_id * 97 + trial_id * 13) % (2**31 - 1))
