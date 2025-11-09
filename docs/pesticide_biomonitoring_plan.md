# Pesticide Biomonitoring & External Exposure Context Expansion Plan

Version: 0.2 (Draft)
Generated: 2025-11-09
Related Instructions: `.github/copilot-instructions.md`

---
## 1. Purpose
Introduce a structured, testable ingestion + exploration layer for NHANES pesticide biomonitoring analytes and high-value external exposure context datasets (USGS agricultural use, PDP residue monitoring, TRI releases, etc.). Provide an integrated Streamlit tab enabling temporal trends, disparity views, and exploratory health linkage while preserving the project’s *exploratory, non-inferential* positioning.

## 2. High-Level Objectives
1. Internal ingestion of NHANES pesticide laboratory analytes (urine & serum) with harmonized schema.
2. Streamlit “Pesticide Biomonitoring” tab: multi-analyte trends, distribution heatmap, demographic disparities, and preliminary health correlations.
3. External context scaffolding for agricultural use and residue prevalence without premature geospatial microdata linkage claims.
4. Reusable data contracts + registry for each external source with schema versioning.
5. Transparent UI & docs disclaimers about simplified weighting, exploratory correlations, and absent complex survey design adjustments.

## 3. Scope (In / Out)
IN:
- NHANES pesticide analyte ingestion (DAP metabolites, pyrethroids, glyphosate/AMPA, organochlorines).
- Per-cycle concentration extraction + log transform + detection flag.
- Basic summary metrics: geometric mean, median, percent detected, 95th percentile.
- Demographic stratification: age range, gender, race/ethnicity, income (INDFMPIR quartiles).
- External dataset ingestion (USGS use; PDP residues) with stable schemas.
- Minimal exploratory correlation panels (e.g., analyte vs BMI / systolic BP).
- Test coverage for ingestion helpers & external source normalization.

OUT (Future Phases):
- Full survey design variance estimation (strata/PSU).
- Restricted-use geographic linkage (county/ZIP) – requires separate data access.
- Causal inference / regression modeling.
- Mixture exposure modeling (weighted quantile sum, Bayesian kernels).
- Occupation-level risk dashboards until occupational code mapping stabilized.

## 4. Phased Milestones
| Phase | Milestone | Deliverables | Success Criteria |
|-------|-----------|--------------|------------------|
| 1 | Internal analyte ingestion | `laboratory_pesticides.py`, schema docs | Load ≥8 key analytes across ≥5 cycles; no ingestion crashes |
| 2 | Biomonitoring tab (core) | New Streamlit tab with trends, heatmap, disparity chart | Tab loads <3s cached; user can select ≥4 analytes & cycles |
| 3 | External source scaffolding | `external/usgs_use.py`, `external/pdp_residues.py`, registry | USGS + PDP functions return non-empty normalized DataFrames |
| 4 | Context integration | Tab section: agricultural use overlay + commodity residue table | Overlay chart renders; detection table downloadable |
| 5 | Exploratory health linkage | BMI/BP correlation panel + disclaimers | Correlation updates on filter; clearly marked exploratory |
| 6 | Mixture / co-exposure matrix | Analyte correlation heatmap + network graph | Graph renders for ≥6 analytes; performance acceptable |

Current Progress (2025-11-09):
- Reference restructuring complete (`data/reference/` hierarchical layout).
- Core minimal analyte list established (108 analytes).
- CAS verification implemented via PubChem synonyms endpoint (78 verified, 72%).
- CDC Fourth Report classification enrichment integrated (35 classified, 32%).
- Script consolidation under `scripts/pesticides/` for maintainability.
- Backward compatibility shim (`pesticide_reference.csv`) + legacy stubs to keep tests green.
- Next active milestone: Implement laboratory ingestion module and first pass of per-cycle DataFrame assembly (Phase 1 still in progress).

## 5. Architecture Overview (Updated)
```
pophealth_observatory/
  laboratory_pesticides.py            # NHANES pesticide lab ingestion (planned)
  pesticide_context.py                # Analyte reference loading + lookup (updated with new fields)
  rag/                                # Retrieval scaffolding (future narrative integration)
  external/                           # (Planned) external contextual sources
    usgs_use.py                       # Agricultural use data (planned)
    pdp_residues.py                   # Commodity residue monitoring (planned)
    registry.py                       # Source registry & schema metadata (planned)
apps/
  streamlit_app.py                    # Will host 'Pesticide Biomonitoring' tab
scripts/
  pesticides/                         # Consolidated pesticide maintenance scripts
    build_minimal_pesticide_reference.py
    verify_minimal_reference_cas.py
    add_cdc_classifications.py
    derive_parent_pesticide_mapping.py
    discover_nhanes_pesticides.py
    curate_pesticide_reference.py
    validate_pesticide_reference.py
data/
  reference/
    minimal/                          # Core 108-analyte reference (78 CAS verified)
    classified/                       # CDC Fourth Report classifications (35 analytes)
    legacy/                           # Archived curated AI-derived reference
    discovery/                        # Raw NHANES variable discovery output
    evidence/                         # Parent mapping attempt artifacts
    config/                           # Source registry yaml
    pesticide_reference.csv           # Compatibility shim (copy of minimal)
tests/
  test_pesticide_context.py           # Reference loading & integrity
  test_laboratory_pesticides.py       # (placeholder / future expansion)
```

## 6. Internal Data Model (Updated)
We now distinguish between:

1. Analyte Reference Schema (static descriptive metadata)
2. Laboratory Measurement Schema (per-participant concentration records – forthcoming)

### 6.1 Analyte Reference Schema
| Field | Type | Description |
|-------|------|-------------|
| analyte_name | str | Canonical short name (e.g. `3-PBA`) |
| cas_rn | str | CAS Registry Number if verified |
| cas_verified_source | str | Source of CAS verification (e.g. `pubchem_api`, blank if unverified) |
| chemical_class | str | High-level chemical class (from CDC classification) |
| chemical_subclass | str | Subclass / group (if provided) |
| classification_source | str | Source of classification (e.g. `cdc_fourth_report`) |
| legacy_parent_pesticide | str | (Deprecated) formerly `parent_pesticide` – kept blank for backward compatibility |
| legacy_metabolite_class | str | (Deprecated) formerly `metabolite_class` – retained only for compatibility |
| current_measurement_flag | bool | Always True placeholder (legacy compatibility stub) |

Notes:
- Legacy fields remain as empty strings or True (for boolean) to avoid breaking existing tests/scripts.
- Classification coverage currently 35 / 108 analytes (32.4%).
- CAS verification coverage 78 / 108 analytes (72.2%).

### 6.2 Laboratory Measurement Schema (Planned)
| Field | Type | Description |
|-------|------|-------------|
| participant_id | int | NHANES SEQN identifier |
| cycle | str | Survey cycle (e.g. `2017-2018`) |
| analyte_name | str | Must join to reference analyte_name |
| matrix | str | `urine` or `serum` |
| concentration_raw | float | Reported concentration (original units) |
| unit | str | Measurement unit (e.g. `µg/L`, `ng/g lipid`) |
| log_concentration | float | ln(concentration_raw) where concentration_raw > 0 |
| detected_flag | bool | concentration_raw > 0 or > LOD (when available) |
| lod | float | Limit of detection (if parseable) |
| source_file | str | Originating XPT filename |

Removed (legacy) fields from planned measurement schema: `parent_pesticide`, `metabolite_class` (superseded by structured classification in reference layer).

## 7. External Data Contracts
### USGS Use
```
{ year:int, state_fips:str, state_name:str, pesticide_active_ingredient:str, lbs_ai:float }
```
### PDP Residues
```
{ year:int, commodity:str, analyte:str, detect_freq_pct:float, mean_detect_level:float|None, max_detect_level:float|None }
```
### TRI Releases (Future)
```
{ year:int, cas_rn:str, state:str, release_lbs:float }
```
### Sales (CA DPR - Future)
```
{ year:int, county:str, ai_name:str, lbs_sold:float }
```

## 8. Functions & Contracts (Initial)
```python
# laboratory_pesticides.py
def get_pesticide_metabolites(cycle: str) -> pd.DataFrame:
    """Return harmonized pesticide analyte DataFrame for a cycle.
    Raises ValueError for malformed cycle; returns empty DataFrame if files missing."""

# external/usgs_use.py
def fetch_usgs_state_use(year: int) -> pd.DataFrame:
    """Download or load cached agricultural pesticide use estimates (state-level)."""

def normalize_usgs(df: pd.DataFrame) -> pd.DataFrame:
    """Ensure canonical columns & types; drop rows with missing active ingredient or lbs."""

# external/pdp_residues.py
def fetch_pdp_summary(year: int) -> pd.DataFrame:
    """Retrieve commodity-level residue frequency and concentrations."""

# external/exposure_context.py
def build_exposure_context(year_range: tuple[int,int], analytes: list[str]) -> dict[str, pd.DataFrame]:
    """Aggregate external context slices keyed by source name."""
```

## 9. Streamlit Tab Responsibilities
- Inputs: analyte list, cycle range, demographics, metric type, weights toggle.
- Data pipeline: multi-cycle stack → filter → summarize → visualize.
- Visual components:
  - Line Trends: geometric mean or detection frequency over cycles.
  - Heatmap: analytes × cycles (metric).
  - Demographic Bars: exposure by race/income quartile.
  - Correlation Panel (experimental): analyte concentration vs BMI / BP.
  - Context Overlay: USGS use trend vs population biomonitoring trend.
- Export: CSV (long format: cycle, analyte, mean, n, detected_flag_rate).

## 10. Edge Cases & Handling (Updated)
| Scenario | Handling |
|----------|----------|
| Missing cycle file | Return empty DataFrame; log info message |
| Zero or negative concentrations | Exclude from log transform; keep raw |
| No analytes selected | Disable plots; show instruction message |
| Single cycle selected for trends | Show warning (need ≥2 cycles) |
| External source fetch timeout | Return empty DataFrame with schema; display caution banner |
| Weight application without weight column | Graceful fallback to unweighted aggregation |
| Detection limits unavailable in raw XPT | Placeholder `lod` null; future enhancement to parse doc pages |
| Partial classification coverage | Display "Unclassified" bucket; surface coverage % in docs |
| Partial CAS verification | Soft-fail with blank CAS; expose progress metric |

## 11. Testing Strategy
- Unit:
  - Synthetic XPT fixture ingestion (column rename, log transform correct).
  - External fetch mocked responses (schema check, normalization).
- Integration:
  - `build_exposure_context` returns dict with expected keys.
  - Streamlit tab caching (simulate first vs second call).
- Edge-case asserts: empty cycle, analyte not present in early cycles, zero-only concentration vector.

## 12. Performance Considerations
- Cache per-cycle pesticide ingestion (`@st.cache_data ttl=3600`).
- Avoid full multi-year reprocessing: incremental stacking on selection changes.
- Limit default analyte set (3–5) to keep initial render fast (<1.5s).
- Defer correlation heatmap rendering until user toggles advanced section.

## 13. Disclaimers (UI + Docs)
- “Survey weights simplified (exam weights only); no strata/PSU variance estimation.”
- “Correlations exploratory; no causal inference.”
- “External agricultural and residue data are context indicators, not direct exposure determinants.”
- “Detection frequency may shift due to analytical method changes; interpret longitudinal changes cautiously.”

## 14. PR Breakdown & Labels
| PR | Title | Label Suggestions | Summary |
|----|-------|------------------|---------|
| 1 | feat: ingest pesticide lab analytes | feat, labs | Add `get_pesticide_metabolites` + schema docs |
| 2 | feat: pesticide biomonitoring tab | feat, ui | Add new Streamlit tab (trends + heatmap) |
| 3 | feat: external USGS ingestion | feat, external-data | Add USGS module + registry entry |
| 4 | feat: PDP residue ingestion | feat, external-data | Commodity residue loader + tests |
| 5 | feat: exposure context builder | feat, orchestration | `build_exposure_context` aggregator |
| 6 | feat: disparity & correlation views | feat, analysis | Add demographic bar + simple correlations |
| 7 | feat: mixture correlation matrix | feat, analysis | Add analyte correlation heatmap + network |
| 8 | chore: docs & disclaimers update | docs | README + release notes + tab disclaimers |

## 15. Acceptance Criteria (Phase 1–2)
- Running `get_pesticide_metabolites("2017-2018")` returns DataFrame with ≥5 analytes and required columns.
- Biomonitoring tab displays multi-line trend for ≥3 analytes across ≥4 cycles.
- Heatmap renders without error; missing analyte-cycle pairs show NA.
- External USGS function returns non-empty DataFrame for a known recent year (mocked in CI).
- All new tests pass; coverage for new modules ≥80%.

## 16. Risks & Mitigations
| Risk | Impact | Mitigation |
|------|--------|------------|
| Inconsistent file naming across cycles | Missing ingestion | Build a small mapping table; fallback empty frame |
| Detection limits unavailable in raw XPT | Incomplete detection frequency | Introduce placeholder flag; future enhancement to parse doc pages |
| Large memory usage stacking many cycles | Slow UI | Limit default cycle selection; offer advanced multi-cycle toggle |
| External API schema drift | Break ingestion | Add schema validation & version pin in registry |
| Misinterpretation of exploratory correlations | Reputational risk | Prominent disclaimers + UI badge + docs alignment |

## 17. Future Enhancements (Beyond Current Plan)
- Creatinine adjustment helper for urinary analytes.
- Automated analytic method change flag (LOD tracking per cycle) + store per-cycle LOD metadata table.
- Occupational linkage (when occupation code ingestion stabilized).
- RAG integration: embedding pesticide trend narrative with snippet retrieval.
- Export Parquet snapshots for R survey design analysis.
- Classification coverage completion pass (target ≥90%).
- Semi-automated synonym expansion for unverified CAS resolution.

## 18. Implementation Order Rationale
Start with internal analyte ingestion (foundation). Progress to UI integration for immediate visible value. External data ingestion next to enrich context. Analytic overlays (disparities, correlations) deferred until baseline ingestion stable to avoid compounding debugging scopes.

## 19. Open Questions
- Should glyphosate/AMPA cycles with partial missing data be excluded or flagged? (Decision: flag rows with `partial_cycle=True`).
- Do we harmonize lipid-adjusted vs. raw serum concentrations into a single field? (Decision: keep `unit` explicit; no conversion yet.)
- Is creatinine normalization required for all urinary analytes up-front? (Decision: optional later; display raw only initially.)

## 20. Next Immediate Steps (Actionable, Updated)
1. Implement `laboratory_pesticides.get_pesticide_metabolites` with cycle validation + empty-on-miss.
2. Add tests: ingestion happy path (mock single cycle), empty cycle edge case, reference join integrity.
3. Create mapping table for XPT filenames → analyte short names (minimize hard-coded branching).
4. Add classification & CAS coverage badges to docs (auto-generated snippet optional).
5. Begin Streamlit tab scaffolding (load + simple table) behind feature flag.
6. Extend CDC classification enrichment to attempt additional matching heuristics (e.g., case-insensitive substring, hyphen normalization) – log unresolved analytes.
7. Draft external source registry skeleton (USGS & PDP placeholders returning empty typed DataFrames).

---
_This plan is a living document. Version bumped to 0.2 for reference layer restructuring & classification/CAS progress recording._
