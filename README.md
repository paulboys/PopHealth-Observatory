# PopHealth Observatory

![PyPI Version](https://img.shields.io/pypi/v/pophealth-observatory.svg)
![Python Versions](https://img.shields.io/pypi/pyversions/pophealth-observatory.svg)
![License](https://img.shields.io/github/license/paulboys/PopHealth-Observatory.svg)
![Docs](https://img.shields.io/badge/docs-online-blue.svg)

Exploratory population health & nutrition analytics: acquisition → harmonization → stratified insights → geographic & temporal visualization.

PopHealth Observatory is an open-source toolkit for exploring population health and nutrition metrics using publicly available survey microdata (NHANES) and state-level prevalence (BRFSS). It streamlines secure data acquisition, cleaning, demographic stratification, trend / cross‑cycle analysis, exploratory visualization, and geographic prevalence mapping—designed for assumption checking, rapid exploratory real‑world evidence generation, and reproducible epidemiologic or health disparities research.

## Overview

![PopHealth Observatory Overview](docs/assets/images/PopHealth_Observatory.png)

The project provides a Python-based framework for ingesting, harmonizing, and analyzing public health survey data (initially NHANES). NHANES (National Health and Nutrition Examination Survey) is a nationally representative program assessing the health and nutritional status of the U.S. population. PopHealth Observatory abstracts common data wrangling and analytic patterns so you can focus on questions, not boilerplate.

## Core Capabilities

Fundamental building blocks beyond the Streamlit UI—each designed for repeatable, auditable exploratory epidemiology workflows:

| Domain | What It Does | Key Objects / Functions | Output Artifacts |
|--------|--------------|-------------------------|------------------|
| Resilient Acquisition | Attempts multiple URL patterns for NHANES SAS transport files, applies timeouts, returns empty DataFrame (not exception crash) on failure | `PopHealthObservatory._download_xpt`, `NHANESExplorer.get_<component>()` | In‑memory DataFrames |
| Schema Harmonization | Column subset + semantic renaming, derived gender/race labels applied uniformly across cycles | `NHANESExplorer._standardize_columns`, `create_merged_dataset()` | Cycle‑merged DataFrames |
| Derived Health Metrics | BMI, BMI category, averaged BP (systolic/diastolic), BP stage classification | `NHANESExplorer._derive_metrics` | Enriched analytic columns |
| Component Metadata Manifesting | Parses component listing HTML tables, normalizes spans, attaches file URLs, sizes, publish dates, schema versioning | `NHANESExplorer.get_detailed_component_manifest()` | JSON / JSONL manifests under `manifests/` |
| Validation Layer | Programmatic dataset integrity (row counts, source availability) + expanding reproducibility notebooks | `NHANESExplorer.validate()`; notebooks in `reproducibility/` | Structured validation dict + notebooks |
| BRFSS Indicator Exploration | Local Parquet snapshot + indicator/year filtering; animated choropleth playback | `BRFSSExplorer` methods, `scripts/fetch_brfss_data.py` | Parquet cache + interactive plots |
| Pesticide Text Snippet Extraction | Sentence segmentation, regex analyte matching, windowed snippet construction (context preserved) | `pesticide_ingestion.generate_snippets()` (Dataclass `Snippet`) | JSONL snippet files (`data/processed/pesticides/`) |
| RAG Embedding & Retrieval (Experimental) | Deterministic or model-based embeddings; ranked snippet retrieval; prompt assembly decoupled from generation | `rag.pipeline.RAGPipeline`, `DummyEmbedder`, `SentenceTransformerEmbedder` | In‑memory embedding cache + retrieval results |
| Extensible Loader Pattern | New NHANES components follow consistent mapping + derivation contract | `NHANESExplorer.get_body_measures()` (pattern exemplar) | Additional domain-specific DataFrames |
| Caching Strategy | Lightweight in‑session caches (data files, component pages) to avoid redundant network calls | Internal dictionaries (`_component_page_cache`, `data_cache`) | Faster repeated interactive queries |
| Planned Cross‑Language Exchange | Parquet format reserved for future R analytics layer (Arrow) | Future `r/` directory (design only) | Parquet snapshots (naming: `YYYY-MM-DD_<descriptor>.parquet`) |

Design Principles:
- Pure transformation helpers separated from I/O
- Precomputed indices (regex patterns, embeddings) before iteration loops
- Dataclasses (e.g. `Snippet`) for structured, schema-stable records
- Explicit, narrow exception handling (fail gracefully with empty DataFrames)
- Type hints and predictable return contracts (dict / list / DataFrame)
- One-object-per-line JSONL for append-friendly text artifact generation
- Separation of retrieval vs prompt formatting in RAG pipeline

These capabilities permit a workflow where ingestion, harmonization, derived metric expansion, validation, and exploratory retrieval (text + tabular) occur through programmable, test‑covered interfaces—reducing manual wrangling time before hypothesis generation.

## Features

- **Automated Acquisition**: Pull SAS transport (.XPT) files directly from CDC endpoints
- **Caching Layer**: Avoid redundant downloads within a session
- **Schema Harmonization**: Standardized variable selection & human-readable labels
- **Derived Metrics**: BMI categories, blood pressure categories, summary anthropometrics
- **Demographic Stratification**: Rapid group-wise descriptive statistics
- **Cycle Comparison**: Simple cross-cycle trend scaffolding
- **Visualization Suite**: Boxplots, distributions, stratified means, interactive widgets
- **Tabbed Streamlit UI (0.6.0)**: Cross-sectional, Trend Analysis, Bivariate relationships, and Geographic (state‑level BRFSS) views with per‑tab demographic filters
- **Multi-Dataset Support**:
  - **NHANES**: National-level clinical measurements and demographics
  - **BRFSS**: State-level health indicators via `BRFSSExplorer` class (obesity, physical activity, nutrition metrics)
  - Geographic health analysis combining national trends with state-level prevalence
- **Animated Time Series (0.6.0)**: Year‑over‑year choropleth playback (2011–2023) for BRFSS indicators
- **Local BRFSS Parquet Caching (0.6.0)**: One-time multi‑year download script with in‑memory indicator/year filtering (no repeated API calls)
- **Extensible Architecture**: Plug in additional NHANES components or other survey sources
- **Reproducible Reporting**: Programmatic summary report generation
- **Rich Metadata Manifest**: Enumerate all component table rows with standardized schema & filtering
- **Logo Theming (0.6.0)**: Light + dark transparent logo variant generated automatically (Pillow)

## Installation

Full setup instructions (including development workflow & validation layers):
`SETUP_GUIDE.md` (repository root) | Online: https://paulboys.github.io/PopHealth-Observatory/setup-guide/

## Repository Structure

```
├─ apps/                       # End-user applications (Streamlit, future CLI wrappers)
│  └─ streamlit_app.py         # Interactive NHANES exploration UI
├─ examples/                   # Simple executable usage examples
│  └─ demo.py                  # Former main.py demonstration script
├─ manifests/                  # Generated manifest JSON artifacts (not source code)
│  └─ component_files_manifest_...json
├─ notebooks/                  # Exploratory & development Jupyter notebooks
│  ├─ nhanes_demographics_link_finder.ipynb
│  ├─ nhanes_explorer_demo.ipynb
│  ├─ nhanes_url_testing.ipynb
│  ├─ observatory_exploration.ipynb
│  └─ README.md
├─ pophealth_observatory/      # Library source (core observatory & explorer classes)
├─ tests/                      # Automated tests (unit / integration)
├─ requirements.txt            # Python dependencies
├─ pyproject.toml / setup.py   # Packaging configuration
├─ CHANGELOG.md                # Versioned change log
└─ README.md                   # Project documentation (this file)
```

### Apps Directory

`apps/streamlit_app.py` provides an interactive interface to:
- Select NHANES cycle and view merged demographics + clinical metrics
- Slice metrics by demographic categories with summary statistics
- Inspect laboratory and questionnaire file inventory via manifest sampling
- Preview raw merged data (first N rows) for QA

Future additions may include:
- CLI data export tool (e.g., `apps/nhanes_export.py`)
- Dashboard variants (e.g., multi-page Streamlit or FastAPI backend)


### From Source (Development)

1. Clone:
   ```
   git clone https://github.com/paulboys/PopHealth-Observatory.git
   cd PopHealth-Observatory
   ```
2. (Recommended) Create & activate a virtual environment.
3. Install in editable mode with dev extras:
   ```
   pip install -e .[dev]
   ```

### From PyPI
```
pip install pophealth-observatory
```

## Quick Start

```python
from pophealth_observatory import NHANESExplorer

# Initialize the explorer (NHANES-focused implementation)
explorer = NHANESExplorer()

# Validate data quality before analysis (recommended)
validation_report = explorer.validate('2017-2018', ['demographics', 'body_measures'])
print(f"Data Validation: {validation_report['status']}")  # PASS/WARN/FAIL

# Download and merge demographics, body measures, and blood pressure data
data = explorer.create_merged_dataset('2017-2018')

# Generate a summary report
print(explorer.generate_summary_report(data))

# Analyze BMI by race/ethnicity
bmi_by_race = explorer.analyze_by_demographics(data, 'bmi', 'race_ethnicity_label')
print(bmi_by_race)

# Create visualization
explorer.create_demographic_visualization(data, 'bmi', 'race_ethnicity_label')
```

### BRFSS State-Level Data

For geographic health analysis, use the `BRFSSExplorer` to access state-level indicators:

```python
from pophealth_observatory import BRFSSExplorer

# Initialize BRFSS explorer
brfss = BRFSSExplorer()

# Get latest state-level obesity data
obesity_data = brfss.get_obesity_data()
print(brfss.summary(obesity_data))

# Get other indicators
physical_activity = brfss.get_indicator(
    class_name='Physical Activity',
    question='Percent of adults aged 18 years and older who engage in no leisure-time physical activity'
)

# Discover available indicators
indicators = brfss.list_available_indicators()
print(indicators.head(10))
```

## Interactive App (Streamlit)

An interactive exploration UI is provided via `streamlit_app.py`.

Run locally (from project root):
```bash
streamlit run apps/streamlit_app.py
```

App Tabs (0.6.0):
- **Cross-Sectional**: Cycle selection, demographic filters (age, gender, race), metric distribution (box/violin), summary stats
- **Trend Analysis**: Multi-cycle comparison with confidence bands and optional survey weights
- **Bivariate Analysis**: Scatter with OLS trendline, Pearson correlation
- **Geographic (BRFSS)**: Single-year or animated multi-year choropleth; local cached data filtering; state ranking table

Performance Improvements (0.6.0):
- Indicator-level cached normalization for BRFSS (fast year switching)
- Removal of repeated per-year API calls in animated view
- Metrics hidden during animation to avoid static misinterpretation

Optional Local BRFSS Cache (recommended for speed):
```bash
python scripts/fetch_brfss_data.py  # generates data/processed/brfss_indicators.parquet
```
After creation, the app reads the Parquet file first; API fallback occurs only if missing.

Requirements: `streamlit`, `plotly`, `pillow` (auto logo processing), and core package dependencies.

Tagline updated to emphasize *exploratory analysis* rather than definitive scientific visualization.

> If you encounter slow initial BRFSS loads, ensure the Parquet cache is generated and verify network throughput.

### New Dependency (0.6.0)
`pillow` added for runtime logo dark/transparent variant generation.

### Plan for 0.7.0 (Preview)
- Expanded survey weight robustness (design effects)
- Additional NHANES component loaders
- Optional DuckDB persistent cache layer


## Metadata Manifest (NHANES Component Tables)

The explorer can build a structured manifest of NHANES component listing tables (Demographics, Examination, Laboratory, Dietary, Questionnaire) including:

Fields per row:
- `year_raw`, `year_normalized` (e.g. `2005_2006`)
- `data_file_name`
- **Programmatic Validation**: Automated integrity checks (row counts & source availability)
- **Analytical Validation (in progress)**: Reproducibility notebooks confirm published statistics
- **Survey Weight Helpers (experimental)**: Auto-recommend weight variable + weighted mean utility
- `doc_file_url`, `doc_file_label`
- `data_file_url`, `data_file_label`
- `data_file_type` (XPT | ZIP | FTP | OTHER)
- `data_file_size` (e.g. `3.4 MB` if present)
- `date_published`
- `original_filename`, `derived_local_filename` (cycle-year appended for XPT when possible)

Schema control:
- Top-level manifest includes `schema_version` (semantic version; current: `1.0.0`) and `generated_at` (UTC ISO timestamp).
- Future structural changes will increment the manifest schema version (MAJOR = breaking, MINOR = additive, PATCH = non-breaking fixes).

### Generate a Manifest

```python
from pophealth_observatory.observatory import NHANESExplorer
e = NHANESExplorer()
manifest = e.get_detailed_component_manifest(
   components=['Demographics','Laboratory'],
   file_types=['XPT'],            # optional filter
   year_range=('2005','2014'),    # inclusive overlap on normalized spans
   as_dataframe=True              # attach pandas DataFrame
)
print(manifest['schema_version'], manifest['total_file_rows'])
print(manifest['summary_counts'])
df = manifest['dataframe']
print(df.head())
```

### Persist to JSON

```python
e.save_detailed_component_manifest(
   'nhanes_manifest.json',
   file_types=['XPT','ZIP'],
   year_range=('1999','2022')
)
```

### Overriding Schema Version (Advanced)

You can pass a custom `schema_version` if producing a forked or experimental layout:

```python
e.get_detailed_component_manifest(schema_version='1.1.0-exp')
```

### Caching & Refresh

- Component listing HTML pages are cached in-memory per session.
- Use `force_refresh=True` to re-fetch a component page.

### Filtering Logic

- `year_range=('2005','2010')` keeps any row whose normalized span overlaps that interval.
- `file_types=['XPT']` restricts to XPT transport files.

### Summary Structure

`summary_counts` is a nested dict: `{ component: { data_file_type: count } }` for quick inventory.

---


## Example Analyses

### BMI by Race/Ethnicity
Analyze how Body Mass Index (BMI) varies across different racial and ethnic groups.

### Blood Pressure by Gender
Compare systolic and diastolic blood pressure measurements between males and females.

### Health Metrics by Education Level
Explore how health indicators vary by educational attainment.

## Data Components

Implemented ingestion helpers (download + basic harmonization) currently cover:
- Demographics (DEMO): Includes derived labels for gender/race and survey weight variables.
- Body Measurements (BMX): Includes derived BMI categories.
- Blood Pressure (BPX): Includes derived blood pressure stages and averages.

Additional component codes are mapped internally (see `PopHealthObservatory.components`) but do **not** yet have dedicated loader convenience methods:
- Cholesterol (TCHOL)
- Diabetes (GLU)
- Dietary Intake (DR1TOT)
- Physical Activity (PAQ)
- Smoking (SMQ)
- Alcohol Use (ALQ)

Planned expansion will add per-component loaders patterned after `get_body_measures()` with column selection, semantic renaming, and derived metrics where appropriate.

### Validation Layers

1. Programmatic: `validate()` checks ingested datasets against CDC metadata (row counts & source availability).
2. Analytical (expanding): notebooks in `reproducibility/` re-derive published aggregate statistics for credibility.

### Future R Layer (Planned)

An optional R analytics layer will consume parquet outputs via Apache Arrow for advanced survey design handling. It will not rely on `reticulate`; cross-language exchange will remain file-based.

## Roadmap (Planned Enhancements)

- **Programmatic & Analytical Validation**: Enhance the `validate()` method and expand the `reproducibility/` framework.
- **Survey-Weighted Analysis**: Full support for complex survey design in statistical calculations.
- **Additional NHANES Components**: Add loaders for lab panels (lipids, glucose), dietary day 2, and activity monitors.
- **Cross-Cycle Harmonization**: Implement a registry for mapping variables across different survey cycles.
- **Adapters for Other Surveys**: Extend the framework to support other public health datasets like BRFSS.
- **Persistent Caching**: Use DuckDB or Parquet for efficient local caching of large datasets.
- **CLI Interface**: Develop a command-line tool for scripted data exports and manifest generation.

## Retrieval-Augmented Generation (RAG) Scaffolding (Experimental)

An LLM-agnostic RAG layer is scaffolded to let users experiment with question answering over
curated pesticide narrative snippets without requiring a local GPU or committing to a specific
model provider.

Key pieces:
- `pesticide_ingestion.py` – builds JSONL snippet files from raw narrative text.
- `pophealth_observatory.rag` package – lightweight embedding + retrieval utilities.
   - `RAGConfig` – paths & settings.
   - `DummyEmbedder` – deterministic CPU-only test embedder (no external downloads).
   - `SentenceTransformerEmbedder` – optional (install with `pip install pophealth-observatory[rag]`).
   - `RAGPipeline` – orchestrates loading snippets, embedding (with caching), retrieval, and prompt assembly.

Usage example (after generating a snippets JSONL using the ingestion scaffold):

```python
from pathlib import Path
from pophealth_observatory.rag import RAGConfig, RAGPipeline, DummyEmbedder

cfg = RAGConfig(
      snippets_path=Path('data/processed/pesticides/snippets_pdp_sample.jsonl'),
      embeddings_path=Path('data/processed/pesticides/emb_cache'),
)
pipeline = RAGPipeline(cfg, DummyEmbedder())
pipeline.prepare()  # loads snippets & builds or loads cached embeddings

def echo_generator(question, snippets, prompt):
      # In real usage, call your LLM API or local model here.
      return f"(stub) {len(snippets)} snippets considered"

result = pipeline.generate("What are DMP trends?", echo_generator, top_k=3)
print(result['answer'])
```

To use real embeddings:
```bash
pip install "pophealth-observatory[rag]"
```
Then substitute `DummyEmbedder()` with:
```python
from pophealth_observatory.rag import SentenceTransformerEmbedder
pipeline = RAGPipeline(cfg, SentenceTransformerEmbedder())
```

Provide any LLM by passing a generator function: `(question, snippets, prompt) -> answer`.

Future directions: FAISS-based index (already partially supported via optional dependency),
hybrid lexical + vector retrieval, snippet ranking refinement, streaming answer helpers.

## License

This project is licensed under the MIT License - see the `LICENSE` file for details.

## Contributing
Contributions are welcome. Open issues for: feature requests, new NHANES components, performance improvements, documentation gaps. Use conventional commits where possible.

### Dev Workflow
```bash
# Install pre-commit hooks (one-time setup)
pre-commit install

# Hooks run automatically on commit, or manually:
pre-commit run --all-files

# Lint
ruff check .

# Format (check) / apply
black --check .
black .

# Run tests with coverage
pytest -q
coverage run -m pytest && coverage report -m
```

### Pull Requests
- Keep changes focused
- Add/extend tests for new logic
- Update `CHANGELOG.md` if user-facing changes
- Ensure CI passes (lint, tests, build)

## Acknowledgments & Disclaimer

- Data provided by the [National Health and Nutrition Examination Survey](https://www.cdc.gov/nchs/nhanes/?CDC_AAref_Val=https://www.cdc.gov/nchs/nhanes/index.htm)
- Centers for Disease Control and Prevention (CDC) / National Center for Health Statistics (NCHS)

PopHealth Observatory is an independent open-source project and is not affiliated with, endorsed by, or sponsored by CDC or NCHS. Always review official NHANES documentation for variable definitions and analytic guidance, especially regarding complex survey design and weighting.

---

Tagline: Exploratory population health analytics from acquisition to insight.

## Try the App ▶️

Quick launch streamlit.io app:
```bash
https://pophealth-observatory.streamlit.app/
```

Recommended (faster BRFSS geographic tab):
```bash
python scripts/fetch_brfss_data.py  # one-time multi-year BRFSS snapshot -> data/processed/brfss_indicators.parquet
streamlit run apps/streamlit_app.py
```

Environment sanity check:
```bash
python -c "import pophealth_observatory, streamlit, plotly, pillow; print(pophealth_observatory.__version__)"
```

If the geographic tab is slow on first load, generate the local Parquet cache and re-run. No additional configuration required; the app auto-detects the file.

## FAQ ❓

<details>
<summary><strong>Why do some summary numbers differ from published NHANES reports?</strong></summary>
Published reports often apply full complex survey design adjustments (strata, PSU, weighting). Current helpers apply exam weights only (simplified). For publication-grade estimates, incorporate full survey design or use specialized R survey packages once parquet export arrives.
</details>

<details>
<summary><strong>Where are survey weights handled?</strong></summary>
Experimental weight selection & weighted means are in the validation/weight helpers. In the Streamlit app you can toggle "Apply Survey Weights"; this uses exam weights for rough population-level approximations.
</details>

<details>
<summary><strong>How can I speed up BRFSS indicator exploration?</strong></summary>
Run the `scripts/fetch_brfss_data.py` script to create a local multi-year Parquet cache. The app then performs in-memory filtering per indicator/year (no repeated API calls) and animation playback becomes instant.
</details>

<details>
<summary><strong>What does the 0.6.0 release change?</strong></summary>
Tabbed UI, animated BRFSS choropleth (2011–2023), local Parquet caching, indicator-level performance layer, dark/transparent logo generation, clarified exploratory positioning.
</details>

<details>
<summary><strong>How is versioning handled?</strong></summary>
Semantic versioning with conventional commits. Minor bumps (`feat:`) add features without breaking APIs; patch entries cover fixes/docs. Tags trigger automated publish workflows.
</details>

<details>
<summary><strong>Can I add a new NHANES component?</strong></summary>
Yes. Follow existing loader patterns (see `observatory.py`), implement column mapping + derived metrics, add tests, update manifests if needed, and document in the README + CHANGELOG.
</details>

<details>
<summary><strong>How do I contribute R layer functionality?</strong></summary>
Parquet exchange will be the bridge. Avoid `reticulate`; design stand-alone R code in a future `r/` directory using Arrow (`arrow::read_parquet`). Share a proposal via issue first.
</details>

<details>
<summary><strong>Are there plans for a CLI?</strong></summary>
Yes—roadmap includes scripted manifest generation and batch exports (likely `pophealth-cli`).
</details>

<details>
<summary><strong>Is the logo theming automatic?</strong></summary>
On first app run Pillow generates a dark/transparent variant if possible; falls back gracefully if Pillow missing.
</details>

<details>
<summary><strong>Is this production / regulatory grade?</strong></summary>
No. It is an exploratory toolkit for assumption checking, hypothesis generation, and early analytic prototyping. For regulated / submission contexts perform validated workflows with full survey design and audit trails.
</details>

## What's New in 0.6.0
Minor feature release focused on UI, performance, and multi-dataset exploration.

Added:
- Streamlit UI redesign with per-tab demographic filters and logo integration (dark variant auto-generated)
- Animated BRFSS choropleth (2011–2023) and year slider
- Local Parquet caching + indicator-level filtering (no repeated API calls)
- `scripts/fetch_brfss_data.py` utility for full BRFSS snapshot
- Pillow dependency for image processing

Changed:
- Tagline clarified to reflect exploratory / assumption-checking usage
- Single-year BRFSS view now subsets cached multi-year data
- Metrics hidden during animation mode to prevent misleading static stats

Removed:
- Obsolete per-year BRFSS indicator loader function (replaced by unified cached flow)

Performance:
- Eliminated sequential API loop for animated BRFSS time series
- Faster indicator selection via cached normalized DataFrame

Documentation:
- Interactive App section expanded, emphasis on generating local cache

SemVer & Tagging:
- Version bumped to 0.6.0 (`feat` scope, non-breaking). Semantic versioning automated via commit message conventions and CI.

Suggested GitHub Topics: `population-health`, `epidemiology`, `public-health`, `nutrition`, `analytics`, `data-science`, `health-disparities`, `python`, `nhanes`, `visualization`

© 2025 Paul Boys and PopHealth Observatory contributors
