## Changelog

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
