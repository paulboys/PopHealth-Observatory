## Changelog

### Version Bump Convention (Automated via CI/CD)
- **MAJOR** (`x.0.0`): Breaking changes — commit message contains `[major]` or `BREAKING CHANGE`
- **MINOR** (`0.x.0`): New features — commit message starts with `feat` or contains `[minor]` or `[feature]`
- **PATCH** (`0.0.x`): Bug fixes, docs, refactoring — all other commits to main
- Automatic version tagging triggers PyPI publish via existing `publish.yml` workflow

### [Unreleased]
Added
- (placeholder)

### [0.7.0] - 2025-11-08

#### Summary
Version 0.7.0 focuses on **robustness, reliability, and extensibility**. This release introduces foundational infrastructure for pesticide biomonitoring analysis while dramatically improving code quality, test coverage (90% → 96%), and system stability.

#### Added
- **Pesticide Laboratory Ingestion Module** (`laboratory_pesticides.py`):
  - `get_pesticide_metabolites(cycle)`: Multi-component NHANES pesticide file discovery & ingestion with flexible URL fallback
  - `load_pesticide_reference()`: Curated reference metadata (CAS RN, matrix, cycle availability)
  - Derived metrics: log-transformed concentration (`log_concentration`) and detection flag (`detected_flag`)
  - Coverage: 99% (108/109 statements tested)

- **Data Validation Framework** (`validation.py`):
  - `run_validation()`: Programmatic validation against official CDC sources
  - `validate_component()`: Component-level URL and row count verification
  - `_scrape_cdc_component_metadata()`: Automated CDC page parsing for validation
  - Coverage: 100% (120/120 statements tested)

- **Comprehensive Test Expansion**:
  - 35+ new micro-tests across 3 modules
  - `TestDownloadXPTFlexible`: URL fallback logic, network failures (6 tests)
  - `TestScrapeCDCMetadata`: CDC page parsing robustness (9 tests)
  - `TestValidateComponent`: Component validation logic (17 tests)
  - `TestRunValidation`: Multi-component pipeline (4 tests)
  - Observatory edge cases: HTML parsing, year filtering, manifest exceptions (6 tests)

#### Improved
- **Test Coverage**: Overall project 90% → 96% (+6 percentage points)
  - `laboratory_pesticides.py`: 83% → 99% (+16%)
  - `validation.py`: 31% → 100% (+69%)
  - `observatory.py`: 85% → 86% (+1%)
- **Code Quality**: All pre-commit hooks passing (black, ruff, trailing whitespace, line endings)
- **Documentation**: Added comprehensive pesticide biomonitoring roadmap (`docs/pesticide_biomonitoring_plan.md`)

#### Fixed
- **Streamlit Application**: Line length compliance (E501) in help strings and filter summaries
- **Repository Hygiene**:
  - Resolved F841 unused variable warnings
  - Fixed B007 unused loop variable names
  - Added B904 exception chaining for better error context
  - Corrected E712 boolean comparison style

#### Changed
- Version bump to 0.7.0 (minor feature release; non-breaking API additions)
- README updated with v0.7.0 feature highlights and coverage improvements
- Feature status page updated to reflect pesticide ingestion availability

#### Technical Details
- Total Tests: 144 (up from 109)
- All Passing: ✅
- Execution Time: ~35 seconds
- No new required dependencies
- No performance regressions

#### Notes
- Establishes foundation for future pesticide biomonitoring UI (Phase 2, planned v0.8.0)
- Fully backward-compatible with v0.6.x
- See `docs/release-notes/0.7.0.md` for complete release documentation
- See `docs/pesticide_biomonitoring_plan.md` for detailed roadmap

### [0.6.0] - 2025-11-05
Added
- Streamlit application UI redesign: tab-specific NHANES demographic filters (age, gender, race, weights) isolated per analytical context (cross-sectional, trends, bivariate).
- Animated BRFSS choropleth time series (2011–2023) with in-memory playback and year slider/play controls.
- Local BRFSS Parquet caching (`scripts/fetch_brfss_data.py`) eliminating repeated large remote pulls; single-year view now filters cached multi-year dataset.
- Performance caching layers (raw, indicator-filtered, aggregated) for BRFSS data access; removal of per-year API loops for animation.
- Logo integration with dark/transparent variant generation (Pillow) replacing prior microscope emoji branding.
- `get_asset_path()` helper and automatic dark logo processor.

Changed
- Tagline clarified to emphasize exploratory analysis rather than finalized scientific visualization.
- Geographic tab metrics hidden during animation to avoid misleading static summaries.
- Single-year BRFSS selection now uses cached filtered DataFrame (no API call) for instant response.
- Removed obsolete `load_brfss_indicator()` function (redundant after unified caching approach).
- Added Pillow (`pillow>=10.0.0`) to core dependencies for runtime logo image transformation.

Performance
- Eliminated 13 sequential API calls in animated BRFSS time series; replaced with vectorized in-memory filtering.
- Reduced latency for year switching (BRFSS) via indicator-level cached normalization.

Documentation
- Internal UI text updated (tagline) to align with intended business exploratory & assumption‑checking use cases.

Notes
- Non-breaking feature expansion; minor version bump per convention (`feat` scope, no API removal).

### [0.5.0] - 2025-11-04
Added
- BRFSSExplorer module (`pophealth_observatory/brfss.py`) introducing first multi-dataset adapter (CDC BRFSS state-level indicators).
  - `get_obesity_data(year=None)` convenience method.
  - Generic `get_indicator(class_name, question, year=None)` for arbitrary BRFSS metrics.
  - `list_available_indicators()` discovery helper.
  - `summary(df)` quick statistics.
  - In-memory caching minimizes repeat API calls; resilient error handling (network failures, invalid years).
- Comprehensive test suite (`tests/test_brfss_explorer.py`) covering caching, indicator retrieval variants, error paths, normalization logic (mocked requests; no live dependency).

Changed
- Exported `BRFSSExplorer` via package `__init__.py` to public API.
- Refactored `notebooks/nhanes_explorer_demo.ipynb` Section 10 to use new module instead of inline prototype code.
- Expanded README Multi-Dataset Support section with BRFSS quick start examples.

Documentation
- New guide `docs/usage/brfss.md` (rationale, quick start, indicator catalog, visualization patterns, caching & error handling).
- Extended `docs/api.md` with BRFSSExplorer method signatures and examples.

Notes
- Establishes geographic prevalence complement to NHANES clinical measures; aligns with roadmap "Multi-dataset adapters" milestone now in progress.

### [0.4.1] - 2025-11-03
Docs
- Refactored `SETUP_GUIDE.md` into concise human-focused Python setup & usage guide (removed legacy Bioconductor / agent content, added validation + survey weight sections, troubleshooting, FAQ).
- Updated `README.md` to surface programmatic vs analytical validation layers and experimental survey weight helpers.
- Updated `docs/features.md` to: (a) remove duplicated legacy sections, (b) rephrase reticulate prohibition to planned Arrow-based R/Python interop, (c) align feature list with current capabilities.

Added
- Clear articulation of validation layers (programmatic integrity checks vs analytical reproducibility notebooks).
- Survey weight helper documentation (auto weight selection + weighted mean) flagged as experimental.

Changed
- Harmonized terminology ("Programmatic Validation" / "Analytical Validation") across docs.
- Navigation guidance now points users to `SETUP_GUIDE.md` for environment bootstrap.

Notes
- Version number already at 0.4.0 in `pyproject.toml`; this patch entry records documentation evolution preceding any subsequent functional changes.

### [0.4.0] - 2025-11-02
Added
- Programmatic validation framework: `validate()` integrating with new `validation.py` (row count checks, URL/source availability, component-level statuses) plus dataclass-backed report representation.
- Survey weight helpers: `get_survey_weight()` and `calculate_weighted_mean()` for early-stage weighted analysis.
- Reproducibility scaffold: `reproducibility/` directory and initial notebook for analytical validation layer.
- Composite GitHub Action for Python setup (dependency install consolidation across workflows).
- Documentation: validation concept sections, weighting explanation, roadmap/status updates.

Changed
- Consolidated CI workflows (lint/autofix, test matrix, publish) reducing duplication and replacing experimental reusable workflow attempt with composite action.
- Enhanced README and feature docs to distinguish ingestion/harmonization vs validation responsibilities.
- Strengthened multi-URL download resilience (broader pattern list, clearer diagnostics).

Fixed
- Resolved auto-version workflow failure caused by `sed` incompatibility on Windows; replaced with pure Python edit approach.

Notes
- Marks maturation from ingestion-only (0.2.x) to integrity + credibility focus (validation layers).

### [0.3.0] - 2025-10-15
Added
- Expanded pesticide snippet ingestion reliability (regex boundary refinements, analyte normalization improvements) preparing for RAG retrieval accuracy.
- Initial analytical validation planning notes and doc placeholders (pre-implementation of full reproducibility notebook).
- Streamlined manifest generation filters (year overlap + file type) aligned with forthcoming harmonization registry design.

Changed
- Refactored observatory internals for clearer separation of I/O vs transformation helpers (foundation for validation integration in 0.4.0).
- Improved naming & docstring consistency (NumPy style adoption near complete across public API).

Removed
- Legacy or redundant exploratory notebook code paths superseded by formalized helpers (soft deprecation documented, not breaking API).

Notes
- Transitional release laying groundwork for validation & weighting; final pre-validation architectural cleanup.

### [0.2.1] - 2025-11-02
Fixed
- Constrained setuptools to `<70.0` in build requirements to avoid Metadata-Version 2.4 fields that PyPI doesn't support yet (PEP 639 compatibility issue)
- Enabled successful PyPI package publishing for version 0.2.1

Added
- Automated version bumping workflow (`.github/workflows/auto-version.yml`) with semantic commit message parsing

### [0.2.0] - 2025-09-14
Added
- Experimental RAG scaffolding (`pophealth_observatory.rag`): config, dummy embedder, sentence-transformer embedder, cosine index, pipeline orchestration, test coverage.
- Optional dependency group `[rag]` with `sentence-transformers` and optional `faiss-cpu`.
- README documentation for RAG usage and example code.
 - Comprehensive NumPy-style docstrings added across ingestion, context, and RAG modules (documentation-only change).

Changed
- Improved pesticide analyte suggestion normalization (robust matching for names like `p,p'-DDE`).
- Excluded Jupyter notebooks from Ruff lint (`extend-exclude`) temporarily to unblock CI (will refactor / clean notebooks later for compliance).

Notes
- This is an experimental feature; API may evolve before a stable 1.x release.
 - Retrieval prompt truncation behavior documented (max_chars parameter in `_format_prompt`).

### [0.1.4] - 2025-09-14
Added
- Changelog, README badges & version exposure (`__version__`).
- CI enhancement plan (pending) to verify wheel install before publish.

Changed
- Lint/style conformance (wrapped long lines, import ordering, modern typing).

### [0.1.3] - 2025-09-14
Changed
- Version bump to capture manifest filtering and docs adjustments.
- Adjusted GitHub Pages deploy condition to bypass environment protection failure.

### [0.1.2] - 2025-09-13
Added
- Manifest schema version & generation timestamp.
- Multi-URL fallback, retries, caching improvements.
- Expanded component parsing & filtering (year range, file types).

Changed
- Repository restructuring (apps/, manifests/, examples/, notebooks/).

### [0.1.1] - 2025-09-12
Added PyPI publish automation (token-based) and lint/coverage enhancements in CI.

### [0.1.0] - 2025-09-12
Initial release.

Added:
- Core `PopHealthObservatory` base class
- `NHANESExplorer` subclass with demographics, body measures, blood pressure components
- Caching layer for downloaded XPT files
- Derived metrics (BMI categories, BP categories, averages)
- Demographic stratification helper (`analyze_by_demographics`)
- Visualization helper with lazy matplotlib/seaborn import
- Summary report generator
- Basic pytest suite
- Packaging (pyproject + setup.py) and build artifacts
- GitHub Actions CI (test matrix + tagged build artifacts)

Planned (not in this release): weighted analyses, additional components, cross-cycle harmonization registry, alternative dataset adapters, DuckDB/Parquet caching, CLI interface.

---

Guiding Principle: Reproducible, modular population health analytics from acquisition to insight.
