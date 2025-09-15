from pathlib import Path

from pophealth_observatory.rag import DummyEmbedder, RAGConfig, RAGPipeline

# We'll synthesize a temporary snippet file rather than depend on real ingestion.


def _write_snippets(tmp_path: Path) -> Path:
    content = """
{"text": "Dimethylphosphate (DMP) levels decreased in 2022."}
{"text": "3-PBA remained stable across cohorts."}
{"text": "DEP findings were limited."}
{"text": "Unrelated nutritional note."}
""".strip()
    f = tmp_path / "snips.jsonl"
    f.write_text(content, encoding="utf-8")
    return f


def test_rag_pipeline_dummy(tmp_path: Path):
    snip_file = _write_snippets(tmp_path)
    cfg = RAGConfig(
        snippets_path=snip_file,
        embeddings_path=tmp_path / "embeddings_cache",
        model_name="dummy",
    )
    pipe = RAGPipeline(cfg, DummyEmbedder(dim=8))
    pipe.prepare()

    # Simple generator echo
    def gen(q, snippets, prompt):  # noqa: D401
        return f"Q={q}|N={len(snippets)}"

    result = pipe.generate("What about DMP trends?", gen, top_k=2)
    assert result["question"].startswith("What about")
    assert result["answer"].startswith("Q=")
    assert result["snippets"]
    # ensure caching works
    pipe2 = RAGPipeline(cfg, DummyEmbedder(dim=8))
    pipe2.prepare()  # should load from cache without error
    assert pipe2.retrieve("DMP", top_k=1)
