from __future__ import annotations

import json
from pathlib import Path
from typing import Callable, List, Sequence

import numpy as np

from .config import RAGConfig
from .embeddings import BaseEmbedder
from .index import VectorIndex, save_metadata, load_metadata

GeneratorFn = Callable[[str, List[dict], str], str]
# signature: (question, context_snippets, prompt_text) -> answer


def _load_snippets(path: Path) -> List[dict]:
    data = []
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                data.append(json.loads(line))
            except json.JSONDecodeError:  # pragma: no cover
                continue
    return data


def _format_prompt(question: str, snippets: Sequence[dict], max_chars: int = 3000) -> str:
    pieces = []
    total = 0
    for s in snippets:
        t = s.get("text", "")
        chunk = f"[SNIPPET]\n{t}\n"
        if total + len(chunk) > max_chars:
            break
        pieces.append(chunk)
        total += len(chunk)
    context_block = "\n".join(pieces)
    return (
        "You are an assistant answering questions about pesticide exposure and metabolites. "
        "Using ONLY the provided snippets, answer the question concisely. If unsure, say you are unsure.\n\n"
        f"{context_block}\nQuestion: {question}\nAnswer:"
    )


class RAGPipeline:
    def __init__(self, config: RAGConfig, embedder: BaseEmbedder):
        self.config = config
        self.embedder = embedder
        self._snippets: List[dict] = []
        self._index: VectorIndex | None = None
        self._texts: List[str] = []
        self._meta: List[dict] = []

    # --- Build / load ---
    def load_snippets(self) -> None:
        self._snippets = _load_snippets(self.config.snippets_path)
        self._texts = [s.get("text", "") for s in self._snippets]
        self._meta = [s for s in self._snippets]

    def build_or_load_embeddings(self) -> None:
        root = self.config.embeddings_path
        if self.config.cache and (root / "embeddings.npy").exists():
            self._index = VectorIndex.load(root)
            self._texts, self._meta = load_metadata(root)
            return
        # build
        vecs = self.embedder.encode(self._texts)
        self._index = VectorIndex(vectors=vecs)
        self._index.save(root)
        save_metadata(self._texts, self._meta, root)

    # --- Retrieval ---
    def retrieve(self, question: str, top_k: int = 5) -> List[dict]:
        q_vec = self.embedder.encode([question])[0]
        assert self._index is not None, "Index not built"
        hits = self._index.query(q_vec, top_k=top_k)
        return [self._meta[i] for i, _ in hits]

    # --- Generation ---
    def generate(self, question: str, generator: GeneratorFn, top_k: int = 5) -> dict:
        snippets = self.retrieve(question, top_k=top_k)
        prompt = _format_prompt(question, snippets)
        answer = generator(question, snippets, prompt)
        return {"question": question, "answer": answer, "snippets": snippets, "prompt": prompt}

    # Convenience orchestrator
    def prepare(self) -> None:
        if not self._snippets:
            self.load_snippets()
        self.build_or_load_embeddings()
