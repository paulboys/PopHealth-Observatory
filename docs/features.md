# Feature Status

Comprehensive breakdown of implemented vs planned capabilities.

---

## ✅ Implemented Features

### Data Acquisition
- **Multi-URL NHANES Download**: Resilient XPT file retrieval with automatic fallback patterns across CDC hosting changes
- **In-Memory Caching**: Session-level cache for downloaded component data (avoids redundant network calls)
- **Cycle/Component Mapping**: Letter suffix resolution for NHANES cycles (1999-2000 → A, 2017-2018 → J, etc.)

### Data Harmonization & Derivation
- **Demographics (DEMO)**: Download, column selection, semantic renaming, gender/race labels
- **Body Measures (BMX)**: Weight, height, BMI with categorical bins (Underweight/Normal/Overweight/Obese)
- **Blood Pressure (BPX)**: Multi-reading averages + hypertension staging (Normal/Elevated/Stage 1/Stage 2)
- **Merged Datasets**: Participant-level merge across DEMO, BMX, BPX via `participant_id`
- **Pesticide Laboratory (UPHOPM / OPD / PP)**: Multi-series file discovery, analyte harmonization (parent pesticide, metabolite class, matrix, unit), derived `log_concentration` + `detected_flag`.

### Metadata & Manifesting
- **Component Table Parsing**: Extract file listings (XPT/ZIP/FTP) from Demographics, Examination, Laboratory, Dietary, Questionnaire pages
- **Schema Versioning**: Manifest outputs include `schema_version` (semver) and `generated_at` (UTC ISO timestamp)
- **Filtering**: Year range overlap + file type subsetting
- **Local Filename Derivation**: Canonical naming with cycle years appended (e.g., `DEMO_2017_2018.xpt`)
- **Summary Aggregation**: Nested counts by component and file type
- **Manifest Persistence**: JSON serialization with optional flattened DataFrame attachment

### Analytics Helpers
- **Demographic Stratification**: Group-wise descriptive stats (count, mean, median, std, min, max) for any metric by demographic variable
- **Summary Report Generation**: Text-based participant count, age distribution, gender/race breakdowns, health metric summaries
- **Visualization**: Boxplots + bar charts for metric distributions by demographic groups (lazy matplotlib/seaborn import)
- **Survey Weight Support**: Helper methods to identify correct survey weights (`get_survey_weight`) and calculate weighted means (`calculate_weighted_mean`)

### Testing & Quality
- **Programmatic Validation**: `validate()` method to verify data integrity against official CDC metadata (URL correctness, row counts)
- **Analytical Validation Framework**: Reproducibility notebooks to validate tool output against published research (`reproducibility/`)
- **Pytest Suite**: Expanded tests (observatory coverage 30% → 81%) covering HTML parsing, manifest filtering, weighted means, merged dataset assembly, pesticide ingestion.
- **NumPy-Style Docstrings**: Comprehensive Parameter/Returns/Raises documentation across all modules
- **Lint/Format Config**: Ruff + Black with notebook exclusion, 120-char line length
- **Pre-commit Hooks**: Automated code formatting and linting with Black, Ruff, and file hygiene checks

### Documentation
- **MkDocs Site**: Material theme with navigation sections
- **Getting Started Guide**: Installation, first manifest, Streamlit app launch
- **Usage Examples**: Manifest generation, quick start snippets, data validation guide
- **API Reference**: High-level method listing (inline docstrings authoritative)
- **Copilot Instructions**: Global, Python-specific, and R-specific (future) guidance files

### Applications
- **Streamlit App**: Interactive cycle selection, metric/demographic aggregation, manifest sampling, raw data preview
- **Reproducibility Notebooks**: Executable studies that validate tool correctness against published statistics

---

## 🔧 Planned Features

### Near-Term (Q4 2025)
- **Laboratory Panel Expansion**: Lipids, glucose tolerance, inflammatory markers with dedicated loaders
- **Parquet/DuckDB Caching**: Persistent local backend for multi-cycle assemblies (optional)
- **CLI Utility**: Command-line interface for manifest generation, data download, component listing
- **Manifest Delta**: Compare manifests across dates to detect new/updated files

### Mid-Term (Q1 2026)
- **Cross-Cycle Harmonization Registry**: Variable name mapping + recoding rules for longitudinal analysis
- **Automated Data Dictionary Merger**: Extract variable documentation from PDF/HTML component pages
- **Time Trend Utilities**: Multi-cycle joins with alignment & weighting
- **Additional Components**: Dietary day 2, accelerometer, environmental exposures (dedicated loaders)
- **Retention Policy**: Configurable cache artifact cleanup (size/time-based)

### Long-Term
- **Multi-Dataset Adapters**: Unified API for BRFSS, NHIS, other public health surveys
- **Interactive Cohort Builder**: Criteria → derived dataset manifest with provenance
- **Plugin Interface**: Register custom metric calculators and derivation functions
- **Cloud Deployment Recipe**: Serverless manifest builder + cache API
- **Provenance Tracking**: Content hashing, reproducibility metadata, lineage graphs

### Quality & Tooling
- **Auto API Reference**: MkDocs integration with docstring extraction (partially—site exists, automation pending)
- **Coverage Gating**: Fail CI builds below threshold
- **Example Notebooks Gallery**: Binder/Codespaces links for interactive demos

### Stretch Ideas
- **Web UI**: Next.js + FastAPI for manifest browsing
- **ML Feature Extraction**: Standardized pipelines from harmonized datasets
- **Synthetic Data Generator**: Teaching/demo datasets with privacy preservation

---

## 📦 Component Loader Status

| Component | Code Mapped | Loader Method | Column Harmonization | Derived Metrics |
|-----------|-------------|---------------|----------------------|-----------------|
| Demographics (DEMO) | ✅ | ✅ `get_demographics_data()` | ✅ | Gender/race labels, survey weights |
| Body Measures (BMX) | ✅ | ✅ `get_body_measures()` | ✅ | BMI categories |
| Blood Pressure (BPX) | ✅ | ✅ `get_blood_pressure()` | ✅ | BP staging, averages |
| Cholesterol (TCHOL) | ✅ | ❌ | ❌ | ❌ |
| Diabetes (GLU) | ✅ | ❌ | ❌ | ❌ |
| Dietary (DR1TOT) | ✅ | ❌ | ❌ | ❌ |
| Physical Activity (PAQ) | ✅ | ❌ | ❌ | ❌ |
| Smoking (SMQ) | ✅ | ❌ | ❌ | ❌ |
| Alcohol (ALQ) | ✅ | ❌ | ❌ | ❌ |

**Legend:**
- ✅ Implemented
- ❌ Planned (code path exists for generic download via `download_data()`, but no dedicated convenience method)

---

## 🧪 RAG Pipeline Maturity

| Capability | Status | Notes |
|------------|--------|-------|
| Text ingestion | ✅ Implemented | Sentence segmentation, regex token matching |
| Snippet serialization | ✅ Implemented | JSONL format |
| Reference analyte loading | ✅ Implemented | CSV + YAML source registry |
| Embedding abstraction | ✅ Implemented | `DummyEmbedder` + `SentenceTransformerEmbedder` |
| Vector index | ✅ Implemented | In-memory NumPy cosine similarity |
| Retrieval | ✅ Implemented | Top-k snippet ranking |
| Prompt assembly | ✅ Implemented | Length-capped context formatting |
| Generator integration | ✅ Implemented | External callable pattern |
| FAISS backend | 🔧 Optional | Partial support via dependency marker |
| Hybrid retrieval (lexical+vector) | 🔧 Planned | BM25 + embedding fusion |
| Streaming answers | 🔧 Planned | Token-by-token generation helpers |
| Multi-document sources | 🔧 Planned | Expand beyond PDP excerpts |

**Legend:**
- ✅ Implemented and tested
- 🔧 Planned or partially available

---

## 🗂️ Data Exchange

| Protocol | Status | Notes |
|----------|--------|-------|
| JSONL (snippets) | ✅ Implemented | Text snippet artifacts |
| JSON (manifests) | ✅ Implemented | Component metadata |
| Parquet (cross-language) | 🔧 Planned | `shared_data/` directory reserved; Arrow interchange protocol documented |
| CSV | ❌ Not planned | Discouraged for structured exchange |
| R/Python Interop (Arrow) | 🔧 Planned | Future parquet-based exchange; no reticulate bridging |

---

## 📝 Documentation Coverage

| Artifact | Status | Location |
|----------|--------|----------|
| README | ✅ Complete | `README.md` |
| Getting Started | ✅ Complete | `docs/getting-started.md` |
| Quick Start | ✅ Complete | `docs/usage/quickstart.md` |
| Data Validation Guide | ✅ Complete | `docs/usage/validation.md` |
| Manifest Reference | ✅ Complete | `docs/usage/manifest.md` |
| API Overview | ✅ Complete | `docs/api.md` |
| Feature Status | ✅ Complete | `docs/features.md` (this page) |
| Inline Docstrings | ✅ Complete | All public functions/classes (NumPy style) |
| Copilot Instructions | ✅ Complete | `.github/copilot-instructions.md`, scoped files |
| CHANGELOG | ✅ Current | `CHANGELOG.md` |
| ROADMAP | ✅ Current | `ROADMAP.md` |
| Pesticide Biomonitoring Plan | ✅ Current | `docs/pesticide_biomonitoring_plan.md` |
| Auto API Reference | 🔧 Planned | MkDocs plugin integration pending |

---

## 🔄 Continuous Integration

| Step | Status | Notes |
|------|--------|-------|
| Lint (Ruff) | ✅ Implemented | Via pre-commit hooks and `autofix-pr` workflow |
| Format (Black) | ✅ Implemented | Via pre-commit hooks and `autofix-pr` workflow |
| Test (Pytest) | ✅ Passing | 18 tests (basic, context, RAG, validation) |
| Coverage | 🔧 Configured | `coverage` tool installed; gating not enforced |
| Build Artifacts | ✅ Implemented | `release.yml` workflow handles tagged build/publish |
| Pre-commit Hooks | ✅ Implemented | `.pre-commit-config.yaml` with Black, Ruff, etc. |
| Auto-Versioning | ✅ Implemented | `auto-version.yml` bumps version on merge to main |

---

## 🚀 Usage Readiness

| Use Case | Readiness | Requirements |
|----------|-----------|--------------|
| Explore single-cycle demographics + anthropometrics | ✅ Production-ready | Install from source or PyPI |
| Generate component file manifests with filtering | ✅ Production-ready | BeautifulSoup4 optional for HTML parsing |
| Build interactive Streamlit dashboard | ✅ Production-ready | Streamlit installed |
| Perform weighted survey analyses | 🧪 Experimental | Helper methods implemented; complex variance not yet supported |
| Cross-cycle trend analysis | ❌ Not ready | Harmonization registry + time utilities pending |
| Pesticide RAG question answering | 🧪 Experimental | Functional but API may evolve; test coverage limited |
| Export harmonized data for R analysis | 🔧 Partially ready | Parquet protocol documented; no R source yet |

**Legend:**
- ✅ Production-ready: Stable API, tested, documented
- 🧪 Experimental: Functional but evolving API
- 🔧 Partially ready: Infrastructure exists, full workflow incomplete
- ❌ Not ready: Planned but not implemented

---

**Last Updated:** 2026-04-22
**Version Coverage:** 1.0.0

For implementation timelines, see [ROADMAP.md](roadmap.md).
For change history, see [CHANGELOG.md](changelog.md).
For pesticide domain planning details, see [Pesticide Biomonitoring Plan](pesticide_biomonitoring_plan.md).
