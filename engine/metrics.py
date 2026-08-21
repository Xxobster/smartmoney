"""Metrics: daily MTM Sharpe, pooled PF, DSR, PBO helpers, block bootstrap."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Optional, Sequence

import numpy as np
import pandas as pd
from scipy import stats

from engine.backtest import BacktestResult, Trade


@dataclass
class MetricBundle:
    n_trades: int
    net_pnl: float
    expectancy: float
    profit_factor: float
    win_rate: float
    payoff: float
    sharpe_daily_ann: float
    sharpe_raw_daily: float
    hac_sharpe_ann: float
    max_drawdown: float
    fees: float
    funding: float
    liquidations: int
    trades_per_month: float


def trades_to_frame(trades: Sequence[Trade]) -> pd.DataFrame:
    if not trades:
        return pd.DataFrame(
            columns=[
                "symbol",
                "side",
                "entry_ts",
                "exit_ts",
                "pnl",
                "fees",
                "funding",
                "reason",
                "liquidated",
            ]
        )
    return pd.DataFrame(
        [
            {
                "symbol": t.symbol,
                "side": t.side,
                "entry_ts": t.entry_ts,
                "exit_ts": t.exit_ts,
                "pnl": t.pnl,
                "fees": t.fees,
                "funding": t.funding,
                "reason": t.reason,
                "liquidated": t.liquidated,
            }
            for t in trades
        ]
    )


def pooled_profit_factor(pnls: np.ndarray) -> float:
    gains = pnls[pnls > 0].sum()
    losses = np.abs(pnls[pnls < 0].sum())
    if losses == 0:
        return float("inf") if gains > 0 else float("nan")
    return float(gains / losses)


def max_drawdown(equity: np.ndarray) -> float:
    if len(equity) == 0:
        return 0.0
    peak = np.maximum.accumulate(equity)
    dd = (equity - peak) / np.maximum(peak, 1e-12)
    return float(-dd.min())


def daily_mtm_returns(equity_curve: pd.DataFrame) -> pd.Series:
    if equity_curve.empty:
        return pd.Series(dtype=float)
    eq = equity_curve.copy()
    eq["dt"] = pd.to_datetime(eq["ts_ms"], unit="ms", utc=True)
    daily = eq.set_index("dt")["equity"].resample("1D").last().dropna()
    rets = daily.pct_change().dropna()
    return rets


def sharpe_annualized(daily_rets: pd.Series) -> tuple[float, float]:
    if len(daily_rets) < 2:
        return 0.0, 0.0
    mu = float(daily_rets.mean())
    sd = float(daily_rets.std(ddof=1))
    if sd < 1e-12:
        return 0.0, 0.0
    raw = mu / sd
    return raw, raw * np.sqrt(365.0)


def hac_sharpe_annualized(daily_rets: pd.Series, lag: int = 5) -> float:
    """Newey-West HAC adjusted Sharpe, annualized."""
    if len(daily_rets) < lag + 3:
        return 0.0
    x = daily_rets.to_numpy(dtype=float)
    mu = x.mean()
    n = len(x)
    e = x - mu
    gamma0 = np.dot(e, e) / n
    var = gamma0
    for k in range(1, lag + 1):
        w = 1.0 - k / (lag + 1.0)
        gamma = np.dot(e[k:], e[:-k]) / n
        var += 2.0 * w * gamma
    se = np.sqrt(max(var, 1e-18) / n)
    if se < 1e-18:
        return 0.0
    t = mu / se
    # Convert mean/se to annualized Sharpe-like: mu/sd * sqrt(365)
    sd = np.sqrt(max(var, 1e-18))
    return float((mu / sd) * np.sqrt(365.0)) if sd > 0 else 0.0


def deflated_sharpe_ratio(
    observed_sharpe_ann: float,
    n_obs: int,
    n_trials: int,
    skew: float = 0.0,
    kurt: float = 3.0,
) -> float:
    """Bailey & López de Prado Deflated Sharpe Ratio probability.

    Returns P(SR* > max(SR_expected under null of n_trials)).
    Approximation using expected max Sharpe of n_trials.
    """
    if n_obs < 2 or n_trials < 1:
        return 0.0
    # Non-annualized SR for DSR formula: convert ann to daily-equivalent
    sr = observed_sharpe_ann / np.sqrt(365.0)
    # Expected max SR under null (approx)
    euler = 0.5772156649
    em = (1.0 - euler) * stats.norm.ppf(1.0 - 1.0 / n_trials) + euler * stats.norm.ppf(
        1.0 - 1.0 / (n_trials * np.e)
    )
    # Variance of SR
    sr_var = (1.0 - skew * sr + (kurt - 1.0) / 4.0 * sr**2) / max(n_obs - 1, 1)
    if sr_var <= 0:
        return 0.0
    dsr = stats.norm.cdf((sr - em) / np.sqrt(sr_var))
    return float(dsr)


def block_bootstrap_positive_expectancy(
    pnls: np.ndarray,
    n_resamples: int = 10000,
    block: int = 5,
    seed: int = 0,
) -> float:
    """Circular block bootstrap of trade pnl; fraction with mean > 0."""
    if len(pnls) < 2:
        return 0.0
    rng = np.random.default_rng(seed)
    n = len(pnls)
    block = max(1, min(block, n))
    # Precompute starts
    means = np.empty(n_resamples)
    n_blocks = int(np.ceil(n / block))
    for i in range(n_resamples):
        starts = rng.integers(0, n, size=n_blocks)
        sample = np.concatenate([pnls[s : s + block] if s + block <= n else np.concatenate([pnls[s:], pnls[: (s + block) % n]]) for s in starts])[
            :n
        ]
        means[i] = sample.mean()
    return float(np.mean(means > 0))


def compute_metrics(
    result: BacktestResult,
    n_trials_for_dsr: int = 1,
    bootstrap_resamples: int = 1000,
    seed: int = 0,
) -> tuple[MetricBundle, dict]:
    tf = trades_to_frame(result.trades)
    pnls = tf["pnl"].to_numpy(float) if len(tf) else np.array([])
    n = len(pnls)
    net = float(pnls.sum()) if n else 0.0
    exp = float(pnls.mean()) if n else 0.0
    pf = pooled_profit_factor(pnls) if n else float("nan")
    wins = pnls[pnls > 0]
    losses = pnls[pnls < 0]
    wr = float((pnls > 0).mean()) if n else 0.0
    payoff = float(wins.mean() / abs(losses.mean())) if len(wins) and len(losses) else float("nan")

    rets = daily_mtm_returns(result.equity_curve)
    raw, sharpe_ann = sharpe_annualized(rets)
    hac = hac_sharpe_annualized(rets)
    eq = result.equity_curve["equity"].to_numpy(float) if not result.equity_curve.empty else np.array([0.0])
    mdd = max_drawdown(eq)

    # trades/month from span
    if n >= 1 and tf["exit_ts"].notna().any():
        span_days = max((tf["exit_ts"].max() - tf["entry_ts"].min()) / 86_400_000.0, 1.0)
        tpm = n / (span_days / 30.0)
    else:
        tpm = 0.0

    bundle = MetricBundle(
        n_trades=n,
        net_pnl=net,
        expectancy=exp,
        profit_factor=pf,
        win_rate=wr,
        payoff=payoff,
        sharpe_daily_ann=float(sharpe_ann),
        sharpe_raw_daily=float(raw),
        hac_sharpe_ann=float(hac),
        max_drawdown=mdd,
        fees=float(result.fees_paid),
        funding=float(result.funding_pnl),
        liquidations=int(result.liquidations),
        trades_per_month=float(tpm),
    )
    extras = {
        "dsr": deflated_sharpe_ratio(sharpe_ann, max(len(rets), 2), n_trials_for_dsr),
        "bootstrap_pos_exp": block_bootstrap_positive_expectancy(
            pnls, n_resamples=min(bootstrap_resamples, 10000), seed=seed
        )
        if n
        else 0.0,
        "pnl_excluding_best_trade": float(net - (wins.max() if len(wins) else 0.0)),
    }
    return bundle, extras


def probability_of_backtest_overfitting(
    candidate_by_time_returns: np.ndarray,
) -> Optional[float]:
    """PBO from complete aligned candidate-by-time matrix (rows=candidates, cols=time).

    Returns None if matrix insufficient.
    """
    if candidate_by_time_returns is None:
        return None
    mat = np.asarray(candidate_by_time_returns, dtype=float)
    if mat.ndim != 2 or mat.shape[0] < 2 or mat.shape[1] < 4:
        return None
    # Simplified CSCV PBO: split time in half many combinations is expensive;
    # use single mid split as diagnostic (full PBO requires combinatorial CSCV).
    mid = mat.shape[1] // 2
    is_train = mat[:, :mid]
    is_test = mat[:, mid:]
    train_sr = is_train.mean(axis=1) / (is_train.std(axis=1) + 1e-12)
    test_sr = is_test.mean(axis=1) / (is_test.std(axis=1) + 1e-12)
    best = int(np.argmax(train_sr))
    # Rank of best-in-train on test (lower relative performance => overfitting)
    test_rank = stats.rankdata(-test_sr)[best]  # 1 = best
    # PBO proxy: fraction of splits where best-train underperforms median test — here single split
    pbo_proxy = 1.0 if test_sr[best] < np.median(test_sr) else 0.0
    return float(pbo_proxy)
