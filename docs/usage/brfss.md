# BRFSS Integration

The `BRFSSExplorer` class provides access to state-level health indicators from the CDC's Behavioral Risk Factor Surveillance System (BRFSS) dataset. This complements NHANES national-level data with geographic health metrics.

## Why BRFSS?

**NHANES** provides detailed clinical measurements and demographics but deliberately omits geographic identifiers (state, county) from public datasets due to privacy constraints. Small sample sizes combined with demographic details could enable participant re-identification.

**BRFSS** fills this gap by providing state-level prevalence estimates for similar health metrics. While BRFSS lacks the clinical depth of NHANES (no blood samples, physical examinations), it offers:

- State-level geographic granularity
- Larger sample sizes per state
- Consistent annual data collection
- Complementary health behaviors (diet, physical activity, screening rates)

## Quick Start

### Basic Obesity Data

```python
from pophealth_observatory import BRFSSExplorer

# Initialize explorer
brfss = BRFSSExplorer()

# Get latest obesity data for all states
obesity_data = brfss.get_obesity_data()

# Display summary
stats = brfss.summary(obesity_data)
print(f"Year: {stats['year']}")
print(f"States: {stats['count']}")
print(f"Mean obesity rate: {stats['mean_value']:.1f}%")
print(f"Range: {stats['min_value']:.1f}% - {stats['max_value']:.1f}%")
```

### Specific Year

```python
# Get 2022 obesity data
obesity_2022 = brfss.get_obesity_data(year=2022)
```

## Generic Indicator Access

Use `get_indicator()` to fetch any BRFSS health metric:

```python
# Physical inactivity
physical_inactivity = brfss.get_indicator(
    class_name='Physical Activity',
    question='Percent of adults aged 18 years and older who engage in no leisure-time physical activity'
)

# Fruit consumption
fruit_consumption = brfss.get_indicator(
    class_name='Fruits and Vegetables',
    question='Percent of adults who report consuming fruit less than 1 time daily'
)

# Diabetes prevalence (if available in dataset)
diabetes = brfss.get_indicator(
    class_name='Diabetes',
    question='Percent of adults aged 18 years and older who have been told they have diabetes',
    year=2022
)
```

## Discovering Available Indicators

List all unique class/question combinations:

```python
indicators = brfss.list_available_indicators()
print(f"Total indicators: {len(indicators)}")
print(indicators)

# Filter by class
obesity_indicators = indicators[indicators['class'] == 'Obesity / Weight Status']
print(obesity_indicators)
```

## Geographic Visualization

Create choropleth maps with Plotly:

```python
import plotly.express as px

# Get obesity data
obesity_data = brfss.get_obesity_data()

# Rename 'value' to 'obesity_rate' for clarity
plot_data = obesity_data.rename(columns={'value': 'obesity_rate'})

# Create map
fig = px.choropleth(
    plot_data,
    locations='state',
    locationmode='USA-states',
    color='obesity_rate',
    color_continuous_scale='YlOrRd',
    range_color=(20, 40),
    scope="usa",
    labels={'obesity_rate': 'Obesity Prevalence (%)'},
    title=f"Adult Obesity Prevalence by State ({plot_data['year'].iloc[0]})",
    hover_data={'state': True, 'state_name': True, 'obesity_rate': ':.1f'}
)
fig.show()
```

## Data Structure

All BRFSS methods return DataFrames with standardized columns:

| Column | Type | Description |
|--------|------|-------------|
| `year` | int | Survey year |
| `state` | str | Two-letter state abbreviation |
| `state_name` | str | Full state name |
| `value` | float | Indicator value (e.g., prevalence percentage) |
| `low_ci` | float | Lower 95% confidence interval |
| `high_ci` | float | Upper 95% confidence interval |
| `sample_size` | int | Sample size for estimate |
| `data_source` | str | "CDC BRFSS hn4x-zwk7" |
| `class_name` | str | BRFSS indicator class |
| `question` | str | Full question text |

## Caching

`BRFSSExplorer` uses in-memory caching to avoid repeated API calls:

```python
# First call fetches from API
obesity_data = brfss.get_obesity_data()  # Network request

# Second call uses cache
obesity_data_cached = brfss.get_obesity_data()  # Instant

# Disable caching
brfss_no_cache = BRFSSExplorer(enable_cache=False)
```

Cache keys are unique per indicator/year combination, so different indicators don't interfere:

```python
obesity = brfss.get_obesity_data()  # Cached separately
activity = brfss.get_indicator(...)  # Different cache entry
```

## Error Handling

Network failures and missing data return empty DataFrames with warnings:

```python
# Invalid year
try:
    data = brfss.get_obesity_data(year=1999)  # Not in dataset
except ValueError as e:
    print(f"Error: {e}")  # "Year 1999 not found..."

# Nonexistent indicator (returns empty DataFrame + warning)
data = brfss.get_indicator(
    class_name='Nonexistent',
    question='Invalid question'
)
# Prints: "⚠ No data found for class='Nonexistent'..."
print(data.empty)  # True
```

## Configuration

Customize API behavior with `BRFSSConfig`:

```python
from pophealth_observatory.brfss import BRFSSExplorer, BRFSSConfig

config = BRFSSConfig(
    timeout=60,  # Longer timeout for slow connections
    default_limit=10000  # Increase limit for future larger datasets
)

brfss = BRFSSExplorer(config=config)
```

## Common Indicators

### Obesity & Weight Status
- "Percent of adults aged 18 years and older who have obesity"
- "Percent of adults aged 18 years and older who are overweight"

### Physical Activity
- "Percent of adults aged 18 years and older who engage in no leisure-time physical activity"
- "Percent of adults meeting aerobic physical activity guidelines"
- "Percent of adults meeting muscle strengthening guidelines"

### Nutrition
- "Percent of adults who report consuming fruit less than 1 time daily"
- "Percent of adults who report consuming vegetables less than 1 time daily"
- "Percent of adults who report drinking sugar-sweetened beverages at least 1 time daily"

### Chronic Conditions (if available)
- "Percent of adults aged 18 years and older who have been told they have diabetes"
- "Percent of adults ever told they have high blood pressure"

## Combining NHANES and BRFSS

National trends from NHANES + state-level patterns from BRFSS:

```python
from pophealth_observatory import NHANESExplorer, BRFSSExplorer

# National average from NHANES
nhanes = NHANESExplorer()
nhanes_data = nhanes.create_merged_dataset('2017-2018')
national_obesity = (nhanes_data['bmi'] >= 30).mean() * 100
print(f"National obesity rate (NHANES): {national_obesity:.1f}%")

# State-level from BRFSS
brfss = BRFSSExplorer()
state_obesity = brfss.get_obesity_data(year=2017)
print(f"\nState-level obesity rates (BRFSS {state_obesity['year'].iloc[0]}):")
print(state_obesity[['state_name', 'value']].head())
```

## API Reference

### BRFSSExplorer

#### Methods

- **`get_obesity_data(year=None)`**
  - Returns: DataFrame with state-level adult obesity prevalence
  - Parameters: `year` (int, optional) - specific year, defaults to latest

- **`get_indicator(class_name, question, year=None)`**
  - Returns: DataFrame for any BRFSS indicator
  - Parameters:
    - `class_name` (str) - BRFSS class (e.g., "Physical Activity")
    - `question` (str) - exact question text
    - `year` (int, optional) - specific year, defaults to latest

- **`list_available_indicators()`**
  - Returns: DataFrame with columns ['class', 'question']
  - Use to discover valid class/question combinations

- **`summary(df)`**
  - Returns: dict with count, mean, min, max, year, class, question
  - Parameters: `df` - DataFrame from get_obesity_data() or get_indicator()

## Data Source

- **Dataset**: CDC BRFSS Nutrition, Physical Activity, and Obesity
- **API**: https://data.cdc.gov/resource/hn4x-zwk7.json
- **Documentation**: https://data.cdc.gov/Nutrition-Physical-Activity-and-Obesity
- **Update Frequency**: Annual
- **Coverage**: All 50 U.S. states + DC, territories (varies by year)

## Limitations

- **Survey-based**: Self-reported data (no clinical measurements)
- **State-level only**: No county or individual-level data
- **Annual snapshots**: Not continuous monitoring
- **Variable availability**: Not all indicators available for all years
- **Question wording**: Exact question text required for `get_indicator()`

## Best Practices

1. **Always check summary statistics** before visualization to catch data issues
2. **Use list_available_indicators()** to discover valid class/question pairs
3. **Enable caching** (default) for interactive analysis
4. **Handle empty DataFrames** gracefully (network failures, missing years)
5. **Document year** in reports - BRFSS questions evolve over time

## Examples

See `notebooks/nhanes_explorer_demo.ipynb` Section 10 for complete geographic analysis workflow.
