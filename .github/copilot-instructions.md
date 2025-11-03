# PopHealth Observatory – Comprehensive Copilot Instructions

Authoritative, project-specific guidance for AI-assisted code generation. Align generated code with current repository architecture, data flow, naming, and testing practices. Avoid generic boilerplate.

---
## 1. Project Overview
**Primary Purpose**: Unified toolkit for NHANES cycle-aware ingestion, harmonization, component metadata manifesting, and pesticide analyte text snippet extraction with an experimental Retrieval-Augmented Generation (RAG) layer.

**Problem Solved**: NHANES data access is fragmented (multiple URL patterns, schema drift, inconsistent variable naming). This codebase automates resilient multi-URL downloads, semantic column renaming, derived health metric computation (BMI, blood pressure categories), and creates text snippet context for downstream retrieval and question answering.

---
## 2. Technology Stack
### Python Packages (from `pyproject.toml` & `requirements.txt`)
Runtime:
- pandas, numpy – tabular & numeric processing
- requests – HTTP retrieval of XPT files and HTML pages
- matplotlib, seaborn, plotly, ipywidgets – visualization & interactive notebooks
Optional groups:
- rag: sentence-transformers, faiss-cpu (vector embeddings; FAISS skipped on Windows via marker)
Dev/Docs:
- pytest, coverage – testing & coverage
- ruff, black – lint & formatting
- build, twine – packaging/distribution
- mkdocs, mkdocs-material – static documentation site

### Python Version Targets
`requires-python >=3.8` (project metadata) but code uses modern typing forms (`list[str]`) and targets 3.10+ (Black & Ruff configs: `py310` .. `py313`).

### R Packages (Planned for Future Structured Data Analysis)
Referenced in setup/roadmap for a potential, separate R-based analytics layer:
- arrow – Parquet exchange (required for any R/Python interop)
- testthat – unit tests (required)
- *Optional for advanced tabular analysis (not relevant to pesticide RAG):*
  - BiocCheck, BiocStyle – Bioconductor compliance
  - SummarizedExperiment / MultiAssayExperiment – assay + metadata containers
  - jsonlite – light JSON utilities
No R source currently; do NOT invent usage until `r/` directory exists.

### Other Tools
- Streamlit (`streamlit_app.py`) – lightweight interactive UI
- GitHub Actions (workflow under `.github/workflows/`) – CI for lint/tests
- Jupyter notebooks (`notebooks/`) – exploration & prototyping
- No databases; remote CDC endpoints only
- No reticulate, no Quarto; MkDocs drives docs site

---
## 3. Architecture & Folder Roles
```
pophealth_observatory/     # Core Python library modules
    observatory.py           # PopHealthObservatory & NHANESExplorer classes
    pesticide_ingestion.py   # Text segmentation, regex pattern indexing, Snippet dataclass
    pesticide_context.py     # Reference analyte loading
    rag/                     # RAG scaffolding (config, embeddings, pipeline, index)
tests/                     # Pytest suite (unit tests for ingestion & RAG)
manifests/                 # Generated JSON component manifests
data/
    raw/pesticides/          # Source text files for pesticide snippet extraction
    processed/pesticides/    # Output JSONL snippet artifacts
docs/                      # MkDocs documentation sources
apps/                      # Streamlit application entry(s)
notebooks/                 # Exploratory analysis & prototyping
```

**Code Organization Principles**:
- Pure transformation helpers separate from I/O wrappers
- Regex pattern compilation done once before iteration
- Dataclasses for structured text snippet records
- Caches limited to explicit dictionaries (e.g. `data_cache`, `_component_page_cache`)

---
## 4. Data Flow & Exchange
1. Multi-URL attempt download of NHANES XPT → pandas DataFrame
2. Column subset & semantic renaming via mapping dicts
3. Derived fields (gender/race labels, BMI category, averaged blood pressure) computed
4. JSON manifest generation of component metadata (stored under `manifests/`)
5. Pesticide text ingestion: segment sentences → match analyte/pesticide tokens → create `Snippet` dataclass instances → serialize line-oriented JSONL
6. RAG pipeline loads snippet texts → builds embedding index (FAISS or alt) → retrieval & prompt assembly
7. (Planned) Cross-language Parquet artifacts in `shared_data/` for R/Python (Arrow) interchange

**Current Exchange**: JSONL (snippets), JSON (manifests). No Parquet yet.
**Preferred Cross-Language Protocol**: Arrow Parquet; no CSV, no reticulate.

Naming (planned Parquet): `YYYY-MM-DD_<descriptor>.parquet` (e.g. `2025-11-02_cycle_demographics.parquet`). Avoid committing >10MB.

---
## 5. Python Code Patterns & Standards
### Core Patterns
- Paths: always `Path` objects
- Type hints: required on all public functions & methods
- Regex: compiled once (e.g. `_index_analyte_patterns`) using word-boundaries + case-insensitive flags
- Serialization: JSONL one-object-per-line, `ensure_ascii=False`
- Prompt assembly separated from retrieval logic (`_format_prompt` in RAG pipeline)

### Naming
- Modules/functions: `snake_case`
- Private helpers: prefix `_`
- Classes: `CamelCase` (`PopHealthObservatory`, `NHANESExplorer`, `RAGPipeline`, `Snippet` dataclass)
- Dataclass fields: lowercase `snake_case`

### Error Handling
- Raise `ValueError` for invalid parameters (e.g., unknown cycle suffix)
- Return empty DataFrame when multi-URL download fails (after logging/printing errors)
- Avoid silent broad exception swallowing (limit to narrow try/except where justified)

### Example (Snippet dataclass)
```python
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
```

### Docstrings
Current mix (some minimal). New code SHOULD use NumPy-style sections: Parameters, Returns, Raises.

### Performance Guidelines
- Precompute indices (regex, embeddings) before loops
- Avoid per-record network calls; batch when expanding features
- Keep functions < ~40 LOC unless cohesive (HTML table parsing acceptable but factor internal helpers if it grows further)

---
## 6. Planned R Layer for Structured Data (Future/Optional)
*(This section is for a potential future enhancement focused on tabular NHANES data analysis in R. It is NOT relevant to the current pesticide text-mining and RAG pipeline.)*
- Assignment operator: `<-`
- Classes: S4 CamelCase (e.g. `NhAnesCycleData`)
- Functions: `snake_case`
- Documentation: roxygen2 with `@export`
- Data interchange: `arrow::write_parquet()` / `arrow::read_parquet()`; never reticulate
- Containers: `SummarizedExperiment` or `MultiAssayExperiment` for assay + demographics
- Validation: cycle string matches `^[0-9]{4}-[0-9]{4}$`; stop with informative message otherwise
- Tests: `tests/testthat/` verifying constructor, slot integrity, round-trip Parquet

---
## 7. Testing Practices
### Python
- Framework: `pytest` (see `[tool.pytest.ini_options]` in `pyproject.toml`)
- Location: `tests/` directory
- Style: small deterministic unit tests for pure helpers
- Use `tmp_path` for filesystem outputs (snippet writing)
- Mock embedder for RAG retrieval ordering (length-based vector encoding)

**Edge Cases to Cover**:
- Empty text → no snippets
- Multiple analyte matches in one sentence
- Unicode characters in sentences
- Failed network downloads → empty DataFrame
- Merged dataset preserves participant count uniqueness

### Coverage Targets
- Regex correctness (boundary, whole-word)
- Snippet window boundaries (first/last sentence handling)
- Prompt truncation respects `max_chars`
- Data merge integrity (`participant_id` uniqueness)

### Future R
- `testthat` parity: cycle validation, parquet round-trip, row/column preservation

---
## 8. File Naming Conventions
| Artifact Type | Pattern | Example |
| ------------- | ------- | ------- |
| Python module | `snake_case.py` | `pesticide_ingestion.py` |
| Dataclass name | `CamelCase` | `Snippet` |
| Snippet output | `snippets_<source_id>.jsonl` | `snippets_pdp_sample.jsonl` |
| Manifest JSON  | `component_files_manifest_<years>_all_components_detailed.json` | `component_files_manifest_2021_2023_all_components_detailed.json` |
| Notebook       | `snake_case.ipynb` | `nhanes_explorer_demo.ipynb` |
| Planned Parquet| `YYYY-MM-DD_<descriptor>.parquet` | `2025-11-02_cycle_demographics.parquet` |
| R script (future) | `snake_case.R` | `load_cycle_data.R` |

---
## 9. Build / Run / Test Commands
### Python
Install (editable + dev extras):
```bash
pip install -e .[dev]
```
Run tests:
```bash
pytest
```
Coverage report:
```bash
coverage run -m pytest && coverage report -m
```
Lint & format checks:
```bash
ruff check .
black --check .
```
Build distribution artifacts:
```bash
python -m build
```

### Planned R (once added)
```r
R CMD check .
Rscript -e "BiocCheck::BiocCheck('r/')"
Rscript -e "testthat::test_dir('r/tests/testthat')"
```

---
## 10. RAG Pipeline Contract (Experimental)
`RAGPipeline` responsibilities:
- `prepare()`: load snippets + build or load embeddings
- `retrieve(question, top_k)`: return ordered snippet dicts
- `generate(question, generator, top_k)`: construct prompt via `_format_prompt`, delegate generation to external callable `(question, snippets, prompt) -> answer`
Keep embedding mechanism (vector index) decoupled from prompt assembly & generation.

**Mock Embedder Example**:
```python
class _MockEmbedder(BaseEmbedder):
        def encode(self, texts: list[str]) -> list[list[float]]:
                return [[float(len(t))] for t in texts]
```

Use for deterministic retrieval tests (similarity by length).

---
## 11. Extension Blueprints
### New Snippet Domain
1. `_index_<domain>_patterns()` → list[(domain_obj, compiled_pattern)]
2. `generate_<domain>_snippets(sentences, ...)` → yields dataclass instances
3. Reuse `write_snippets` for JSONL output
4. Pytest verifying counts + window boundaries

### New NHANES Component Loader
1. Add mapping to `self.components`
2. Implement `get_<component>(cycle)` patterned after `get_body_measures`
3. Column rename + derived metrics
4. Merge through `participant_id`
5. Tests mocking network responses or skipping when offline

---
## 12. Prompting Guidance
Reference this file explicitly:
```text
Follow .github/copilot-instructions.md; implement extract_analyte_summary(sentences: list[str]) -> dict[str,int] and add pytest covering empty input & multi-sentence counts.
```
R (future):
```text
Follow .github/copilot-instructions.md; create S4 class NhAnesCycleData with cycle validation & testthat tests.
```
RAG addition:
```text
Follow .github/copilot-instructions.md; add max_chars param to _format_prompt with truncation test.
```

---
## 13. Security & Robustness
- Network calls: always specify timeouts
- Fail gracefully: empty DataFrame on download failure (with collected error context)
- Avoid printing sensitive info; current simple prints acceptable until logging upgrade
- Future secrets: `.env` (excluded in `.gitignore`)

---
## 14. What NOT To Generate
- No reticulate (R/Python bridging) – use Parquet
- No CSV for cross-language exchange (only Parquet / JSONL)
- No speculative repository/service abstractions without duplication evidence
- No global mutable singletons besides limited caches

---
## 15. Summary Checklist (Internal Use)
Paths via `Path` ✓  | Type hints ✓ | Dataclasses for records ✓ | JSONL outputs ✓ | Regex precompiled ✓ | Tests for pure functions ✓ | R layer future (S4 + Arrow) | Prompt references explicit ✓

Keep this document updated as new components, R code, or data exchange artifacts are introduced.

