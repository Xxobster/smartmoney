"""Tests for walk-forward fold construction and registry."""
from __future__ import annotations

from engine.walkforward import build_inner_folds, build_outer_folds, fold_seed
from research.registry import TrialRegistry
from paths import ARTIFACTS


def test_outer_folds_expanding():
    start = 1_600_000_000_000
    end = start + 800 * 86_400_000
    folds = build_outer_folds(start, end, "15m")
    assert len(folds) >= 3
    for f in folds:
        assert f.train_end_ms <= f.test_start_ms
        assert f.test_end_ms > f.test_start_ms


def test_inner_folds():
    start = 1_600_000_000_000
    end = start + 400 * 86_400_000
    folds = build_inner_folds(start, end, "15m")
    assert len(folds) >= 1


def test_fold_seed_deterministic():
    assert fold_seed(20260724, 1, 2) == fold_seed(20260724, 1, 2)
    assert fold_seed(20260724, 1, 2) != fold_seed(20260724, 1, 3)


def test_registry_append_only(tmp_path):
    reg = TrialRegistry(tmp_path / "reg.sqlite")
    i1 = reg.log_trial(root_seed=1, stage="t", params={"a": 1}, status="ok")
    i2 = reg.log_trial(root_seed=1, stage="t", params={"a": 2}, status="ok")
    assert i2 == i1 + 1
    assert reg.count_trials() == 2
    h = reg.freeze_candidate({"a": 2}, "test")
    assert len(h) == 64
    reg.close()
