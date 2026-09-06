# Trading Project Profile — smartmoney SMC finder

Complete profile for this repository. Methodological rules in
`TRADING_BOT_RESEARCH_STANDARD_V2.md`, `IN_SAMPLE_VS_OOS.md`, and
`FROZEN_DEFAULT_GATES_V2_1.md` cannot be weakened by preferences below.
Installed file hashes: `INSTALLED_STANDARD_HASHES.md`. Pack zip:
`C:\projects\BASE CURSOR\TRADING_BOT_CURSOR_RULES_V2.zip`.

## 1. Project identity

```yaml
project_name: smartmoney_smc_finder
repository_root: D:/projects/smartmoney
project_memory_directory: docs/project_memory
research_core_version: 0.1.0
live_strategy_module: null
backtest_entrypoint: research/run_search.py
walk_forward_entrypoint: research/run_oos.py
live_entrypoint: null
research_database: artifacts/research_registry.sqlite
market_database: D:/projectsdata/candles/market_ohlcv.sqlite
live_database: null
plotting_tool: matplotlib
```

## 2. Target product contract

```yaml
target_venue: binance
product_type: linear_perpetual
symbols: [BTCUSDT, ETHUSDT]
primary_research_symbols: [BTCUSDT, ETHUSDT]
expansion_symbol_queue: [SOLUSDT, BNBUSDT, XRPUSDT, ADAUSDT, DOGEUSDT]
future_market_queue: [EURUSD, XAUUSD]
settlement_currency: USDT
signal_market: binance
execution_market: binance
signal_price_source: last
entry_price_source: next_bar_open
tp_trigger_source: MarkPrice
sl_trigger_source: MarkPrice
liquidation_source: MarkPrice
strategy_timeframes: [1d, 4h, 1h, 15m, 5m]
execution_replay_timeframe: 1m
timezone: UTC
session_definition: 24x7
```

## 3. Account and order contract

```yaml
account_or_subaccount: research_paper
position_mode: one_way
margin_mode: isolated
sizing_mode: fixed_fractional_risk
wallet_allocation_usdt: 10000.0
risk_per_trade: 0.005
max_portfolio_exposure: 1.0
max_concurrent_positions: 1
max_margin_utilization: 0.60
baseline_max_drawdown_budget: 0.20
moderate_stress_max_drawdown_budget: 0.25
max_daily_loss: 0.03
max_weekly_loss: 0.08
max_risk_of_ruin_or_loss_limit_breach: 0.01
leverage_policy: lowest_operational_leverage_meeting_frozen_capital_and_liquidation_constraints
entry_order_type: market
entry_time_in_force: GTC
maker_timeout_ms: null
maker_reprice_policy: null
exit_order_types: [stop_market, take_profit_market]
max_hold_policy: max_hold_bars
one_position_rules: flat_before_new_entry
```

Instrument rules are loaded from `data/instrument_specs.py` with a timestamped
snapshot under `artifacts/instrument_specs/`.

## 4. Costs and execution assumptions

```yaml
fee_source: binance_usdtm_non_vip_baseline
maker_fee: 0.0002
taker_fee: 0.0005
baseline_spread_model: none_separate
baseline_slippage_model: 1_bps_directional
latency_model: next_bar_open
historical_funding_source: binance_public_api
maker_fill_evidence: false
moderate_cost_stress: all_taker_plus_2x_slippage
severe_cost_stress: all_taker_plus_3x_slippage_report_only
```

## 5. Research design and preferences

```yaml
economic_hypothesis: smc_confluence_retrace
candidate_budget: 200
root_random_seed: 20260724
outer_fold_count: 5
outer_scheme: expanding
inner_scheme: expanding
purge_rule: 48_execution_bars
embargo_rule: 24_execution_bars
gate_profile: trading_bot_v2_1_frozen
bootstrap_method_and_block_rule: circular_block_bootstrap_block_5_days
hac_lag_or_bandwidth_rule: newey_west_lag_5
target_sides: [long, short]
side_specific_strategies_allowed: true
win_rate_is_hard_gate: false
```

## 6. Data and secret references

```yaml
primary_market_data_source: D:/projectsdata/candles/market_ohlcv.sqlite
proxy_market_data_sources: [dukascopy, yahoo]
credential_reference: none_for_public_ohlcv_and_funding
download_checkpoint_directory: artifacts/download_checkpoints
smc_knowledge_root: C:/projects/wavetheory/smart_money_concepts
```

## 7. Local and VPS operations

```yaml
research_execution_location: local
vps_role: live_and_shadow_only
vps_host_alias: null
process_supervisor: null
process_names: []
automatic_restart_enabled: false
startup_reconciliation_required: true
singleton_lock_required: true
websocket_primary_stream: true
rest_reconciliation_required: true
```

## 8. Repository-specific reading list

```yaml
required_read_before_changes:
  - docs/project_memory/TRADING_BOT_RESEARCH_STANDARD_V2.md
  - docs/project_memory/FROZEN_DEFAULT_GATES_V2_1.md
  - docs/project_memory/TRADING_PROJECT_PROFILE.md
  - config/search_space.yaml
  - C:/projects/wavetheory/smart_money_concepts/docs/RULES.md
  - C:/projects/wavetheory/smart_money_concepts/docs/LLM_SYNTHESIS.md
```

## 9. Shadow and forward evidence

```yaml
shadow_start_rule: after_SHADOW_READY_freeze
shadow_min_calendar_duration_days: 90
shadow_min_signal_count: 30
shadow_min_fill_observations: 20
shadow_unexplained_action_mismatches_max: 0
shadow_safety_critical_failures_max: 0
micro_live_min_calendar_duration_days: 180
micro_live_min_trade_count: 50
micro_live_preferred_trade_count: 100
micro_live_pf_gate_for_scale: 1.10
scale_schedule: null
```

## 10. Approval record

```yaml
research_authorized: true
shadow_authorized: false
micro_live_authorized: false
deployment_authorized: false
restart_authorized: false
leverage_change_authorized: false
size_increase_authorized: false
approval_scope: local_research_only
approval_timestamp_utc: "2026-07-24T00:00:00Z"
approval_expiry_utc: null
```
