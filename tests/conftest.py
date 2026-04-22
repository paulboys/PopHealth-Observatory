"""Shared pytest fixtures for test modules."""

from __future__ import annotations

from pathlib import Path

import pytest

from pophealth_observatory.rag import DummyEmbedder, RAGConfig


@pytest.fixture
def sample_snippets_jsonl(tmp_path: Path) -> Path:
    """Create a small JSONL snippet fixture for RAG-related tests."""
    content = "\n".join(
        [
            '{"text": "Dimethylphosphate (DMP) levels decreased in 2022."}',
            '{"text": "3-PBA remained stable across cohorts."}',
            '{"text": "DEP findings were limited."}',
            '{"text": "Unrelated nutritional note."}',
        ]
    )
    path = tmp_path / "snippets.jsonl"
    path.write_text(content, encoding="utf-8")
    return path


@pytest.fixture
def rag_config(tmp_path: Path, sample_snippets_jsonl: Path) -> RAGConfig:
    """Standard RAG config fixture with temporary cache directory."""
    return RAGConfig(
        snippets_path=sample_snippets_jsonl,
        embeddings_path=tmp_path / "embeddings_cache",
        model_name="dummy",
    )


@pytest.fixture
def dummy_embedder() -> DummyEmbedder:
    """Deterministic lightweight embedder fixture for tests."""
    return DummyEmbedder(dim=8)
