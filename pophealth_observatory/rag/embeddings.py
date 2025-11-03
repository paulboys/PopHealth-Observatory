from __future__ import annotations

import hashlib
from abc import ABC, abstractmethod

import numpy as np

try:  # optional heavy dependency
    from sentence_transformers import SentenceTransformer  # type: ignore
except Exception:  # pragma: no cover
    SentenceTransformer = None  # type: ignore


class BaseEmbedder(ABC):
    @abstractmethod
    def encode(self, texts: list[str]) -> np.ndarray:  # shape: (n, d)
        """Encode a list of texts into a 2D float32 numpy array.

        Parameters
        ----------
        texts : list[str]
            Raw input sentences/documents.

        Returns
        -------
        numpy.ndarray
            Matrix of shape (n, d) where d == ``self.dimension``.
        """
        raise NotImplementedError

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Embedding dimensionality (vector length)."""
        raise NotImplementedError


class DummyEmbedder(BaseEmbedder):
    """Deterministic small embedding for tests (hash -> vector)."""

    def __init__(self, dim: int = 16):
        self._dim = dim

    @property
    def dimension(self) -> int:  # pragma: no cover - trivial
        return self._dim

    def encode(self, texts: list[str]) -> np.ndarray:
        vecs = []
        for t in texts:
            h = hashlib.sha256(t.encode("utf-8")).digest()
            # repeat/truncate to dim
            needed = self._dim
            raw = (h * ((needed // len(h)) + 1))[:needed]
            arr = np.frombuffer(raw, dtype=np.uint8).astype(np.float32)
            arr = arr / 255.0  # scale
            vecs.append(arr)
        return np.vstack(vecs)


class SentenceTransformerEmbedder(BaseEmbedder):
    """Wrapper around a SentenceTransformer model.

    Parameters
    ----------
    model_name : str, default="sentence-transformers/all-MiniLM-L6-v2"
        HuggingFace sentence-transformers model identifier.

    Raises
    ------
    RuntimeError
        If sentence-transformers is not installed.
    """

    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        if SentenceTransformer is None:  # pragma: no cover
            raise RuntimeError(
                "sentence-transformers not installed. Install extras: pip install pophealth-observatory[rag]"
            )
        self.model_name = model_name
        self._model = SentenceTransformer(model_name)
        # do one dummy to know dimension
        self._dim = int(self._model.get_sentence_embedding_dimension())

    @property
    def dimension(self) -> int:  # pragma: no cover - simple
        return self._dim

    def encode(self, texts: list[str]) -> np.ndarray:
        return np.asarray(self._model.encode(texts, show_progress_bar=False), dtype=np.float32)
