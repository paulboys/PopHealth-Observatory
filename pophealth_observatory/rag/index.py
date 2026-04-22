from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from ..logging_config import log_with_fallback

logger = logging.getLogger(__name__)


@dataclass
class VectorIndex:
    """In-memory cosine similarity index with optional persistence."""

    vectors: np.ndarray  # shape: (n, d)

    def query(self, query_vec: np.ndarray, top_k: int = 5) -> list[tuple[int, float]]:
        # cosine similarity
        a = query_vec / (np.linalg.norm(query_vec) + 1e-9)
        b = self.vectors / (np.linalg.norm(self.vectors, axis=1, keepdims=True) + 1e-9)
        sims = b @ a
        idx = np.argsort(-sims)[:top_k]
        return [(int(i), float(sims[i])) for i in idx]

    def save(self, root: Path) -> None:
        root.mkdir(parents=True, exist_ok=True)
        np.save(root / "embeddings.npy", self.vectors)
        log_with_fallback(logger, logging.INFO, f"Saved vector index to {root / 'embeddings.npy'}")

    @classmethod
    def load(cls, root: Path) -> VectorIndex:  # type: ignore[name-defined]
        arr = np.load(root / "embeddings.npy")
        log_with_fallback(logger, logging.INFO, f"Loaded vector index from {root / 'embeddings.npy'}")
        return cls(vectors=arr)


def save_metadata(texts: list[str], meta: list[dict], root: Path) -> None:
    """Persist raw texts and metadata JSON alongside embeddings.

    Parameters
    ----------
    texts : list[str]
        Original text content list.
    meta : list[dict]
        Corresponding metadata dictionaries.
    root : Path
        Directory root for persistence.
    """
    (root / "metadata.json").write_text(json.dumps({"meta": meta}, ensure_ascii=False, indent=2), encoding="utf-8")
    (root / "texts.json").write_text(json.dumps(texts, ensure_ascii=False, indent=2), encoding="utf-8")


def load_metadata(root: Path) -> tuple[list[str], list[dict]]:
    """Load previously saved texts and metadata.

    Parameters
    ----------
    root : Path
        Directory containing ``texts.json`` and ``metadata.json``.

    Returns
    -------
    tuple[list[str], list[dict]]
        Tuple of (texts, metadata list).
    """
    import json as _json

    texts = _json.loads((root / "texts.json").read_text(encoding="utf-8"))
    meta_wrapped = _json.loads((root / "metadata.json").read_text(encoding="utf-8"))
    return texts, meta_wrapped.get("meta", [])
