## Changelog

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
