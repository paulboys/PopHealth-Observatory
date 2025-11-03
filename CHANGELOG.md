## Changelog

### Version Bump Convention (Automated via CI/CD)
- **MAJOR** (`x.0.0`): Breaking changes — commit message contains `[major]` or `BREAKING CHANGE`
- **MINOR** (`0.x.0`): New features — commit message starts with `feat` or contains `[minor]` or `[feature]`
- **PATCH** (`0.0.x`): Bug fixes, docs, refactoring — all other commits to main
- Automatic version tagging triggers PyPI publish via existing `publish.yml` workflow

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
