"""Download and load free open-source LLMs.

Priority on this machine:
1. Ollama (already installed; reliable downloads + inference)
2. Tiny Hugging Face transformers with hard timeouts
3. Heuristic SMC fallback

The previous hang came from loading multi-GB transformers weights in float32 on CPU
with huge RAG prompts and no timeout. That path is now guarded.
"""
from __future__ import annotations

import json
import os
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout
from dataclasses import dataclass
from typing import Callable, List, Optional

import requests

from paths import HF_CACHE, ensure_artifact_dirs

# Small first — CPU-safe. Larger models only if CUDA or user forces.
TRANSFORMERS_CANDIDATES = [
    "Qwen/Qwen2.5-0.5B-Instruct",
    "Qwen/Qwen2.5-1.5B-Instruct",
]

# Prefer small Ollama tags; fall back to whatever is already local.
OLLAMA_PREFERRED = [
    "qwen2.5:1.5b-instruct",
    "qwen2.5:1.5b",
    "qwen2.5:3b-instruct",
    "qwen2.5:3b",
    "qwen2.5:7b-instruct",
    "qwen2.5:14b-instruct",  # already present on this machine
    "qwen2.5vl:7b",
]

LOAD_TIMEOUT_S = int(os.environ.get("SMARTMONEY_LLM_LOAD_TIMEOUT", "180"))
GEN_TIMEOUT_S = int(os.environ.get("SMARTMONEY_LLM_GEN_TIMEOUT", "120"))
MAX_PROMPT_CHARS = int(os.environ.get("SMARTMONEY_LLM_MAX_PROMPT_CHARS", "3500"))
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434")


@dataclass
class LoadedModel:
    name: str
    backend: str  # ollama | transformers | heuristic
    generate: Callable[..., str]


def has_cuda() -> bool:
    try:
        import torch

        return bool(torch.cuda.is_available())
    except Exception:
        return False


def _truncate_prompt(prompt: str, max_chars: int = MAX_PROMPT_CHARS) -> str:
    if len(prompt) <= max_chars:
        return prompt
    # Keep head (instructions) and tail (JSON cue)
    head = max_chars * 2 // 3
    tail = max_chars - head - 32
    return prompt[:head] + "\n\n[...truncated SMC context...]\n\n" + prompt[-tail:]


def _heuristic_generate(prompt: str, max_new_tokens: int = 512) -> str:
    """Offline fallback when no model weights can be downloaded."""
    spec = {
        "name": "SMC_Heuristic_Proposal",
        "bias_timeframe": "4h",
        "structure_timeframe": "1h",
        "execution_timeframe": "15m",
        "swing_left": 3,
        "swing_right": 3,
        "bos_requires_close": True,
        "fvg_model": "wick",
        "require_liquidity_sweep": True,
        "require_bos_or_choch": True,
        "require_fvg": True,
        "require_order_block": "order block" in prompt.lower(),
        "require_premium_discount": True,
        "min_confluence_count": 3,
        "volume_confirm_lookback": 5,
        "volume_confirm_mult": 1.2,
        "stop_beyond_sweep_atr_mult": 0.1,
        "target_rr": 3.0,
        "use_pd_targets": True,
        "max_hold_bars": 96,
        "risk_fraction": 0.005,
        "rationale": "Heuristic fallback: highest-confluence SMC recipe from RULES.md",
        "economic_justification": (
            "Liquidity sweep + BOS/CHOCH + FVG (+ optional OB) in HTF direction, "
            "enter on retrace in discount/premium with volume confirmation."
        ),
    }
    h = sum(ord(c) for c in prompt) % 3
    if h == 1:
        spec["require_order_block"] = True
        spec["min_confluence_count"] = 4
        spec["name"] = "SMC_Heuristic_OB_Strict"
    elif h == 2:
        spec["execution_timeframe"] = "5m"
        spec["target_rr"] = 4.0
        spec["name"] = "SMC_Heuristic_5m_4R"
    return json.dumps(spec)


def ollama_available() -> bool:
    try:
        r = requests.get(f"{OLLAMA_HOST}/api/tags", timeout=3)
        return r.status_code == 200
    except Exception:
        return False


def ollama_list_models() -> List[str]:
    try:
        r = requests.get(f"{OLLAMA_HOST}/api/tags", timeout=5)
        r.raise_for_status()
        return [m["name"] for m in r.json().get("models", [])]
    except Exception as exc:
        print(f"ollama list failed: {exc}")
        return []


def ollama_pull(model: str, timeout_s: int = 600) -> bool:
    """Pull a model via `ollama pull` with a hard timeout."""
    print(f"Pulling Ollama model: {model} (timeout {timeout_s}s)...")
    try:
        proc = subprocess.run(
            ["ollama", "pull", model],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_s,
            check=False,
        )
        if proc.returncode != 0:
            print(f"ollama pull failed: {proc.stderr[-500:]}")
            return False
        print(f"Pulled {model}")
        return True
    except subprocess.TimeoutExpired:
        print(f"ollama pull timed out for {model}")
        return False
    except FileNotFoundError:
        print("ollama executable not found on PATH")
        return False


def _pick_ollama_tag(installed: List[str]) -> Optional[str]:
    installed_set = set(installed)
    # Exact preferred match
    for tag in OLLAMA_PREFERRED:
        if tag in installed_set:
            return tag
    # Prefix match (e.g. qwen2.5:14b-instruct present)
    for tag in OLLAMA_PREFERRED:
        base = tag.split(":")[0]
        for inst in installed:
            if inst == tag or inst.startswith(tag) or (tag in inst):
                return inst
            if inst.startswith(base + ":"):
                # Prefer instruct variants
                if "instruct" in inst or tag in OLLAMA_PREFERRED:
                    return inst
    return installed[0] if installed else None


def load_ollama_model(model: Optional[str] = None, pull_if_missing: bool = True) -> Optional[LoadedModel]:
    if not ollama_available():
        print("Ollama API not reachable at", OLLAMA_HOST)
        return None

    installed = ollama_list_models()
    tag = model or _pick_ollama_tag(installed)

    if tag is None and pull_if_missing:
        # Pull the smallest preferred model
        for candidate in OLLAMA_PREFERRED[:3]:
            if ollama_pull(candidate):
                tag = candidate
                break
        installed = ollama_list_models()
        tag = tag or _pick_ollama_tag(installed)

    if tag is None:
        print("No Ollama models available")
        return None

    # If preferred small model missing but large ones exist, optionally pull small
    if pull_if_missing and tag in ("qwen2.5:14b-instruct", "qwen2.5vl:7b"):
        for small in ("qwen2.5:1.5b-instruct", "qwen2.5:1.5b", "qwen2.5:3b"):
            if small not in installed and ollama_pull(small, timeout_s=900):
                tag = small
                break
            if small in installed:
                tag = small
                break

    def generate(prompt: str, max_new_tokens: int = 400) -> str:
        prompt = _truncate_prompt(prompt)
        payload = {
            "model": tag,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.7,
                "top_p": 0.9,
                "num_predict": max_new_tokens,
            },
        }
        r = requests.post(
            f"{OLLAMA_HOST}/api/generate",
            json=payload,
            timeout=GEN_TIMEOUT_S,
        )
        r.raise_for_status()
        return (r.json().get("response") or "").strip()

    # Smoke-test generate quickly so we fail soft (not hard) if model is busy
    try:
        with ThreadPoolExecutor(max_workers=1) as ex:
            fut = ex.submit(generate, 'Reply with JSON only: {"ok": true}', 32)
            fut.result(timeout=min(GEN_TIMEOUT_S, 90))
    except Exception as exc:
        print(f"Ollama smoke test warning for {tag}: {exc} (continuing anyway)")

    print(f"Loaded Ollama model: {tag}")
    return LoadedModel(name=f"ollama:{tag}", backend="ollama", generate=generate)


def load_transformers_model(model_id: str) -> Optional[LoadedModel]:
    try:
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer
    except Exception as exc:
        print(f"transformers unavailable: {exc}")
        return None

    ensure_artifact_dirs()
    os.environ.setdefault("HF_HOME", str(HF_CACHE))
    os.environ.setdefault("TRANSFORMERS_CACHE", str(HF_CACHE))
    os.environ.setdefault("HF_HUB_DOWNLOAD_TIMEOUT", "60")

    def _load():
        tok = AutoTokenizer.from_pretrained(model_id, cache_dir=str(HF_CACHE))
        model = AutoModelForCausalLM.from_pretrained(
            model_id,
            cache_dir=str(HF_CACHE),
            dtype=torch.float32,
            low_cpu_mem_usage=True,
        )
        model = model.to("cpu")
        model.eval()
        return tok, model

    try:
        with ThreadPoolExecutor(max_workers=1) as ex:
            fut = ex.submit(_load)
            tok, model = fut.result(timeout=LOAD_TIMEOUT_S)
    except FuturesTimeout:
        print(f"Timed out loading transformers model {model_id} after {LOAD_TIMEOUT_S}s")
        return None
    except Exception as exc:
        print(f"Failed to load {model_id}: {exc}")
        return None

    def generate(prompt: str, max_new_tokens: int = 256) -> str:
        prompt = _truncate_prompt(prompt)
        inputs = tok(prompt, return_tensors="pt", truncation=True, max_length=1024)
        with torch.no_grad():
            out = model.generate(
                **inputs,
                max_new_tokens=min(max_new_tokens, 256),
                do_sample=True,
                temperature=0.7,
                top_p=0.9,
                pad_token_id=tok.eos_token_id,
            )
        text = tok.decode(out[0], skip_special_tokens=True)
        if text.startswith(prompt[:200]):
            # Best-effort strip of echoed prompt
            text = text[len(prompt) :] if text.startswith(prompt) else text
        return text.strip()

    return LoadedModel(name=model_id, backend="transformers", generate=generate)


def load_ensemble(max_models: int = 1, allow_heavy: bool | None = None) -> List[LoadedModel]:
    """Load LLM backends. Prefer Ollama; never hang forever.

    SMARTMONEY_LOAD_LLM=1 enables real model load (default now also tries Ollama
    when SMARTMONEY_USE_OLLAMA is not 0). Heuristic remains the last resort.
    """
    if allow_heavy is None:
        allow_heavy = os.environ.get("SMARTMONEY_LOAD_LLM", "0") == "1"

    use_ollama = os.environ.get("SMARTMONEY_USE_OLLAMA", "1") != "0"
    models: List[LoadedModel] = []

    if allow_heavy or use_ollama:
        # 1) Ollama first — avoids HF transformers hang on CPU
        if use_ollama and len(models) < max_models:
            m = load_ollama_model(pull_if_missing=allow_heavy)
            if m:
                models.append(m)

        # 2) Tiny HF transformers ONLY if explicitly allowed and Ollama produced nothing
        if allow_heavy and not models and os.environ.get("SMARTMONEY_ALLOW_TRANSFORMERS", "0") == "1":
            for mid in TRANSFORMERS_CANDIDATES[:1]:
                print(f"Trying transformers fallback: {mid}")
                m = load_transformers_model(mid)
                if m:
                    models.append(m)
                    print(f"Loaded transformers model: {mid}")
                    break

    if not models:
        print(
            "Using heuristic SMC proposer. "
            "To use a real LLM: start Ollama, then "
            "`$env:SMARTMONEY_LOAD_LLM=1; python -m research.run_search`"
        )
        models.append(LoadedModel(name="heuristic", backend="heuristic", generate=_heuristic_generate))
    return models


def prefetch_default_model() -> dict:
    """CLI helper: ensure a small Ollama instruct model is present."""
    ensure_artifact_dirs()
    out = {"ollama_up": ollama_available(), "installed_before": ollama_list_models(), "pulled": None}
    if not out["ollama_up"]:
        out["error"] = f"Ollama not reachable at {OLLAMA_HOST}. Start the Ollama app first."
        return out
    tag = _pick_ollama_tag(out["installed_before"])
    # Prefer pulling a small model for research speed
    for small in ("qwen2.5:1.5b-instruct", "qwen2.5:1.5b"):
        if small in out["installed_before"]:
            out["pulled"] = small
            out["status"] = "already_installed"
            return out
    for small in ("qwen2.5:1.5b-instruct", "qwen2.5:1.5b", "qwen2.5:3b"):
        if ollama_pull(small, timeout_s=900):
            out["pulled"] = small
            out["status"] = "pulled"
            out["installed_after"] = ollama_list_models()
            return out
    # Fall back to whatever is already installed
    out["pulled"] = tag
    out["status"] = "using_existing" if tag else "failed"
    out["installed_after"] = ollama_list_models()
    return out


if __name__ == "__main__":
    info = prefetch_default_model()
    print(json.dumps(info, indent=2))
    if info.get("status") in ("already_installed", "pulled", "using_existing"):
        m = load_ollama_model(pull_if_missing=False)
        if m:
            raw = m.generate(
                'Return ONLY JSON: {"name":"test","bias_timeframe":"4h",'
                '"structure_timeframe":"1h","execution_timeframe":"15m",'
                '"swing_left":3,"swing_right":3,"bos_requires_close":true,'
                '"fvg_model":"wick","require_liquidity_sweep":true,'
                '"require_bos_or_choch":true,"require_fvg":true,'
                '"require_order_block":false,"require_premium_discount":true,'
                '"min_confluence_count":3,"volume_confirm_lookback":5,'
                '"volume_confirm_mult":1.2,"stop_beyond_sweep_atr_mult":0.1,'
                '"target_rr":3.0,"use_pd_targets":true,"max_hold_bars":96,'
                '"risk_fraction":0.005,"rationale":"x","economic_justification":"y"}',
                max_new_tokens=200,
            )
            print("SAMPLE_OUTPUT:", raw[:500])
