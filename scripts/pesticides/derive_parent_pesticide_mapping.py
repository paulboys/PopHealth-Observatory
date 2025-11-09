#!/usr/bin/env python
"""
Derive authoritative analyte → parent pesticide mappings strictly from NHANES lab documentation.

Workflow:
1. Load nhanes_pesticide_variables_discovered.csv
2. For each unique (variable_name, earliest data_file_name, earliest cycle):
     - Fetch NHANES lab codebook HTML
     - Parse variable description row + narrative sections
     - Apply regex extraction of parent relationship phrases
3. Classify mapping_type and produce structured output.

No AI / heuristic guessing beyond explicit text pattern matches.
"""

from __future__ import annotations

import argparse
import json
import re
import time
from dataclasses import asdict, dataclass
from pathlib import Path

import pandas as pd
import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent.parent
DISCOVERED = ROOT / "data" / "reference" / "discovery" / "nhanes_pesticide_variables_discovered.csv"
CACHE_DIR = ROOT / "data" / "raw" / "codebooks"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

URL_PATTERNS = [
    "https://wwwn.cdc.gov/Nchs/Nhanes/{cycle_start}-{cycle_end}/{file}.htm",
    "https://wwwn.cdc.gov/Nchs/Nhanes/{cycle_start}-{cycle_end}/Lab{file}.htm",
    "https://wwwn.cdc.gov/Nchs/Nhanes/{cycle_start}-{cycle_end}/{file}",
]

PARENT_REGEXES = {
    "specific_parent": re.compile(r"\bmetabolite of ([A-Za-z0-9'\-/ (),]+)", re.IGNORECASE),
    "multi_parent_family": re.compile(
        r"\b(common metabolite of|metabolite of multiple|metabolite of several) ([A-Za-z0-9'\-/ (),]+)",
        re.IGNORECASE,
    ),
    "persistent_metabolite": re.compile(
        r"\bpersistent (?:environmental )?metabolite of ([A-Za-z0-9'\-/ (),]+)",
        re.IGNORECASE,
    ),
    "non_specific_family": re.compile(
        r"\bnon[- ]specific (?:biomarker|metabolite) of ([A-Za-z0-9'\-/ (),]+)",
        re.IGNORECASE,
    ),
    "parent_compound": re.compile(r"\b(parent compound)\b", re.IGNORECASE),
}

STOPWORDS = {"pesticides", "pyrethroid insecticides", "organophosphate pesticides"}


@dataclass
class MappingRecord:
    analyte_name: str
    variable_name: str
    data_file_name: str
    earliest_cycle: int
    source_url: str
    mapping_type: str
    parent_pesticides: list[str]
    evidence_sentences: list[str]
    verification_date: str


def fetch_codebook_html(cycle: int, data_file: str) -> tuple[str, str | None]:
    """Fetch codebook HTML with caching."""
    cache_file = CACHE_DIR / f"{data_file}_{cycle}.html"
    if cache_file.exists():
        content = cache_file.read_text(encoding="utf-8")
        # Check if cached content is a 404 page
        if "Page Not Found" in content or "404" in content[:500]:
            cache_file.unlink()  # Remove bad cache
        else:
            return content, f"(cached){cache_file.name}"

    # Convert cycle year to cycle range format (e.g., 2005 -> 2005-2006)
    cycle_start = cycle
    cycle_end = cycle + 1

    session = requests.Session()
    session.headers.update({"User-Agent": "PopHealthObservatory/parent-mapping"})
    for pattern in URL_PATTERNS:
        url = pattern.format(cycle_start=cycle_start, cycle_end=cycle_end, file=data_file)
        try:
            resp = session.get(url, timeout=30)
            if resp.status_code == 200 and "html" in resp.headers.get("Content-Type", ""):
                # Check if it's actually a 404 page
                if "Page Not Found" not in resp.text[:1000]:
                    cache_file.write_text(resp.text, encoding="utf-8")
                    return resp.text, url
        except requests.RequestException:
            continue
    return "", None


def extract_sentences(text: str) -> list[str]:
    """Basic sentence splitter."""
    raw = re.split(r"(?<=[.!?])\s+", text)
    return [s.strip() for s in raw if s.strip()]


def classify_mapping(sentences: list[str]) -> tuple[str, list[str], list[str]]:
    """Search sentences for mapping evidence."""
    matches: list[str] = []
    evidence: list[str] = []
    mapping_type = "unmapped"

    for s in sentences:
        for mtype, pattern in PARENT_REGEXES.items():
            m = pattern.search(s)
            if m:
                mapping_type = mtype if mapping_type == "unmapped" else mapping_type
                # Extract group with parents if present
                groups = m.groups()
                if groups:
                    parent_phrase = groups[-1]
                    # Split potential list
                    raw_parts = re.split(r"[;,/]| and ", parent_phrase)
                    cleaned = []
                    for part in raw_parts:
                        part = part.strip(" ()")
                        if not part or part.lower() in STOPWORDS:
                            continue
                        cleaned.append(part)
                    if cleaned:
                        matches.extend(cleaned)
                        evidence.append(s)
    # Deduplicate
    matches = sorted(set(matches))
    return mapping_type, matches, evidence


def derive_mapping_for_variable(row: pd.Series, verification_date: str) -> MappingRecord:
    variable = row["variable_name"]
    data_file = row["data_file_name"]
    cycle = int(row["cycle"])
    html, url = fetch_codebook_html(cycle, data_file)
    if not html or not url:
        return MappingRecord(
            analyte_name=variable,  # will normalize later
            variable_name=variable,
            data_file_name=data_file,
            earliest_cycle=cycle,
            source_url=url or "",
            mapping_type="unmapped",
            parent_pesticides=[],
            evidence_sentences=[],
            verification_date=verification_date,
        )
    soup = BeautifulSoup(html, "html.parser")

    # Gather textual sections
    texts = []
    for selector in ["p", "td", "li"]:
        for el in soup.select(selector):
            t = el.get_text(separator=" ", strip=True)
            if t:
                texts.append(t)
    full_text = " ".join(texts)
    sentences = extract_sentences(full_text)
    mtype, parents, evidence = classify_mapping(sentences)

    return MappingRecord(
        analyte_name=variable,
        variable_name=variable,
        data_file_name=data_file,
        earliest_cycle=cycle,
        source_url=url,
        mapping_type=mtype,
        parent_pesticides=parents,
        evidence_sentences=evidence[:5],  # cap for brevity
        verification_date=verification_date,
    )


def main():
    ap = argparse.ArgumentParser(description="Derive analyte → parent pesticide mapping from NHANES docs")
    ap.add_argument("--verification-date", default="2025-11-08")
    ap.add_argument(
        "--output-jsonl",
        default="data/reference/parent_pesticide_mapping_raw.jsonl",
    )
    ap.add_argument("--limit", type=int, default=0, help="Process only first N unique variables (debug)")
    args = ap.parse_args()

    df = pd.read_csv(DISCOVERED)

    # Choose earliest cycle per variable (for initial evidence)
    earliest = (
        df.sort_values("cycle")
        .groupby("variable_name", as_index=False)
        .first()[["variable_name", "data_file_name", "cycle"]]
    )

    if args.limit:
        earliest = earliest.head(args.limit)

    records: list[MappingRecord] = []
    for i, row in earliest.iterrows():
        print(f"[{i+1}/{len(earliest)}] {row['variable_name']} → fetching documentation...")
        rec = derive_mapping_for_variable(row, args.verification_date)
        records.append(rec)
        time.sleep(0.5)  # polite pacing

    out_path = ROOT / args.output_jsonl
    with out_path.open("w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(asdict(r), ensure_ascii=False) + "\n")

    print(f"\n✓ Saved raw mapping evidence to {out_path}")
    summary = {}
    for r in records:
        summary[r.mapping_type] = summary.get(r.mapping_type, 0) + 1
    print("Mapping type counts:")
    for k, v in summary.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
