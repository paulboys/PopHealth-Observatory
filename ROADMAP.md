# Roadmap

## Near-Term (Q4 2025)
- Laboratory panel ingestion expansion (lipids, glucose tolerance, inflammatory markers)
- Weighted analysis helper (survey design: strata, PSU, weights abstraction)
- Parquet/DuckDB local cache backend (optional persistent layer)
- CLI utility (`pophealth-observatory manifest` / `download` commands)
- Manifest delta generation (compare schema_version outputs across dates)

## Mid-Term (Q1 2026)
- Cross-cycle harmonization registry (variable name mapping + recodes)
- Automated data dictionary merger (documentation extraction from PDF/HTML)
- Time trend utilities (join multiple cycles with alignment & weighting)
- Additional components: dietary day 2, accelerometer, environmental exposures
- Configurable retention policy for cached artifacts (size/time-based)

## Long-Term
- Multi-dataset adapters (e.g., BRFSS, NHIS) under a unified acquisition API
- Interactive cohort builder (criteria -> derived dataset manifest)
- Plugin interface for custom derivations (register metric calculators)
- Cloud deployment recipe (serverless manifest builder + cache API)
- Governance: provenance tracking (hashing, reproducibility metadata)

## Quality & Tooling Enhancements
- Sphinx or MkDocs auto API reference from docstrings
- Coverage gating (fail under threshold)
- Pre-commit hooks (ruff, black, mypy optional)
- Example notebooks gallery (binder / codespaces link)

## Stretch Ideas
- Web UI (Next.js + FastAPI) for manifest browsing
- ML feature extraction pipeline from harmonized datasets
- Synthetic data generator for teaching & demos

---
Feedback and contributions welcome—open an issue or discussion to propose adjustments.
