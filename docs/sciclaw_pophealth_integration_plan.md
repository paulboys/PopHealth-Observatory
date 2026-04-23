# SciClaw × PopHealth Observatory Integration Plan

**Use Case**: Pyrethroid Biomonitoring — 3-PBA (CAS 70458-82-3)

**Date**: 2026-04-22

---

## Objective

Combine PopHealth Observatory's NHANES data pipeline with SciClaw's agentic research capabilities to produce a reproducible, evidence-grounded scientific report on temporal trends in 3-phenoxybenzoic acid (3-PBA) exposure across U.S. population cohorts.

## Workflows

| Phase | Workflow | PopHealth Observatory Role | SciClaw Role |
|-------|----------|---------------------------|--------------|
| 1 | Data Exploration | Load NHANES pesticide lab data for 3-PBA across cycles, harmonize, compute summary statistics | Not needed (pure data layer) |
| 2 | Literature Search | Provide analyte context (CAS RN, reference metadata, enrichment records) as seed queries | Agentic web search across PubMed, EPA, CDC sources; extract structured evidence |
| 3 | Report Authoring | Supply tables, figures, validated data summaries | Synthesize narrative sections from retrieved literature + data context |
| 4 | Scientific Writing | Enrichment merge provides citation metadata and evidence statements | Draft manuscript sections (intro, methods, results, discussion) grounded in both data and literature |

---

## Architecture

```text
PopHealth Observatory (Python)          SciClaw (Go CLI)
─────────────────────────────           ─────────────────
1. Data Exploration
   get_pesticide_metabolites()
   load_analyte_reference()
   → NHANES 3-PBA data + stats
   → export summary to workspace

                                        2. Literature Search
                                           sciclaw agent -m "Find recent
                                           papers on 3-PBA (CAS 70458-82-3)
                                           pyrethroid exposure biomarkers"
                                           → pubmed-cli skill
                                           → workspace evidence trail

3. Evidence Ingest
   load_evidence_enrichment()
   merge_reference_with_enrichment()
   → structured evidence records

                                        4. Scientific Writing
                                           sciclaw agent -m "Draft methods
                                           and results using workspace data"
                                           → quarto-authoring skill
                                           → .qmd manuscript sections
```

---

## Deliverables

### 1. SciClaw Bridge Module

**File**: `pophealth_observatory/sciclaw_bridge.py`

Responsibilities:

- Export PopHealth data summaries to SciClaw workspace format (JSON)
- Parse SciClaw evidence output back into `EvidenceEnrichmentRecord` JSONL
- Map SciClaw citation objects to `EvidenceCitation` dataclass instances

### 2. Orchestration Script

**File**: `scripts/sciclaw/pyrethroid_3pba_pipeline.py`

End-to-end pipeline running all 4 phases:

```python
# Phase 1: Data Exploration (PopHealth Observatory)
from pophealth_observatory.laboratory_pesticides import get_pesticide_metabolites
from pophealth_observatory.pesticide_context import (
    load_analyte_reference, load_evidence_enrichment,
    merge_reference_with_enrichment, find_analyte,
)

# Pull NHANES 3-PBA data across available cycles
cycles = ["2007-2008", "2009-2010", "2011-2012", "2013-2014", "2015-2016"]
# Load, summarize, export stats as JSON to SciClaw workspace

# Phase 2: Call SciClaw for literature search
import subprocess
subprocess.run([
    "sciclaw", "agent", "-m",
    "Search PubMed for 3-PBA (CAS 70458-82-3) pyrethroid metabolite "
    "biomonitoring studies published 2015-2025. Save structured citations."
])

# Phase 3: Ingest SciClaw evidence back into PopHealth enrichment
# Parse SciClaw workspace output → enrichment JSONL
# load_evidence_enrichment() + merge

# Phase 4: Call SciClaw for Quarto manuscript drafting
subprocess.run([
    "sciclaw", "agent", "-m",
    "Using the NHANES summary data and PubMed evidence in workspace, "
    "draft a Quarto manuscript on temporal trends in 3-PBA exposure."
])
```

### 3. Quarto Manuscript Template

**File**: `docs/pyrethroid_3pba_report.qmd`

A Quarto document skeleton populated by the pipeline with:

- Data exploration tables and figures from PopHealth Observatory
- Literature citations from SciClaw's `pubmed-cli`
- Evidence-grounded narrative sections from SciClaw's `scientific-writing` skill

---

## SciClaw Skills Used

| Workflow | SciClaw Skill | Purpose |
|----------|---------------|---------|
| Literature search | `pubmed-cli` | PubMed search, article fetch, citation graphs, MeSH lookup |
| Report authoring | `quarto-authoring` | Loop-driven `.qmd` authoring and rendering |
| Scientific writing | `scientific-writing` | Manuscript drafting with claim-evidence alignment |
| Evidence provenance | `experiment-provenance` | Reproducible experiment metadata capture |

---

## SciClaw Workspace Routing

Route SciClaw to the PopHealth Observatory workspace so it can access data artifacts directly:

```bash
sciclaw routing add \
  --channel discord \
  --chat-id <your-channel-id> \
  --workspace /c/Users/User/Documents/NHANES \
  --label pophealth-3pba
```

This gives SciClaw direct access to `data/reference/enrichment/` for reading and writing evidence artifacts.

---

## Data Flow

```text
NHANES XPT files
  → PopHealth Observatory: download, harmonize, derive metrics
  → Export: cycle summary JSON + analyte reference context
  → SciClaw workspace: ~/sciclaw/ or routed NHANES workspace

SciClaw PubMed search
  → Structured citations (title, DOI, PMID, journal, year)
  → Evidence statements with confidence scores
  → Saved to workspace evidence trail

PopHealth enrichment ingest
  → Parse SciClaw output → EvidenceEnrichmentRecord JSONL
  → load_evidence_enrichment() → merge_reference_with_enrichment()
  → Enriched analyte context available in RAG pipeline

SciClaw Quarto authoring
  → Reads enriched data + evidence from workspace
  → Drafts .qmd manuscript sections
  → Renders to HTML/PDF/DOCX via Quarto
```

---

## Reproducibility Controls

| Control | Mechanism |
|---------|-----------|
| Data layer reproducibility | `RAGConfig(enable_evidence_enrichment=False)` bypasses enrichment for raw snippet-only runs |
| Evidence provenance | SciClaw `experiment-provenance` skill logs all search queries and results |
| Audit trail | SciClaw workspace stores full session history in `~/sciclaw/sessions/` |
| Citation verification | `EvidenceCitation` dataclass requires at least one identifier (DOI, PMID, or URL) |
| Record validation | `_parse_evidence_record()` enforces CAS RN format, non-empty summaries, confidence bounds |

---

## PopHealth Observatory Modules Involved

| Module | Functions Used |
|--------|----------------|
| `laboratory_pesticides.py` | `get_pesticide_metabolites(cycle)` |
| `pesticide_context.py` | `load_analyte_reference()`, `find_analyte()`, `load_evidence_enrichment()`, `merge_reference_with_enrichment()` |
| `pesticide_ingestion.py` | `generate_snippets()`, `write_snippets()` |
| `rag/pipeline.py` | `RAGPipeline.prepare()`, `.retrieve()`, `.generate()` |
| `rag/config.py` | `RAGConfig(enable_evidence_enrichment=True/False)` |
| `sciclaw_bridge.py` | `export_data_summary()`, `parse_sciclaw_evidence()`, `import_citations()` |

---

## Implementation Order

1. **`pophealth_observatory/sciclaw_bridge.py`** — Export/import bridge between PopHealth data structures and SciClaw workspace
2. **`scripts/sciclaw/pyrethroid_3pba_pipeline.py`** — Orchestration script running all 4 phases
3. **`docs/pyrethroid_3pba_report.qmd`** — Quarto manuscript template with embedded Python code chunks
4. **Tests** — Unit tests for bridge module serialization and round-trip parsing
