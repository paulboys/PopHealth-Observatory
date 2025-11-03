# Roadmap

## Near-Term (Q4 2025)
Status legend: (planned) not yet started; (in progress); (done)

- Laboratory panel ingestion expansion (lipids, glucose tolerance, inflammatory markers) (planned)
- Weighted analysis helper (survey design: strata, PSU, weights abstraction) (planned)
- Parquet/DuckDB local cache backend (optional persistent layer) (planned)
- CLI utility (`pophealth-observatory manifest` / `download` commands) (planned)
- Manifest delta generation (compare schema_version outputs across dates) (planned)

## Mid-Term (Q1 2026)
- Cross-cycle harmonization registry (variable name mapping + recodes) (planned)
- Automated data dictionary merger (documentation extraction from PDF/HTML) (planned)
- Time trend utilities (join multiple cycles with alignment & weighting) (planned)
- Additional components: dietary day 2, accelerometer, environmental exposures (planned)
- Configurable retention policy for cached artifacts (size/time-based) (planned)

## Long-Term
- Multi-dataset adapters (e.g., BRFSS, NHIS) under a unified acquisition API (planned)
- Interactive cohort builder (criteria -> derived dataset manifest) (planned)
- Plugin interface for custom derivations (register metric calculators) (planned)
- Cloud deployment recipe (serverless manifest builder + cache API) (planned)
- Governance: provenance tracking (hashing, reproducibility metadata) (planned)

## Quality & Tooling Enhancements
- Sphinx or MkDocs auto API reference from docstrings (partially—MkDocs site exists; auto API not yet implemented) (planned)
- Coverage gating (fail under threshold) (planned)
- Pre-commit hooks (ruff, black, mypy optional) (planned)
- Example notebooks gallery (binder / codespaces link) (planned)

## Stretch Ideas
- Web UI (Next.js + FastAPI) for manifest browsing (planned)
- ML feature extraction pipeline from harmonized datasets (planned)
- Synthetic data generator for teaching & demos (planned)

---
Feedback and contributions welcome—open an issue or discussion to propose adjustments.
