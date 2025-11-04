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
