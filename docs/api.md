# API Reference

## NHANESExplorer
High-level convenience class for NHANES workflows.

### Methods (selected)
- `get_detailed_component_manifest(...)`
- `save_detailed_component_manifest(path, **kwargs)`
- `get_demographics_data(cycle)`
- `get_body_measures(cycle)`
- `get_blood_pressure(cycle)`
- `create_merged_dataset(cycle)`
- `analyze_by_demographics(df, metric, demographic)`
- `create_demographic_visualization(df, metric, demographic)`
- `generate_summary_report(df)`

Refer to inline docstrings for full parameter details.

## Pesticide Laboratory Module

### `get_pesticide_metabolites(cycle, ref_path=None, timeout=30)`
Load and harmonize NHANES pesticide laboratory analytes for a given cycle.

**Parameters:**
- `cycle` (str): NHANES cycle in format YYYY-YYYY (e.g., '2017-2018')
- `ref_path` (Path, optional): Path to pesticide_reference.csv (defaults to data/reference/pesticide_reference.csv)
- `timeout` (int): Download timeout in seconds (default: 30)

**Returns:** DataFrame with schema:

| Column | Type | Description |
|--------|------|-------------|
| participant_id | int | NHANES SEQN identifier |
| cycle | str | Survey cycle |
| analyte_name | str | Normalized metabolite name (e.g., '3-PBA') |
| parent_pesticide | str | Parent active ingredient or chemical class |
| metabolite_class | str | Category (pyrethroid, OP, organochlorine, herbicide) |
| matrix | str | Biological matrix ('urine' or 'serum') |
| concentration_raw | float | Reported concentration (original units) |
| unit | str | Measurement unit (e.g., 'µg/L', 'ng/g lipid') |
| log_concentration | float | Natural log of concentration (NaN for ≤0) |
| detected_flag | bool | True if concentration_raw > 0 |
| source_file | str | Originating XPT filename |

Returns empty DataFrame if cycle has no pesticide data or download fails.

**Raises:**
- `ValueError`: If cycle format invalid or not in known mapping

**Example:**
```python
from pophealth_observatory import get_pesticide_metabolites

pest_df = get_pesticide_metabolites('2017-2018')
print(pest_df[['participant_id', 'analyte_name', 'concentration_raw']].head())
```

**Data Sources:**
Attempts to download from multiple NHANES pesticide file series:
- UPHOPM: Pyrethroids, Herbicides, & Organophosphorus Metabolites
- OPD: Organophosphate Dialkyl Phosphate Metabolites
- PP: Priority Pesticides - Current Use

**Supported Cycles:** 1999-2000 through 2021-2022 (availability varies by analyte)

**Schema Notes (0.7.0):**
- `log_concentration` uses natural log; values <= 0 yield NaN to avoid math domain errors.
- `detected_flag` is a simple > 0 heuristic; future versions may incorporate LOD/LOQ thresholds when published reference limits are integrated.
- `parent_pesticide` enables grouping analytes by active ingredient lineage for aggregate exposure metrics.
- Output remains wide-format per participant per analyte; long-format convenience helper planned.

**Test Coverage (0.7.0):** Ingestion paths validated via unit tests for empty cycles, synthetic datasets, and edge-case metabolite naming (commas, hyphenation, mixed case).

### `load_pesticide_reference(ref_path=None)`
Load curated pesticide analyte reference metadata.

**Parameters:**
- `ref_path` (Path, optional): Path to reference CSV

**Returns:** DataFrame with columns:
- `analyte_name`, `parent_pesticide`, `metabolite_class`, `cas_rn`, `typical_matrix`, `unit`, `first_cycle_measured`, `last_cycle_measured`, etc.

Returns empty DataFrame if file not found.

**Example:**
```python
from pophealth_observatory import load_pesticide_reference

ref_df = load_pesticide_reference()
pyrethroids = ref_df[ref_df['metabolite_class'] == 'Pyrethroid']
```

## BRFSSExplorer
State-level health indicator access from CDC BRFSS dataset.

### Methods

#### `get_obesity_data(year=None)`
Retrieve state-level adult obesity prevalence (BMI ≥ 30).

**Parameters:**
- `year` (int, optional): Target year. If None, uses latest available.

**Returns:** DataFrame with columns:
- `year`, `state`, `state_name`, `value`, `low_ci`, `high_ci`, `sample_size`, `data_source`, `class_name`, `question`

**Raises:** `ValueError` if specified year not found.

**Example:**
```python
brfss = BRFSSExplorer()
obesity_data = brfss.get_obesity_data(year=2022)
```

#### `get_indicator(class_name, question, year=None)`
Retrieve any BRFSS health indicator by class and question.

**Parameters:**
- `class_name` (str): BRFSS indicator class (e.g., "Physical Activity")
- `question` (str): Exact question text from BRFSS dataset
- `year` (int, optional): Target year. If None, uses latest available.

**Returns:** DataFrame with same structure as `get_obesity_data()`

**Raises:** `ValueError` if specified year not found for this indicator.

**Example:**
```python
physical_activity = brfss.get_indicator(
    class_name='Physical Activity',
    question='Percent of adults aged 18 years and older who engage in no leisure-time physical activity'
)
```

#### `list_available_indicators()`
List all unique class/question combinations in BRFSS dataset.

**Returns:** DataFrame with columns `['class', 'question']`

**Example:**
```python
indicators = brfss.list_available_indicators()
print(indicators[indicators['class'] == 'Obesity / Weight Status'])
```

#### `summary(df)`
Generate summary statistics for a BRFSS indicator DataFrame.

**Parameters:**
- `df` (DataFrame): Output from `get_obesity_data()` or `get_indicator()`

**Returns:** dict with keys:
- `count`, `mean_value`, `min_value`, `max_value`, `year`, `class_name`, `question`

**Example:**
```python
obesity_data = brfss.get_obesity_data()
stats = brfss.summary(obesity_data)
print(f"Mean: {stats['mean_value']:.1f}%")
```

### Configuration

**BRFSSConfig**
- `base_url` (str): CDC API endpoint (default: "https://data.cdc.gov/resource/hn4x-zwk7.json")
- `timeout` (int): HTTP timeout in seconds (default: 30)
- `default_limit` (int): API result limit (default: 5000)

**BRFSSExplorer constructor:**
- `config` (BRFSSConfig, optional): Configuration object
- `session` (requests.Session, optional): Reusable HTTP session
- `enable_cache` (bool): In-memory caching (default: True)

### Data Source
- **Dataset**: CDC BRFSS Nutrition, Physical Activity, and Obesity (hn4x-zwk7)
- **Documentation**: https://data.cdc.gov/Nutrition-Physical-Activity-and-Obesity
- **Coverage**: State-level health indicators for all 50 states + DC

See `docs/usage/brfss.md` for detailed usage examples.
