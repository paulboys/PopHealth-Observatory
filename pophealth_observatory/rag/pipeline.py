from __future__ import annotations

import json
from collections.abc import Callable, Sequence
from pathlib import Path

from .config import RAGConfig
from .embeddings import BaseEmbedder
from .index import VectorIndex, load_metadata, save_metadata

GeneratorFn = Callable[[str, list[dict], str], str]
# signature: (question, context_snippets, prompt_text) -> answer


def _load_snippets(path: Path) -> list[dict]:
    """Load line-oriented JSONL snippets file into memory.

    Parameters
    ----------
    path : Path
        JSONL file path where each line is a snippet dictionary.

    Returns
    -------
    list[dict]
        Parsed snippet dictionaries (malformed lines skipped).
    """
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
    """Assemble retrieval-augmented prompt with length cap.

    Parameters
    ----------
    question : str
        End-user natural language question.
    snippets : Sequence[dict]
        Ordered snippet dictionaries containing a 'text' field.
    max_chars : int, default=3000
        Maximum cumulative character budget for included snippet blocks.

    Returns
    -------
    str
        Final prompt ready for generator model consumption.
    """
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
    """Lightweight Retrieval-Augmented Generation orchestration class.

    Responsibilities:
      - Load JSONL snippets
      - Build or load embedding index
      - Retrieve top-k similar snippets for a question
      - Format prompt and delegate answer generation

    Parameters
    ----------
    config : RAGConfig
        Configuration object with paths & model settings.
    embedder : BaseEmbedder
        Embedding provider instance.
    """

    def __init__(self, config: RAGConfig, embedder: BaseEmbedder):
        self.config = config
        self.embedder = embedder
        self._snippets: list[dict] = []
        self._index: VectorIndex | None = None
        self._texts: list[str] = []
        self._meta: list[dict] = []

    # --- Build / load ---
    def load_snippets(self) -> None:
        """Populate internal snippet, text and meta arrays from disk."""
        self._snippets = _load_snippets(self.config.snippets_path)
        self._texts = [s.get("text", "") for s in self._snippets]
        self._meta = [s for s in self._snippets]

    def build_or_load_embeddings(self) -> None:
        """Create embeddings index or load cached artifacts if available."""
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
    def retrieve(self, question: str, top_k: int = 5) -> list[dict]:
        """Return top-k snippet metadata records most similar to question.

        Parameters
        ----------
        question : str
            User question.
        top_k : int, default=5
            Number of results to return.

        Returns
        -------
        list[dict]
            Subset of snippet metadata dictionaries.
        """
        q_vec = self.embedder.encode([question])[0]
        assert self._index is not None, "Index not built"
        hits = self._index.query(q_vec, top_k=top_k)
        return [self._meta[i] for i, _ in hits]

    # --- Generation ---
    def generate(self, question: str, generator: GeneratorFn, top_k: int = 5) -> dict:
        """Retrieve context, assemble prompt and invoke generator.

        Parameters
        ----------
        question : str
            User question.
        generator : Callable[[str, list[dict], str], str]
            Generation function accepting (question, snippets, prompt) and returning answer.
        top_k : int, default=5
            Retrieval depth.

        Returns
        -------
        dict
            Structured answer package containing question, answer, snippets and prompt.
        """
        snippets = self.retrieve(question, top_k=top_k)
        prompt = _format_prompt(question, snippets)
        answer = generator(question, snippets, prompt)
        return {"question": question, "answer": answer, "snippets": snippets, "prompt": prompt}

    # Convenience orchestrator
    def prepare(self) -> None:
        """End-to-end pipeline initialization (load snippets + embeddings)."""
        if not self._snippets:
            self.load_snippets()
        self.build_or_load_embeddings()
