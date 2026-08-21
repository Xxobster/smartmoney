# Strategy: The Secret Mindset — Heikin Ashi rising/falling wedge + EMA50

| Field | Value |
|-------|--------|
| **Source** | [Heiken Ashi & 50-EMA](https://www.youtube.com/watch?v=7J2djQ9C-dE) (`7J2djQ9C-dE`) |
| **Transcript** | Captions via `yt-dlp --skip-download` → `reports/secret_mindset/transcript_7J2djQ9C-dE.txt` (full media download still failing) |
| **Readiness** | `LIVE_STOP / RESEARCH_ONLY` |
| **Evidence class** | `RESEARCH_PROXY` |

## H0 (executable)

Video core (shorts): rising wedge on Heikin Ashi (HA) chart → break below support **and** HA close below Exponential Moving Average (EMA) 50 → short. Stop at wedge high. Target ≈ widest wedge distance (also Reward:Risk ≥ 2).

H0 adds the **mirror** falling-wedge long (same geometry inverted) so both sides are tested on crypto.

- Build causal HA Open-High-Low-Close from regular bars  
- EMA(50) on HA close  
- Window **W=30** HA bars: rolling least-squares slopes on HA highs and HA lows  
  - Rising wedge: both slopes > 0 and low-slope > high-slope (converging) and end width < start width  
  - Falling wedge: both slopes < 0 and high-slope more negative than low-slope (converging) and end width < start width  
- Support/resistance at window end from the fitted lines  
- **Short:** first close below rising-wedge support with HA close < EMA50  
- **Long:** first close above falling-wedge resistance with HA close > EMA50  
- Stop: wedge extreme (window HA high / low)  
- Take-Profit: `max(2 × risk, wedge_width)` from entry  

Timeframes: **15m**, **1h**. Symbols: `BTCUSDT`, `ETHUSDT`.  
Execution fills use regular Open-High-Low-Close bars; HA is signal-only.
