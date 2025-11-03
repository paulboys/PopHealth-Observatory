from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class RAGConfig:
    """Configuration for a lightweight RAG pipeline.

    Attributes
    ----------
    snippets_path: Path to JSONL file of snippets (each line: {text, ...}).
    embeddings_path: Directory to store embedding matrix (.npy) and metadata (.json).
    model_name: Name of sentence-transformer model (only used if SentenceTransformerEmbedder is chosen).
    cache: Whether to reuse existing embedding artifacts if present.
    """

    snippets_path: Path
    embeddings_path: Path
    model_name: str = "sentence-transformers/all-MiniLM-L6-v2"
    cache: bool = True

    def ensure_dirs(self) -> None:
        """Create embeddings directory if missing."""
        self.embeddings_path.mkdir(parents=True, exist_ok=True)
