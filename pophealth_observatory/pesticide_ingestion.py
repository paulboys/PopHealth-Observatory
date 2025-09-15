"""Pesticide narrative ingestion scaffolding.

Extracts simple context snippets referencing known pesticide analytes from
plain-text source documents (e.g., PDP summaries). Future work will extend
to PDF/HTML parsing and semantic embedding.
"""
from __future__ import annotations

import json
import re
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from .pesticide_context import PesticideAnalyte, load_analyte_reference

RAW_DIR = Path("data/raw/pesticides")
PROCESSED_DIR = Path("data/processed/pesticides")


SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+\n?|\n{2,}")


@dataclass
class Snippet:
    cas_rn: str
    analyte_name: str
    parent_pesticide: str
    source_id: str
    source_path: str
    position: int
    sentence_window: list[str]

    def to_dict(self) -> dict[str, object]:
        return {
            "cas_rn": self.cas_rn,
            "analyte_name": self.analyte_name,
            "parent_pesticide": self.parent_pesticide,
            "source_id": self.source_id,
            "source_path": self.source_path,
            "position": self.position,
            "text": " ".join(self.sentence_window).strip(),
        }


def ensure_dirs() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def segment_sentences(text: str) -> list[str]:
    # Basic split; retains sentences without aggressive abbreviation logic.
    raw = [s.strip() for s in SENTENCE_SPLIT_RE.split(text) if s.strip()]
    return raw


def _index_analyte_patterns(analytes: list[PesticideAnalyte]) -> list[tuple[PesticideAnalyte, re.Pattern[str]]]:
    patterns: list[tuple[PesticideAnalyte, re.Pattern[str]]] = []
    for a in analytes:
        # Build pattern capturing analyte or parent pesticide (word-ish boundaries)
        tokens = {a.analyte_name, a.parent_pesticide}
        tokens = {t for t in tokens if t}
        if not tokens:
            continue
        escaped = [re.escape(t) for t in tokens]
        pat = re.compile(r"(?i)\b(" + "|".join(escaped) + r")\b")
        patterns.append((a, pat))
    return patterns


def generate_snippets(sentences: list[str], window: int = 1, source_id: str = "sample") -> Iterable[Snippet]:
    analytes = load_analyte_reference()
    patterns = _index_analyte_patterns(analytes)
    for idx, sent in enumerate(sentences):
        for analyte, pat in patterns:
            if pat.search(sent):
                start = max(0, idx - window)
                end = min(len(sentences), idx + window + 1)
                yield Snippet(
                    cas_rn=analyte.cas_rn,
                    analyte_name=analyte.analyte_name,
                    parent_pesticide=analyte.parent_pesticide,
                    source_id=source_id,
                    source_path="",
                    position=idx,
                    sentence_window=sentences[start:end],
                )


def write_snippets(snippets: Iterable[Snippet], dest: Path) -> int:
    count = 0
    with dest.open("w", encoding="utf-8") as fh:
        for snip in snippets:
            fh.write(json.dumps(snip.to_dict(), ensure_ascii=False) + "\n")
            count += 1
    return count


def ingest_text_file(path: Path, source_id: str = "sample", window: int = 1) -> Path:
    ensure_dirs()
    text = read_text(path)
    sentences = segment_sentences(text)
    snippets = list(generate_snippets(sentences, window=window, source_id=source_id))
    out_path = PROCESSED_DIR / f"snippets_{source_id}.jsonl"
    write_snippets(snippets, out_path)
    return out_path


if __name__ == "__main__":  # manual dev test
    sample = RAW_DIR / "sample_pdp_excerpt.txt"
    result = ingest_text_file(sample, source_id="pdp_sample")
    print("Wrote snippets ->", result)