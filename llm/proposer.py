"""LLM ensemble proposer: retrieve SMC rules -> emit validated StrategySpec JSON."""
from __future__ import annotations

import json
import re
from typing import List, Optional

import yaml

from llm.model_zoo import LoadedModel, load_ensemble
from llm.rag import RagIndex
from llm.schema import StrategySpec
from paths import CONFIG_DIR, RAG_DIR


def _extract_json(text: str) -> Optional[dict]:
    text = text.strip()
    # fenced
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, flags=re.S)
    if m:
        text = m.group(1)
    else:
        # first {...}
        m = re.search(r"\{.*\}", text, flags=re.S)
        if not m:
            return None
        text = m.group(0)
    # Strip JS-style comments that small models often insert
    text = re.sub(r"//.*?$", "", text, flags=re.M)
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # trailing commas / minor fixes
        try:
            fixed = re.sub(r",\s*}", "}", text)
            fixed = re.sub(r",\s*]", "]", fixed)
            return json.loads(fixed)
        except json.JSONDecodeError:
            return None


def _clamp(v, lo, hi, default):
    try:
        x = type(default)(v)
    except Exception:
        return default
    if isinstance(default, bool):
        return bool(v) if not isinstance(v, (int, float)) or v in (0, 1) else default
    return type(default)(min(max(x, lo), hi))


def sanitize_proposal(data: dict, seed: dict) -> dict:
    """Clamp LLM nonsense into the preregistered StrategySpec bounds."""
    out = dict(seed)
    out.update({k: v for k, v in data.items() if v is not None})
    # enums
    if str(out.get("bias_timeframe", "")).lower() not in {"1d", "4h", "1h"}:
        out["bias_timeframe"] = seed.get("bias_timeframe", "4h")
    else:
        out["bias_timeframe"] = str(out["bias_timeframe"]).lower()
    if str(out.get("structure_timeframe", "")).lower() not in {"4h", "1h", "15m"}:
        out["structure_timeframe"] = seed.get("structure_timeframe", "1h")
    else:
        out["structure_timeframe"] = str(out["structure_timeframe"]).lower()
    if str(out.get("execution_timeframe", "")).lower() not in {"15m", "5m"}:
        out["execution_timeframe"] = seed.get("execution_timeframe", "15m")
    else:
        out["execution_timeframe"] = str(out["execution_timeframe"]).lower()
    if str(out.get("fvg_model", "")).lower() not in {"wick", "body"}:
        out["fvg_model"] = "wick"
    else:
        out["fvg_model"] = str(out["fvg_model"]).lower()

    # numeric clamps matching schema / search_space
    out["swing_left"] = _clamp(out.get("swing_left"), 2, 8, 3)
    if isinstance(data.get("swing_left"), bool):
        out["swing_left"] = 3
    out["swing_right"] = _clamp(out.get("swing_right"), 2, 8, 3)
    if isinstance(data.get("swing_right"), bool):
        out["swing_right"] = 3
    out["min_confluence_count"] = _clamp(out.get("min_confluence_count"), 2, 6, 3)
    out["volume_confirm_lookback"] = _clamp(out.get("volume_confirm_lookback"), 2, 20, 5)
    out["volume_confirm_mult"] = _clamp(out.get("volume_confirm_mult"), 1.0, 3.0, 1.2)
    out["stop_beyond_sweep_atr_mult"] = _clamp(out.get("stop_beyond_sweep_atr_mult"), 0.0, 1.0, 0.1)
    out["target_rr"] = _clamp(out.get("target_rr"), 1.0, 6.0, 3.0)
    out["max_hold_bars"] = _clamp(out.get("max_hold_bars"), 12, 500, 96)
    out["risk_fraction"] = _clamp(out.get("risk_fraction"), 0.001, 0.02, 0.005)
    out["event_lookback"] = int(_clamp(out.get("event_lookback"), 8, 96, 24))
    out["confirm_bars"] = int(_clamp(out.get("confirm_bars"), 0, 5, 0))
    if str(out.get("session_mode", "")).lower() not in {"none", "killzones", "london_ny", "london", "ny"}:
        out["session_mode"] = seed.get("session_mode", "none")
    else:
        out["session_mode"] = str(out["session_mode"]).lower()
    if not isinstance(out.get("name"), str) or not out["name"].strip():
        out["name"] = "SMC_LLM_Proposal"
    out["rationale"] = str(out.get("rationale") or "")[:500]
    out["economic_justification"] = str(out.get("economic_justification") or "")[:500]
    return out


def build_prompt(context_chunks: List[dict], diversity_hint: str = "") -> str:
    # Keep context short so local CPU LLMs do not hang on long prompts
    pieces = []
    for c in context_chunks[:3]:
        text = (c.get("text") or "")[:500]
        pieces.append(f"SOURCE {c.get('source','?')}#{c.get('chunk_id',0)}:\n{text}")
    ctx = "\n\n".join(pieces)
    schema_hint = (
        "Return ONLY a JSON object with keys: name, bias_timeframe, structure_timeframe, "
        "execution_timeframe, swing_left, swing_right, bos_requires_close, fvg_model, "
        "require_liquidity_sweep, require_bos_or_choch, require_fvg, require_order_block, "
        "require_premium_discount, min_confluence_count, volume_confirm_lookback, "
        "volume_confirm_mult, stop_beyond_sweep_atr_mult, target_rr, use_pd_targets, "
        "max_hold_bars, risk_fraction, rationale, economic_justification. "
        "bias_timeframe in [1d,4h,1h]; structure_timeframe in [4h,1h,15m]; "
        "execution_timeframe in [15m,5m]; fvg_model in [wick,body]."
    )
    return (
        "You are a quantitative research hypothesizer for Smart Money Concepts (SMC). "
        "Propose ONE economically justified StrategySpec for nested walk-forward research. "
        "Do NOT claim profitability. Prefer confluence over frequency. Retrace entries only. "
        "Never fight higher-timeframe order flow. Prefer liquidity sweep + BOS/CHOCH + FVG "
        "(+ optional order block) with premium/discount location filter.\n\n"
        f"{schema_hint}\n"
        "Hard numeric ranges: swing_left/right 2-8 ints; min_confluence_count 2-6; "
        "volume_confirm_lookback 2-20; volume_confirm_mult 1.0-3.0; "
        "stop_beyond_sweep_atr_mult 0.0-1.0; target_rr 1.0-6.0; max_hold_bars 12-500; "
        "risk_fraction 0.001-0.02. Do not invent values outside these ranges.\n\n"
        f"Diversity hint: {diversity_hint}\n\n"
        f"Retrieved SMC knowledge:\n{ctx}\n\n"
        "JSON:"
    )


class StrategyProposer:
    def __init__(self, models: Optional[List[LoadedModel]] = None, rag: Optional[RagIndex] = None):
        self.models = models or load_ensemble(max_models=1)
        self.rag = rag or RagIndex()
        if not (RAG_DIR / "docs.pkl").exists():
            try:
                self.rag.build()
            except Exception as exc:
                print(f"RAG build failed ({exc}); proposer will use empty context")
        else:
            self.rag.load()

    def logical_seed(self) -> StrategySpec:
        with open(CONFIG_DIR / "search_space.yaml", encoding="utf-8") as f:
            search = yaml.safe_load(f)
        return StrategySpec.from_logical_seed(search["logical_seed"])

    def propose_one(self, diversity_hint: str = "", model: Optional[LoadedModel] = None) -> StrategySpec:
        model = model or self.models[0]
        chunks = []
        try:
            chunks = self.rag.query(
                "highest confluence liquidity sweep BOS CHOCH fair value gap order block "
                "premium discount retrace entry HTF alignment " + diversity_hint,
                k=6,
            )
        except Exception as exc:
            print(f"RAG query failed: {exc}")
        prompt = build_prompt(chunks, diversity_hint=diversity_hint)
        raw = model.generate(prompt, max_new_tokens=700)
        data = _extract_json(raw)
        seed = self.logical_seed().model_dump()
        if data is None:
            seed["name"] = f"SMC_Fallback_{model.name.split('/')[-1]}"
            seed["rationale"] = f"Parse failed; used logical seed. Raw snippet: {raw[:200]}"
            return StrategySpec(**seed)
        try:
            cleaned = sanitize_proposal(data, seed)
            return StrategySpec(**cleaned)
        except Exception as exc:
            seed["rationale"] = f"Validation failed ({exc}); logical seed used"
            return StrategySpec(**seed)

    def propose_many(self, n: int = 5) -> List[StrategySpec]:
        specs = [self.logical_seed()]
        hints = [
            "strict HQ order block required",
            "5m execution with 1h bias",
            "wick FVG + fib golden pocket emphasis",
            "volume confirm stricter",
            "no order block but min confluence 4",
            "body FVG model",
            "daily bias + 15m execution",
            "deeper discount only longs / premium shorts",
        ]
        i = 0
        while len(specs) < n + 1:
            model = self.models[i % len(self.models)]
            hint = hints[i % len(hints)]
            specs.append(self.propose_one(diversity_hint=hint, model=model))
            i += 1
        # Deduplicate by params hash-ish
        uniq = []
        seen = set()
        for s in specs:
            key = json.dumps(s.to_params_dict(), sort_keys=True, default=str)
            if key in seen:
                continue
            seen.add(key)
            uniq.append(s)
        return uniq
