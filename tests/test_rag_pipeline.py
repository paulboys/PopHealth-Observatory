from __future__ import annotations

from pathlib import Path

import pytest

import pophealth_observatory.rag.pipeline as pipeline_module
from pophealth_observatory.rag import DummyEmbedder, RAGConfig, RAGPipeline
from pophealth_observatory.rag.pipeline import _format_prompt, _load_snippets


def _write_lines(path: Path, lines: list[str]) -> Path:
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def test_load_snippets_skips_malformed_lines(tmp_path: Path) -> None:
    snippet_file = _write_lines(
        tmp_path / "snips.jsonl",
        [
            '{"text": "valid one"}',
            '{"text": "valid two"}',
            "{not-json}",
            '{"text": "valid three"}',
        ],
    )

    loaded = _load_snippets(snippet_file)
    assert len(loaded) == 3
    assert loaded[0]["text"] == "valid one"
    assert loaded[-1]["text"] == "valid three"


def test_format_prompt_respects_max_chars() -> None:
    snippets = [
        {"text": "a" * 120},
        {"text": "b" * 120},
        {"text": "c" * 120},
    ]
    prompt = _format_prompt("Question?", snippets, max_chars=160)

    assert "Question: Question?" in prompt
    assert "[SNIPPET]" in prompt
    # The second and third snippets should be truncated out by char budget.
    assert "b" * 120 not in prompt
    assert "c" * 120 not in prompt


def test_retrieve_requires_prepared_index(tmp_path: Path) -> None:
    snippet_file = _write_lines(tmp_path / "snips.jsonl", ['{"text": "DMP trend text"}'])
    cfg = RAGConfig(snippets_path=snippet_file, embeddings_path=tmp_path / "cache")
    pipe = RAGPipeline(cfg, DummyEmbedder(dim=8))

    with pytest.raises(AssertionError, match="Index not built"):
        pipe.retrieve("DMP")


def test_prepare_creates_cache_artifacts(tmp_path: Path) -> None:
    snippet_file = _write_lines(
        tmp_path / "snips.jsonl",
        [
            '{"text": "Dimethylphosphate (DMP) levels decreased in 2022."}',
            '{"text": "3-PBA remained stable across cohorts."}',
            '{"text": "DEP findings were limited."}',
        ],
    )
    cfg = RAGConfig(snippets_path=snippet_file, embeddings_path=tmp_path / "embeddings_cache", model_name="dummy")
    pipe = RAGPipeline(cfg, DummyEmbedder(dim=8))
    pipe.prepare()

    assert (cfg.embeddings_path / "embeddings.npy").exists()
    assert (cfg.embeddings_path / "metadata.json").exists()
    assert (cfg.embeddings_path / "texts.json").exists()


def test_prepare_loads_existing_cache(tmp_path: Path) -> None:
    snippet_file = _write_lines(
        tmp_path / "snips.jsonl",
        [
            '{"text": "DMP exposure changed over time."}',
            '{"text": "DEP findings were limited."}',
        ],
    )
    cfg = RAGConfig(snippets_path=snippet_file, embeddings_path=tmp_path / "embeddings_cache", model_name="dummy")

    first = RAGPipeline(cfg, DummyEmbedder(dim=8))
    first.prepare()

    second = RAGPipeline(cfg, DummyEmbedder(dim=8))
    second.prepare()

    assert second.retrieve("DMP", top_k=1)


def test_generate_returns_expected_payload(tmp_path: Path) -> None:
    snippet_file = _write_lines(
        tmp_path / "snips.jsonl",
        [
            '{"text": "Dimethylphosphate (DMP) levels decreased in 2022."}',
            '{"text": "3-PBA remained stable across cohorts."}',
            '{"text": "DEP findings were limited."}',
            '{"text": "Unrelated nutritional note."}',
        ],
    )
    cfg = RAGConfig(snippets_path=snippet_file, embeddings_path=tmp_path / "embeddings_cache", model_name="dummy")
    pipe = RAGPipeline(cfg, DummyEmbedder(dim=8))
    pipe.prepare()

    def gen(question: str, snippets: list[dict], prompt: str) -> str:
        return f"Q={question}|N={len(snippets)}|P={len(prompt)}"

    result = pipe.generate("What about DMP trends?", gen, top_k=2)

    assert result["question"] == "What about DMP trends?"
    assert result["answer"].startswith("Q=What about DMP trends?|N=2")
    assert len(result["snippets"]) == 2
    assert "Question: What about DMP trends?" in result["prompt"]


def test_retrieve_top_k_larger_than_corpus(tmp_path: Path) -> None:
    snippet_file = _write_lines(
        tmp_path / "snips.jsonl",
        [
            '{"text": "snippet one"}',
            '{"text": "snippet two"}',
            '{"text": "snippet three"}',
        ],
    )
    cfg = RAGConfig(snippets_path=snippet_file, embeddings_path=tmp_path / "embeddings_cache")
    pipe = RAGPipeline(cfg, DummyEmbedder(dim=8))
    pipe.prepare()

    hits = pipe.retrieve("snippet", top_k=20)
    assert len(hits) == 3


def test_retrieve_zero_top_k_returns_empty(tmp_path: Path) -> None:
    snippet_file = _write_lines(
        tmp_path / "snips.jsonl",
        [
            '{"text": "snippet one"}',
            '{"text": "snippet two"}',
        ],
    )
    cfg = RAGConfig(snippets_path=snippet_file, embeddings_path=tmp_path / "embeddings_cache")
    pipe = RAGPipeline(cfg, DummyEmbedder(dim=8))
    pipe.prepare()

    assert pipe.retrieve("snippet", top_k=0) == []


def test_generate_surfaces_enrichment_in_prompt(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    snippet_file = _write_lines(
        tmp_path / "snips.jsonl",
        [
            '{"cas_rn": "814-24-8", "analyte_name": "DMP", "text": "DMP findings in cohort samples."}',
        ],
    )
    cfg = RAGConfig(snippets_path=snippet_file, embeddings_path=tmp_path / "embeddings_cache", model_name="dummy")

    monkeypatch.setattr(pipeline_module, "load_evidence_enrichment", lambda: {"814-24-8": object()})
    monkeypatch.setattr(
        pipeline_module,
        "merge_reference_with_enrichment",
        lambda analytes, enrichment_by_cas: [
            {
                "cas_rn": "814-24-8",
                "evidence_enrichment": {
                    "key_health_endpoints": ["neurodevelopment"],
                },
                "sciclaw_evidence_summary": "DMP associated with OP exposure biomarker evidence.",
                "sciclaw_parent_pesticide_candidates": ["Organophosphates"],
                "sciclaw_synonyms": ["Dimethylphosphate"],
            }
        ],
    )

    pipe = RAGPipeline(cfg, DummyEmbedder(dim=8))
    pipe.prepare()

    def gen(question: str, snippets: list[dict], prompt: str) -> str:
        return prompt

    out = pipe.generate("What evidence exists for DMP?", gen, top_k=1)

    assert "[EVIDENCE_SUMMARY]" in out["prompt"]
    assert "OP exposure biomarker evidence" in out["prompt"]
    assert "[KEY_HEALTH_ENDPOINTS]" in out["prompt"]
    assert "neurodevelopment" in out["prompt"]
    assert out["snippets"][0]["sciclaw_evidence_summary"].startswith("DMP associated")
