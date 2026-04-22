from __future__ import annotations

import json
import logging
from collections.abc import Callable, Sequence
from pathlib import Path

from ..logging_config import log_with_fallback
from ..pesticide_context import (
    load_analyte_reference,
    load_evidence_enrichment,
    merge_reference_with_enrichment,
)
from .config import RAGConfig
from .embeddings import BaseEmbedder
from .index import VectorIndex, load_metadata, save_metadata

logger = logging.getLogger(__name__)

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
        evidence_summary = str(s.get("sciclaw_evidence_summary", "")).strip()
        if evidence_summary:
            chunk += f"[EVIDENCE_SUMMARY]\n{evidence_summary}\n"
        endpoints = s.get("key_health_endpoints") or []
        if endpoints:
            chunk += f"[KEY_HEALTH_ENDPOINTS]\n{', '.join(str(e) for e in endpoints)}\n"
        parents = s.get("sciclaw_parent_pesticide_candidates") or []
        if parents:
            chunk += f"[PARENT_CANDIDATES]\n{', '.join(str(p) for p in parents)}\n"
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
        log_with_fallback(logger, logging.INFO, f"Loading snippets from {self.config.snippets_path}")
        self._snippets = _load_snippets(self.config.snippets_path)
        self._attach_evidence_enrichment(self._snippets)
        self._texts = [self._compose_retrieval_text(s) for s in self._snippets]
        self._meta = [s for s in self._snippets]
        log_with_fallback(logger, logging.INFO, f"Loaded {len(self._snippets)} snippets")

    def _compose_retrieval_text(self, snippet: dict) -> str:
        """Compose retrieval text including optional enrichment evidence fields."""
        text = str(snippet.get("text", ""))
        parts = [text]
        summary = str(snippet.get("sciclaw_evidence_summary", "")).strip()
        if summary:
            parts.append(summary)
        endpoints = snippet.get("key_health_endpoints") or []
        if endpoints:
            parts.append(" ".join(str(e) for e in endpoints))
        return " \n".join(p for p in parts if p)

    def _attach_evidence_enrichment(self, snippets: list[dict]) -> None:
        """Attach SciClaw enrichment fields to snippets by CAS RN when available."""
        try:
            enrichment_by_cas = load_evidence_enrichment()
            if not enrichment_by_cas:
                return
            merged_reference = merge_reference_with_enrichment(load_analyte_reference(), enrichment_by_cas)
            by_cas: dict[str, dict] = {
                str(r.get("cas_rn", "")).strip(): r
                for r in merged_reference
                if r.get("evidence_enrichment") and r.get("cas_rn")
            }
            for snippet in snippets:
                cas_rn = str(snippet.get("cas_rn", "")).strip()
                if not cas_rn:
                    continue
                enriched = by_cas.get(cas_rn)
                if not enriched:
                    continue
                snippet["evidence_enrichment"] = enriched.get("evidence_enrichment")
                snippet["sciclaw_synonyms"] = enriched.get("sciclaw_synonyms", [])
                snippet["sciclaw_parent_pesticide_candidates"] = enriched.get("sciclaw_parent_pesticide_candidates", [])
                snippet["sciclaw_evidence_summary"] = enriched.get("sciclaw_evidence_summary", "")
                evidence = snippet.get("evidence_enrichment") or {}
                snippet["key_health_endpoints"] = evidence.get("key_health_endpoints", [])
        except Exception as exc:  # noqa: BLE001
            log_with_fallback(logger, logging.WARNING, f"Failed to attach evidence enrichment: {exc}")

    def build_or_load_embeddings(self) -> None:
        """Create embeddings index or load cached artifacts if available."""
        root = self.config.embeddings_path
        if self.config.cache and (root / "embeddings.npy").exists():
            log_with_fallback(logger, logging.INFO, f"Loading cached embeddings/index from {root}")
            self._index = VectorIndex.load(root)
            self._texts, self._meta = load_metadata(root)
            return
        # build
        log_with_fallback(logger, logging.INFO, f"Building embeddings/index for {len(self._texts)} texts")
        vecs = self.embedder.encode(self._texts)
        self._index = VectorIndex(vectors=vecs)
        self._index.save(root)
        save_metadata(self._texts, self._meta, root)
        log_with_fallback(logger, logging.INFO, f"Saved embeddings/index artifacts under {root}")

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
        logger.debug("Retrieved %s snippets for question", len(hits))
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
        log_with_fallback(logger, logging.INFO, f"Generating answer with top_k={top_k} and {len(snippets)} snippets")
        answer = generator(question, snippets, prompt)
        return {"question": question, "answer": answer, "snippets": snippets, "prompt": prompt}

    # Convenience orchestrator
    def prepare(self) -> None:
        """End-to-end pipeline initialization (load snippets + embeddings)."""
        log_with_fallback(logger, logging.INFO, "Preparing RAG pipeline")
        if not self._snippets:
            self.load_snippets()
        self.build_or_load_embeddings()
        log_with_fallback(logger, logging.INFO, "RAG pipeline ready")
