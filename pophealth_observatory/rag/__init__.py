"""RAG scaffolding (LLM-agnostic).

Public entrypoints:
- RAGConfig
- RAGPipeline
- BaseEmbedder, DummyEmbedder, SentenceTransformerEmbedder (optional)
"""

from .config import RAGConfig
from .embeddings import BaseEmbedder, DummyEmbedder, SentenceTransformerEmbedder  # noqa: F401
from .pipeline import RAGPipeline  # noqa: F401

__all__ = [
    "RAGConfig",
    "RAGPipeline",
    "BaseEmbedder",
    "DummyEmbedder",
    "SentenceTransformerEmbedder",
]
