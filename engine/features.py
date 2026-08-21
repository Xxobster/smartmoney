"""Feature computation SEPARATELY per database with lagged multi-timeframe alignment.

Higher-timeframe (HTF) features use only completed, correctly lagged candles.
Close-based signals are known only after the candle closes.
"""
from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

from engine.data_loader import load_ohlcv, research_db
from smc.confluence import ConfluenceConfig, build_feature_frame, score_confluence


TF_MS = {
    "1m": 60_000,
    "5m": 300_000,
    "15m": 900_000,
    "1h": 3_600_000,
    "4h": 14_400_000,
    "1d": 86_400_000,
}


def lag_htf_to_ltf(
    ltf: pd.DataFrame,
    htf_feat: pd.DataFrame,
    htf: str,
) -> pd.DataFrame:
    """Align HTF features onto LTF bars using only completed HTF candles.

    A HTF candle that opens at T is complete at T + tf_ms, so LTF bars with
    ts_ms >= T + tf_ms may use that candle's features. Implemented via merge_asof
    on (htf_ts + tf_ms).
    """
    step = TF_MS[htf]
    right = htf_feat.copy()
    right["available_ms"] = right["ts_ms"] + step
    cols = [c for c in right.columns if c not in ("source", "symbol", "timeframe", "open", "high", "low", "close", "volume", "price_type", "is_complete")]
    use = right[["available_ms"] + [c for c in cols if c != "ts_ms" and c != "available_ms"]].copy()
    # Prefix HTF columns
    rename = {c: f"htf_{c}" for c in use.columns if c != "available_ms"}
    use = use.rename(columns=rename)
    left = ltf[["ts_ms"]].copy()
    merged = pd.merge_asof(
        left.sort_values("ts_ms"),
        use.sort_values("available_ms"),
        left_on="ts_ms",
        right_on="available_ms",
        direction="backward",
    )
    return merged.drop(columns=["available_ms"], errors="ignore")


def compute_mtf_features(
    db_path: Path,
    symbol: str,
    cfg: ConfluenceConfig,
    bias_tf: str = "4h",
    structure_tf: str = "1h",
    execution_tf: str = "15m",
    start_ms: Optional[int] = None,
    end_ms: Optional[int] = None,
) -> pd.DataFrame:
    """Compute features on one physical DB only (research XOR lockbox)."""
    exec_df = load_ohlcv(db_path, symbol, execution_tf, start_ms=start_ms, end_ms=end_ms)
    if exec_df.empty:
        return exec_df
    bias_df = load_ohlcv(db_path, symbol, bias_tf, start_ms=start_ms, end_ms=end_ms)
    struct_df = load_ohlcv(db_path, symbol, structure_tf, start_ms=start_ms, end_ms=end_ms)

    exec_feat = build_feature_frame(exec_df, cfg)
    signals = score_confluence(exec_feat, cfg)

    out = pd.concat([exec_feat.reset_index(drop=True), signals.reset_index(drop=True)], axis=1)
    # Drop duplicate columns from concat
    out = out.loc[:, ~out.columns.duplicated()]

    if not bias_df.empty:
        bias_feat = build_feature_frame(bias_df, cfg)
        bias_aligned = lag_htf_to_ltf(exec_df, bias_feat, bias_tf)
        # Override htf bias using HTF structure bias
        if "htf_bias" in bias_aligned.columns:
            out["htf_order_flow"] = bias_aligned["htf_bias"].to_numpy()
        else:
            out["htf_order_flow"] = bias_aligned.get("htf_bias", pd.Series(0, index=out.index))
        # Re-gate signals with HTF
        long_ok = out["htf_order_flow"].fillna(0) >= 0
        short_ok = out["htf_order_flow"].fillna(0) <= 0
        out["long_signal"] = out["long_signal"] & long_ok
        out["short_signal"] = out["short_signal"] & short_ok
    else:
        out["htf_order_flow"] = out.get("bias", 0)

    if not struct_df.empty:
        struct_feat = build_feature_frame(struct_df, cfg)
        struct_aligned = lag_htf_to_ltf(exec_df, struct_feat, structure_tf)
        for col in ("htf_bull_bos", "htf_bear_bos", "htf_bull_choch", "htf_bear_choch"):
            src = col  # already prefixed in lag helper as htf_*
            if src in struct_aligned.columns:
                out[col] = struct_aligned[src].to_numpy()

    out["symbol"] = symbol
    out["execution_timeframe"] = execution_tf
    out["cfg_json"] = str(asdict(cfg))
    return out


def fit_scaler_train_only(
    train_values: np.ndarray,
) -> tuple[float, float]:
    """Fit mean/std on training window only; apply elsewhere with these params."""
    mu = float(np.nanmean(train_values))
    sd = float(np.nanstd(train_values))
    if sd < 1e-12:
        sd = 1.0
    return mu, sd


def apply_scaler(values: np.ndarray, mu: float, sd: float) -> np.ndarray:
    return (values - mu) / sd
