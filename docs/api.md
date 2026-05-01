# API Reference

This page documents the public Python API exposed by `pophealth_observatory`.
For narrative usage examples, see [Quickstart](usage/quickstart.md), [Validation](usage/validation.md),
[Manifest](usage/manifest.md), [BRFSS](usage/brfss.md), and [Logging](usage/logging.md).

> Import paths shown below use the canonical submodule form (e.g.
> `from pophealth_observatory.observatory import NHANESExplorer`). Root-level imports
> from `pophealth_observatory` continue to work for backwards compatibility but emit a
> `DeprecationWarning` and will be removed no earlier than version `2.0.0` (target
> date `2027-06-30`).

---

## Module map

| Module | Responsibility |
|--------|----------------|
| `pophealth_observatory.observatory` | `PopHealthObservatory`, `NHANESExplorer` (high-level NHANES workflows) |
| `pophealth_observatory.brfss` | `BRFSSExplorer`, `BRFSSConfig` (state-level CDC indicators) |
| `pophealth_observatory.laboratory_pesticides` | Pesticide analyte ingestion + reference loading |
| `pophealth_observatory.pesticide_ingestion` | Sentence-window snippet extraction (JSONL) |
| `pophealth_observatory.pesticide_context` | Reference + SciClaw evidence enrichment loaders |
| `pophealth_observatory.validation` | CDC metadata validation report types + `run_validation` |
| `pophealth_observatory.nhanes_data_access` | Resilient multi-URL XPT download helpers |
| `pophealth_observatory.nhanes_manifest_service` | Component manifest builder (HTML scrape + structuring) |
| `pophealth_observatory.nhanes_transforms` | `harmonize_*` column-rename + derived metric helpers |
| `pophealth_observatory.nhanes_analysis_service` | Descriptive stats, plots, summary report |
| `pophealth_observatory.logging_config` | `configure_logging`, `log_with_fallback` |
| `pophealth_observatory.core.protocols` | `DataProvider`, `AnalysisRunner`, `ReportGenerator`, `IndicatorProvider` |
| `pophealth_observatory.rag` | Experimental retrieval-augmented snippet pipeline |

---

## `pophealth_observatory.observatory`

### `class NHANESExplorer(PopHealthObservatory)`

High-level convenience class for cycle-aware NHANES download, harmonization, manifest
generation, validation, and survey-weighted analysis. Composition over inheritance is
supported via optional protocol adapters.

**Constructor**

```python
NHANESExplorer(data_provider=None, analysis_runner=None, report_generator=None)
```

- `data_provider` (`DataProvider`, optional) — overrides the default `NHANESDataProviderAdapter`.
- `analysis_runner` (`AnalysisRunner`, optional) — overrides the default `NHANESAnalysisAdapter`.
- `report_generator` (`ReportGenerator`, optional) — overrides the default `NHANESReportAdapter`.

#### Component download & harmonization

| Method | Returns |
|--------|---------|
| `get_demographics_data(cycle="2017-2018")` | DataFrame with `participant_id`, `age_years`, `gender_label`, `race_ethnicity_label`, `interview_weight`, `exam_weight`, etc. |
| `get_body_measures(cycle="2017-2018")` | DataFrame with `weight_kg`, `height_cm`, `bmi`, `waist_cm`, derived `bmi_category` |
| `get_blood_pressure(cycle="2017-2018")` | DataFrame with `systolic_bp_*`, `diastolic_bp_*`, `avg_systolic`, `avg_diastolic` plus derived `bp_category` |
| `create_merged_dataset(cycle="2017-2018")` | DEMO + BMX + BPX merged on `participant_id` |

Column naming follows the harmonized schema produced by
[`nhanes_transforms`](#pophealth_observatorynhanes_transforms). Use `df.columns` to
inspect what is available for a given cycle.

#### Manifest helpers

```python
get_detailed_component_manifest(
    components=None,
    as_dataframe=False,
    year_range=None,
    file_types=None,
    force_refresh=False,
    schema_version=None,
) -> dict
save_detailed_component_manifest(path: str, **manifest_kwargs) -> str
```

Build (and optionally persist) an enriched JSON manifest by parsing the public NHANES
component listing pages. When `as_dataframe=True`, the returned dict also includes a
`dataframe` key with one row per file. See [Manifest usage](usage/manifest.md).

#### Survey-weighted analysis

```python
get_survey_weight(components: list[str]) -> str
```
Returns the harmonized column name of the appropriate sample weight for the chosen
components, following CDC guidance (`dietary_day1_weight` › `exam_weight` ›
`interview_weight`).

```python
calculate_weighted_mean(
    data: pd.DataFrame,
    variable: str,
    weight_var: str | None = None,
    min_weight: float = 0,
) -> dict
```
Compute a weighted mean. When `weight_var is None`, the method auto-detects the first
of `exam_weight`, `interview_weight`, `dietary_day1_weight` present on `data`.

Returns a dict with keys: `weighted_mean`, `unweighted_mean`, `n_obs`, `sum_weights`,
`variable`, `weight_var`. Raises `ValueError` if no weight column is available or no
rows satisfy `min_weight`.

#### Validation

```python
validate(cycle: str, components: list[str]) -> dict
```

Programmatically validate downloaded NHANES data against the CDC component pages.
Delegates to `run_validation` (see the validation section below). Returns a dict
produced by `ValidationReport.to_dict()`. See [Validation usage](usage/validation.md).

#### Descriptive helpers (delegated to `nhanes_analysis_service`)

```python
analyze_by_demographics(df, metric, demographic) -> pd.DataFrame
create_demographic_visualization(df, metric, demographic) -> None
generate_summary_report(df) -> str
```

#### Cycle suffix helpers

`NHANESExplorer.cycle_suffix_map` maps cycles such as `"2017-2018"` to the file letter
suffix `"J"`. The internal helper `_get_cycle_suffix(cycle)` wraps that lookup and
raises `ValueError` for unsupported cycles.

### `class PopHealthObservatory`

Base class. Holds `cycle_suffix_map`, `available_cycles`, `components` (component →
NHANES code), and the `data_cache`. Exposes `get_data_url(cycle, component)` and
`download_data(cycle, component)`.

---

## `pophealth_observatory.brfss`

### `class BRFSSConfig`

Dataclass configuring the BRFSS API client.

| Field | Default | Purpose |
|-------|---------|---------|
| `base_url` | `https://data.cdc.gov/resource/hn4x-zwk7.json` | Socrata BRFSS endpoint |
| `timeout` | `30` | Per-request timeout (seconds) |
| `default_limit` | `150000` | API row limit |

### `class BRFSSExplorer`

```python
BRFSSExplorer(config: BRFSSConfig | None = None,
              session: requests.Session | None = None,
              enable_cache: bool = True)
```

| Method | Description |
|--------|-------------|
| `get_obesity_data(year=None)` | State-level obesity prevalence (BMI ≥ 30). Latest year if `year is None`. |
| `get_indicator(class_name, question, year=None)` | Fetch any BRFSS indicator by class + question. |
| `list_available_indicators()` | DataFrame of unique `(class, question)` combinations. |
| `summary(df)` | Dict: `count`, `mean_value`, `min_value`, `max_value`, plus `year`, `class_name`, `question`. |

`enable_cache=True` caches responses keyed on the request parameters for the lifetime
of the instance. See [BRFSS usage](usage/brfss.md).

---

## `pophealth_observatory.laboratory_pesticides`

### `get_pesticide_metabolites(cycle, ref_path=None, timeout=30) -> pd.DataFrame`

Load and harmonize NHANES pesticide laboratory analytes for a single cycle. Returns
an empty DataFrame if no pesticide files exist for that cycle or all download
candidates fail.

**Output schema**

| Column | Type | Description |
|--------|------|-------------|
| `participant_id` | int | NHANES `SEQN` |
| `cycle` | str | Survey cycle |
| `analyte_name` | str | Normalized metabolite name (e.g. `3-PBA`) |
| `parent_pesticide` | str | Parent active ingredient or chemical class |
| `metabolite_class` | str | Pyrethroid / OP / organochlorine / herbicide / … |
| `matrix` | str | `urine` or `serum` |
| `concentration_raw` | float | Reported concentration (original units) |
| `unit` | str | e.g. `µg/L`, `ng/g lipid` |
| `log_concentration` | float | Natural log; ≤0 → `NaN` |
| `detected_flag` | bool | `concentration_raw > 0` |
| `source_file` | str | Originating XPT filename |

Raises `ValueError` if `cycle` is not in the supported map.

```python
from pophealth_observatory.laboratory_pesticides import get_pesticide_metabolites
pest_df = get_pesticide_metabolites("2017-2018")
```

### `get_pesticide_panel(cycles, ref_path=None, timeout=30) -> pd.DataFrame`

Concatenate `get_pesticide_metabolites(...)` across multiple cycles. Useful for
building a multi-cycle panel for trend analysis.

### `load_pesticide_reference(ref_path=None) -> pd.DataFrame`

Load the curated reference CSV (`data/reference/pesticide_reference.csv`) describing
analyte → parent pesticide → class lineage with CAS RNs and matrix/unit metadata.

### `load_analyte_code_map(map_path=None) -> dict[str, str]`

Load the URX*/LBX* NHANES variable code → analyte-name lookup used during
harmonization.

---

## `pophealth_observatory.pesticide_ingestion`

### `class Snippet`

Dataclass produced by snippet generation.

| Field | Type | Notes |
|-------|------|-------|
| `cas_rn` | str | CAS Registry Number |
| `analyte_name` | str | Matched analyte |
| `parent_pesticide` | str | Parent compound |
| `source_id` | str | Identifier used in output filename |
| `source_path` | str | Path of source text file |
| `position` | int | Sentence index of the central match |
| `sentence_window` | list[str] | Surrounding sentence window |

`Snippet.to_dict()` returns a JSON-serializable dict; `text` is the joined window.

### Functions

| Function | Description |
|----------|-------------|
| `segment_sentences(text)` | Lightweight sentence segmenter. |
| `generate_snippets(sentences, window=1, source_id="sample")` | Yield `Snippet` instances for each analyte match using compiled regex patterns. |
| `write_snippets(snippets, dest)` | Stream snippets to JSONL (one JSON object per line, UTF-8). Returns the number of records written. |
| `ingest_text_file(path, source_id="sample", window=1)` | Convenience: read → segment → generate → write. Returns the output JSONL path. |
| `read_text(path)` | Robust UTF-8 text reader. |
| `ensure_dirs()` | Ensure `data/raw/pesticides/` and `data/processed/pesticides/` exist. |

---

## `pophealth_observatory.pesticide_context`

### Dataclasses

- `PesticideAnalyte` — normalized reference entry (`analyte_name`, `cas_rn`, `matrix`,
  `unit`, `cycle_first_measured`, `cycle_last_measured`, `chemical_class`, …).
- `EvidenceCitation` — bibliographic citation for a SciClaw enrichment record.
- `EvidenceStatement` — claim with direction, confidence, and supporting citations.
- `EvidenceEnrichmentRecord` — CAS-keyed enrichment bundle (statements + health
  endpoints).

### Functions

| Function | Description |
|----------|-------------|
| `load_analyte_reference(path=REFERENCE_CSV) -> list[PesticideAnalyte]` | Resolve and load the reference CSV (cascading lookup: explicit path → workspace `data/reference` → packaged data). |
| `load_evidence_enrichment() -> dict[str, EvidenceEnrichmentRecord]` | Load SciClaw evidence enrichment JSONL keyed by CAS RN. |
| `merge_reference_with_enrichment(ref, enrichment) -> list[PesticideAnalyte]` | Attach enrichment records to analytes by CAS RN. |

---

## `pophealth_observatory.validation`

Dataclasses describing validation results and the runner used by `NHANESExplorer.validate`.

### Dataclasses

| Class | Fields |
|-------|--------|
| `ValidationCheck` | `name`, `status` (`PASS`/`WARN`/`FAIL`), `details`, `expected`, `actual` |
| `ComponentValidation` | `component`, `status`, `checks: list[ValidationCheck]` |
| `ValidationReport` | `cycle`, `status`, `components: list[ComponentValidation]`; helpers `to_dict()`, `__str__()` |

### Functions

```python
validate_component(explorer, cycle, component, downloaded_data=None) -> ComponentValidation
run_validation(explorer, cycle, components) -> ValidationReport  # noqa
```

`run_validation` is the entry point used by `NHANESExplorer.validate`; it scrapes the
public CDC component page (with a browser User-Agent), compares the expected file URL
pattern, and records each check on the report. See [Validation usage](usage/validation.md)
for full report structure and examples.

---

## `pophealth_observatory.nhanes_data_access`

```python
build_nhanes_xpt_url_patterns(cycle, component, letter, base_url, alt_base_url) -> list[str]
try_download_xpt(url_patterns, timeout_seconds=30) -> tuple[pd.DataFrame | None, str | None, list[str]]
```

`try_download_xpt` returns `(df, success_url, errors)` — a non-`None` `df` indicates
a successful XPT parse. `errors` accumulates per-URL failure messages even when one
URL ultimately succeeds.

---

## `pophealth_observatory.nhanes_manifest_service`

Helpers used by `NHANESExplorer.get_detailed_component_manifest`.

| Function | Description |
|----------|-------------|
| `normalize_year_span(year_text)` | Normalize cycle text to `YYYY_YYYY`. |
| `derive_local_filename(remote_url, year_norm)` | Canonical local XPT filename. |
| `classify_data_file(href, label)` | Return one of `XPT`, `ZIP`, `FTP`, `OTHER`. |
| `extract_size(label)` | Extract size token from anchor text (e.g. `12.3 MB`). |
| `parse_component_table(html, page_url)` | Parse the component listing table into structured rows. |
| `fetch_component_page(component_name, cache)` | Cached HTTP GET for a component listing page. |
| `build_detailed_component_manifest(...)` | Full manifest builder with optional `as_dataframe`, `year_range`, `file_types`, `force_refresh`, custom `cache`/`fetch_page`/`parse_table` injection points. |

---

## `pophealth_observatory.nhanes_transforms`

Pure transformation helpers used by the explorer methods.

| Function | Adds / renames |
|----------|----------------|
| `harmonize_demographics(demo_df)` | `SEQN→participant_id`, `RIDAGEYR→age_years`, gender / race labels, weight columns |
| `harmonize_body_measures(bmx_df)` | `BMXBMI→bmi`, `BMXWT→weight_kg`, `BMXHT→height_cm`, derived `bmi_category` |
| `harmonize_blood_pressure(bp_df)` | systolic/diastolic readings, `avg_systolic`/`avg_diastolic`, derived `bp_category` |

All three are no-ops on empty DataFrames and only rename columns that are present.

---

## `pophealth_observatory.nhanes_analysis_service`

| Function | Description |
|----------|-------------|
| `analyze_by_demographics(df, metric, demographic)` | Grouped descriptive statistics (`Count`, `Mean`, `Median`, `Std Dev`, `Min`, `Max`). |
| `create_demographic_visualization(df, metric, demographic)` | Boxplot + mean bar chart (matplotlib + seaborn; gracefully no-ops if unavailable). |
| `generate_summary_report(df)` | Multi-line text summary covering demographics and selected health metrics. |

---

## `pophealth_observatory.logging_config`

```python
configure_logging(level: str | None = None, stream: TextIO | None = None) -> logging.Logger
log_with_fallback(logger, level, message, fallback_print=True) -> None
```

`configure_logging` is idempotent and is invoked automatically on package import. The
log level can be set via the `POPHEALTH_LOGLEVEL` environment variable (defaults to
`INFO`). `log_with_fallback` mirrors the message to stdout if logging has not yet been
initialised — used for transitional compatibility while removing legacy `print` calls.
See [Logging usage](usage/logging.md).

---

## `pophealth_observatory.core.protocols`

`typing.Protocol` definitions used for dependency injection on `NHANESExplorer`:

| Protocol | Required members |
|----------|------------------|
| `DataProvider` | `get_data_url`, `download_data` |
| `AnalysisRunner` | `create_merged_dataset`, `analyze_by_demographics` |
| `ReportGenerator` | `generate_summary_report`, `validate` |
| `IndicatorProvider` | `get_indicator`, `summary` |

Default implementations live in `pophealth_observatory.core.nhanes_adapters` and
`pophealth_observatory.core.nhanes_reporting_adapters`.

---

## `pophealth_observatory.rag` (experimental)

Retrieval-augmented snippet pipeline. The optional dependencies are installed via the
`rag` extra:

```bash
pip install -e .[rag]
```

> FAISS is skipped on Windows via the dependency marker; the in-memory cosine-similarity
> `VectorIndex` (NumPy) is always available.

### `class RAGConfig`

| Field | Default | Purpose |
|-------|---------|---------|
| `snippets_path` | — | JSONL snippet input |
| `embeddings_path` | — | Directory for cached embeddings |
| `model_name` | `all-MiniLM-L6-v2` | sentence-transformers model id |
| `cache` | `True` | Reuse embeddings on disk if present |
| `enable_evidence_enrichment` | `True` | Attach SciClaw evidence to retrieved snippets |

`RAGConfig.ensure_dirs()` creates `embeddings_path`.

### `class RAGPipeline`

```python
RAGPipeline(config: RAGConfig, embedder: BaseEmbedder)
```

| Method | Description |
|--------|-------------|
| `prepare()` | Load snippets and build/load the embedding index. |
| `retrieve(question, top_k=5) -> list[dict]` | Return ordered snippet dicts for a query. |
| `generate(question, generator, top_k=5) -> str` | Build a prompt via `_format_prompt` and delegate text generation to `generator(question, snippets, prompt) -> str`. |

`generator` has type `GeneratorFn = Callable[[str, list[dict], str], str]` — keeps the
LLM/back-end pluggable.

### Embedders (`pophealth_observatory.rag.embeddings`)

- `BaseEmbedder` — abstract base with `encode(texts) -> np.ndarray` and
  `dimension` property.
- `DummyEmbedder` — deterministic hash-based embedder for tests.
- `SentenceTransformerEmbedder` — wraps a HuggingFace sentence-transformers model.

### Vector index (`pophealth_observatory.rag.index`)

`VectorIndex` is a NumPy-backed cosine-similarity index with `query(query_vec, top_k)`,
`save(root)`, `load(root)`. The companion `save_metadata` / `load_metadata` functions
persist the snippet text + metadata alongside the vectors.

---

## Deprecation surface

Importing the following names directly from `pophealth_observatory` emits a
`DeprecationWarning` (use the canonical submodule path instead):

| Deprecated | Use instead |
|------------|-------------|
| `from pophealth_observatory import PopHealthObservatory` | `from pophealth_observatory.observatory import PopHealthObservatory` |
| `from pophealth_observatory import NHANESExplorer` | `from pophealth_observatory.observatory import NHANESExplorer` |
| `from pophealth_observatory import BRFSSExplorer` | `from pophealth_observatory.brfss import BRFSSExplorer` |
| `from pophealth_observatory import get_pesticide_metabolites` | `from pophealth_observatory.laboratory_pesticides import get_pesticide_metabolites` |
| `from pophealth_observatory import get_pesticide_panel` | `from pophealth_observatory.laboratory_pesticides import get_pesticide_panel` |
| `from pophealth_observatory import load_pesticide_reference` | `from pophealth_observatory.laboratory_pesticides import load_pesticide_reference` |

Removal will not happen before version `2.0.0` (target `2027-06-30`).
