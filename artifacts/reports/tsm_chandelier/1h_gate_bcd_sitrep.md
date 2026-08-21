# Sitrep — tsm_chandelier Gate B remainder + Gate C/D

- **Maximum earned readiness:** `LIVE_STOP / SHADOW_READY`
- **Principal blocker:** `None`
- **Engine conformance:** tradesim 1.0.0 @ UNKNOWN_DIRTY | contract perp_bracket_backtest | fixtures 9a037b290c8a | 58/58 identifiers | GREEN
- **Liquidation status (baseline):** MODELLED
- **DSR (n_trials=1 preregistered):** 1.0000 (pass≥0.95)
- **DSR family sensitivity (n_trials=93):** 0.0000
- **Bootstrap pos expectancy:** 1.0000 (pass≥0.9)
- **Moderate 2× slip:** PF=1.4940 pnl=98.01 liq=0
- **Severe 3× slip (report):** PF=1.4276 pnl=87.25
- **Gate D concentration:** True

## Checks

- `dsr_preregistered_n_trials_1`: `True`
- `bootstrap_pos_exp`: `True`
- `moderate_stress_net_pnl_positive`: `True`
- `moderate_stress_pooled_pf`: `True`
- `moderate_stress_no_liquidation`: `True`
- `gate_d_concentration`: `True`
- `engine_conformance_green`: `True`
- `liquidation_not_unknown`: `True`
- `assert_quotable_baseline`: `True`
- `pbo_matrix_available`: `False`

Authorization remains LIVE_STOP until the user explicitly approves live/shadow.
