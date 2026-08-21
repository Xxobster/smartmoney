"""Retrieval-Augmented Generation (RAG) index over SMC knowledge docs."""
from __future__ import annotations

import argparse
import json
import os
import pickle
from pathlib import Path
from typing import List, Sequence

import numpy as np

from paths import DEFAULT_SMC_KB, HF_CACHE, RAG_DIR, ensure_artifact_dirs


def _chunk_text(text: str, chunk_size: int = 800, overlap: int = 100) -> List[str]:
    text = text.strip()
    if not text:
        return []
    chunks = []
    i = 0
    while i < len(text):
        chunks.append(text[i : i + chunk_size])
        i += max(chunk_size - overlap, 1)
    return chunks


def collect_documents(kb_root: Path) -> list[dict]:
    docs = []
    paths = []
    rules = kb_root / "docs" / "RULES.md"
    quick = kb_root / "docs" / "QUICK_CARD.md"
    synth = kb_root / "docs" / "LLM_SYNTHESIS.md"
    chapters = sorted((kb_root / "docs" / "chapters").glob("*.md")) if (kb_root / "docs" / "chapters").exists() else []
    for p in [rules, quick, synth, *chapters]:
        if p and p.exists():
            paths.append(p)
    for p in paths:
        text = p.read_text(encoding="utf-8", errors="ignore")
        for i, ch in enumerate(_chunk_text(text)):
            docs.append({"source": str(p), "chunk_id": i, "text": ch})
    return docs


class RagIndex:
    def __init__(self, index_dir: Path | None = None):
        ensure_artifact_dirs()
        self.index_dir = index_dir or RAG_DIR
        self.index_dir.mkdir(parents=True, exist_ok=True)
        self.docs: list[dict] = []
        self.embeddings: np.ndarray | None = None
        self.model = None
        self.index = None

    def build(self, kb_root: Path | None = None) -> Path:
        kb_root = Path(kb_root or DEFAULT_SMC_KB)
        self.docs = collect_documents(kb_root)
        if not self.docs:
            raise RuntimeError(f"No SMC docs found under {kb_root}")

        try:
            from sentence_transformers import SentenceTransformer
            import faiss
        except Exception as exc:
            # Fallback: bag-of-words TF hash embeddings
            print(f"sentence-transformers/faiss unavailable ({exc}); using hash embedding fallback")
            return self._build_hash_fallback()

        model = SentenceTransformer("BAAI/bge-small-en-v1.5", cache_folder=str(HF_CACHE))
        texts = [d["text"] for d in self.docs]
        emb = model.encode(texts, normalize_embeddings=True, show_progress_bar=True)
        emb = np.asarray(emb, dtype=np.float32)
        index = faiss.IndexFlatIP(emb.shape[1])
        index.add(emb)
        self.model = model
        self.embeddings = emb
        self.index = index

        meta_path = self.index_dir / "docs.pkl"
        emb_path = self.index_dir / "embeddings.npy"
        faiss_path = self.index_dir / "index.faiss"
        with open(meta_path, "wb") as f:
            pickle.dump(self.docs, f)
        np.save(emb_path, emb)
        faiss.write_index(index, str(faiss_path))
        (self.index_dir / "backend.json").write_text(
            json.dumps({"backend": "faiss_bge", "n_docs": len(self.docs)}), encoding="utf-8"
        )
        print(f"RAG index built: {len(self.docs)} chunks -> {self.index_dir}")
        return self.index_dir

    def _build_hash_fallback(self) -> Path:
        dim = 256
        emb = np.zeros((len(self.docs), dim), dtype=np.float32)
        for i, d in enumerate(self.docs):
            for tok in d["text"].lower().split():
                emb[i, hash(tok) % dim] += 1.0
            n = np.linalg.norm(emb[i]) + 1e-9
            emb[i] /= n
        self.embeddings = emb
        with open(self.index_dir / "docs.pkl", "wb") as f:
            pickle.dump(self.docs, f)
        np.save(self.index_dir / "embeddings.npy", emb)
        (self.index_dir / "backend.json").write_text(
            json.dumps({"backend": "hash", "n_docs": len(self.docs)}), encoding="utf-8"
        )
        return self.index_dir

    def load(self) -> None:
        with open(self.index_dir / "docs.pkl", "rb") as f:
            self.docs = pickle.load(f)
        self.embeddings = np.load(self.index_dir / "embeddings.npy")
        backend = json.loads((self.index_dir / "backend.json").read_text(encoding="utf-8"))
        light = os.environ.get("SMARTMONEY_RAG_LIGHT", "1") == "1"
        if backend.get("backend") == "faiss_bge" and not light:
            try:
                import faiss
                from sentence_transformers import SentenceTransformer

                self.index = faiss.read_index(str(self.index_dir / "index.faiss"))
                self.model = SentenceTransformer("BAAI/bge-small-en-v1.5", cache_folder=str(HF_CACHE))
            except Exception as exc:
                print(f"Could not load faiss/BGE backend ({exc}); using numpy/hash search")
                self.index = None
                self.model = None
        else:
            # Light mode avoids reloading sentence-transformers (can AV-crash on some Windows CPU builds)
            self.index = None
            self.model = None
            if light:
                print("RAG light mode: hash/numpy retrieval (set SMARTMONEY_RAG_LIGHT=0 for BGE)")

    def query(self, text: str, k: int = 6) -> List[dict]:
        if self.embeddings is None:
            self.load()
        assert self.embeddings is not None
        if self.model is not None and self.index is not None:
            q = self.model.encode([text], normalize_embeddings=True)
            import numpy as _np

            q = _np.asarray(q, dtype=_np.float32)
            scores, idxs = self.index.search(q, k)
            return [{**self.docs[i], "score": float(s)} for s, i in zip(scores[0], idxs[0]) if i >= 0]
        # hash / numpy cosine
        dim = self.embeddings.shape[1]
        q = np.zeros(dim, dtype=np.float32)
        for tok in text.lower().split():
            q[hash(tok) % dim] += 1.0
        q /= np.linalg.norm(q) + 1e-9
        scores = self.embeddings @ q
        idxs = np.argsort(-scores)[:k]
        return [{**self.docs[i], "score": float(scores[i])} for i in idxs]


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--build", action="store_true")
    p.add_argument("--kb", type=str, default=None)
    p.add_argument("--query", type=str, default=None)
    args = p.parse_args()
    rag = RagIndex()
    if args.build:
        rag.build(Path(args.kb) if args.kb else None)
    if args.query:
        if not (RAG_DIR / "docs.pkl").exists():
            rag.build(Path(args.kb) if args.kb else None)
        else:
            rag.load()
        for hit in rag.query(args.query):
            print(f"[{hit['score']:.3f}] {hit['source']}#{hit['chunk_id']}")
            print(hit["text"][:240].replace("\n", " "))
            print("---")


if __name__ == "__main__":
    main()
