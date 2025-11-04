# PopHealth Observatory – Setup & Usage Guide

This is the documentation site copy of the setup guide. Source of truth: root `SETUP_GUIDE.md`.

---
## 1. Prerequisites

| Requirement | Notes |
|-------------|-------|
| Python 3.10+ | Tested on 3.11 / 3.12 |
| Git | For cloning + version control |
| Optional: virtual env | `python -m venv .venv` or `conda create -n pophealth python=3.11` |
| Optional: Streamlit | For the interactive app (`pip install streamlit`) |

> R is not required. A future optional R layer will use Apache Arrow for file interchange (no Python–R bridging needed).

---
## 2. Install

```powershell
git clone https://github.com/paulboys/PopHealth-Observatory.git
cd PopHealth-Observatory
python -m venv .venv
./.venv/Scripts/Activate.ps1  # Windows PowerShell
pip install -e .[dev]
```

Minimal verification:
```powershell
pytest -q
python -c "import pophealth_observatory as p; print(p.__version__)"
```

---
## 3. Core Workflow

```python
from pophealth_observatory.observatory import NHANESExplorer

explorer = NHANESExplorer()

# Download & merge selected components
df = explorer.get_merged_dataset(cycle="2017-2018", components=["demographics", "body_measures", "blood_pressure"])

# Validate integrity against CDC metadata
report = explorer.validate(["demographics", "body_measures", "blood_pressure"])
print(report.summary())

# Weighted mean (experimental survey helper)
mean_bmi = explorer.calculate_weighted_mean(df, value_col="body_mass_index", cycle="2017-2018")
print("Weighted BMI mean:", mean_bmi)
```

---
## 4. Key Concepts

| Concept | Description | Output |
|---------|-------------|--------|
| Ingestion | Robust multi-URL NHANES file download | DataFrames |
| Harmonization | Column selection + semantic renaming + derived metrics | Standardized schema |
| Manifest | Structured inventory of component listing tables | JSON / DataFrame |
| Validation | Row count & source checks for integrity | Report object |
| Pesticide snippets | Regex-based analyte sentence windows | JSONL lines |
| RAG (experimental) | Embedding + similarity retrieval of snippet context | Ranked snippet dicts |

---
## 5. Data Outputs & Locations

| Artifact | Path | Format |
|----------|------|--------|
| Manifest JSON | `manifests/` | `.json` |
| Pesticide snippets | `data/processed/pesticides/` | `.jsonl` |
| Reference tables | `data/reference/` | `.csv` / `.yml` |
| Raw pesticide text | `data/raw/pesticides/` | `.txt` |

Parquet caching for large multi-cycle merges is planned (will locate under a future `shared_data/` or `data/processed/` subdirectory with date-stamped filenames).

---
## 6. Validation Strategy

1. Programmatic: `validate()` compares ingested data vs. CDC published metadata (rows, availability).
2. Analytical (in progress): `reproducibility/` notebooks re-derive published aggregate stats to confirm end-to-end correctness.

Edge cases handled: missing downloads → empty DataFrame; mismatch in participant IDs triggers warning; missing expected columns raise `ValueError`.

---
## 7. Survey Weights (Experimental Helpers)

Functions:
```python
explorer.get_survey_weight(cycle: str, component: str) -> str
explorer.calculate_weighted_mean(df, value_col: str, cycle: str) -> float
```

Currently covers standard 2-year weights. Planned: variance estimation & multi-cycle normalized weighting.

---
## 8. Development Tasks

```powershell
# Lint & format
ruff check .
black --check .

# Tests & coverage
pytest -q
coverage run -m pytest && coverage report -m

# Build docs
mkdocs build
```

Install/update pre-commit hooks:
```powershell
pre-commit install
pre-commit run --all-files
```

---
## 9. Contributing

1. Open an issue describing feature/bug.
2. Create a branch (`feat/<short>` or `fix/<short>`).
3. Add type hints & NumPy-style docstrings for new public functions.
4. Add tests (use `tmp_path` for filesystem side-effects). Focus on deterministic helpers.
5. Update `CHANGELOG.md` for user-facing changes.
6. Ensure CI passes before requesting review.

---
## 10. Planned R Layer (Future)

The R layer will: parse harmonized parquet outputs via `arrow`, produce advanced survey or longitudinal analyses, and optionally write derived metrics back to shared parquet. There is no S4 implementation yet; ignore any historical Bioconductor references found in older commits.

---
## 11. FAQ

| Question | Answer |
|----------|--------|
| Do I need R? | No—pure Python usage today. |
| Why JSONL for snippets? | Efficient line-wise streaming & indexing. |
| How do I regenerate a manifest? | Use `get_detailed_component_manifest` or `save_detailed_component_manifest`. |
| Can I add new analyte domains? | Follow the pattern in `pesticide_ingestion.py` (compile regex once, yield dataclass instances). |
| How do I trust weights? | Helpers are early-stage; cross-check with NHANES analytic guidance. |

---
## 12. Troubleshooting Quick Reference

| Symptom | Likely Cause | Action |
|---------|--------------|--------|
| Empty DataFrame | All URL attempts failed | Re-run with network available; inspect cycle code |
| Validation mismatch | Source metadata changed | Open issue; update scraper logic |
| No snippet matches | Patterns too strict | Inspect reference file; broaden regex tokens |
| Slow merge | Large multi-cycle join | Future caching; consider subset of cycles |

---
## 13. Ethical / Usage Notes

Not a clinical decision tool. Verify methodology when publishing. Cite NHANES appropriately.

---
## 14. Next Milestones

See `ROADMAP.md` for: harmonization registry, time trend utilities, caching backend, coverage gating.

---
## 15. License

MIT License (see `LICENSE`).

---
*Site copy last synced: 2025-11-03*
