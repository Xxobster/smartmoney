"""Shared path helpers for the smartmoney research repo."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent
CONFIG_DIR = ROOT / "config"
ARTIFACTS = ROOT / "artifacts"
DATASETS = ARTIFACTS / "datasets"
REGISTRY_DB = ARTIFACTS / "research_registry.sqlite"
HF_CACHE = ARTIFACTS / "hf_cache"
RAG_DIR = ARTIFACTS / "rag"
REPORTS = ARTIFACTS / "reports"
INSTRUMENT_SPECS_DIR = ARTIFACTS / "instrument_specs"
DOWNLOAD_CKPT = ARTIFACTS / "download_checkpoints"

DEFAULT_CANDLES_DB = Path(r"D:/projectsdata/candles/market_ohlcv.sqlite")
DEFAULT_SMC_KB = Path(r"C:/projects/wavetheory/smart_money_concepts")


def ensure_artifact_dirs() -> None:
    for p in (
        ARTIFACTS,
        DATASETS,
        HF_CACHE,
        RAG_DIR,
        REPORTS,
        INSTRUMENT_SPECS_DIR,
        DOWNLOAD_CKPT,
    ):
        p.mkdir(parents=True, exist_ok=True)
