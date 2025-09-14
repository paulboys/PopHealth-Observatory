# PopHealth Observatory

Actionable population health & nutrition analytics: acquisition → harmonization → stratified insights → visualization.

PopHealth Observatory is an open-source toolkit for exploring population health and nutrition metrics using publicly available survey microdata (current focus: NHANES). It streamlines secure data acquisition, cleaning, demographic stratification, trend analysis, and visualization—designed for reproducible epidemiologic and health disparities research.

## Overview

The project provides a Python-based framework for ingesting, harmonizing, and analyzing public health survey data (initially NHANES). NHANES (National Health and Nutrition Examination Survey) is a nationally representative program assessing the health and nutritional status of the U.S. population. PopHealth Observatory abstracts common data wrangling and analytic patterns so you can focus on questions, not boilerplate.

## Features

- **Automated Acquisition**: Pull SAS transport (.XPT) files directly from CDC endpoints
- **Caching Layer**: Avoid redundant downloads within a session
- **Schema Harmonization**: Standardized variable selection & human-readable labels
- **Derived Metrics**: BMI categories, blood pressure categories, summary anthropometrics
- **Demographic Stratification**: Rapid group-wise descriptive statistics
- **Cycle Comparison**: Simple cross-cycle trend scaffolding
- **Visualization Suite**: Boxplots, distributions, stratified means, interactive widgets
- **Extensible Architecture**: Plug in additional NHANES components or other survey sources
- **Reproducible Reporting**: Programmatic summary report generation
- **Rich Metadata Manifest**: Enumerate all component table rows with standardized schema & filtering

## Installation

## Repository Structure

```
├─ apps/                       # End-user applications (Streamlit, future CLI wrappers)
│  └─ streamlit_app.py         # Interactive NHANES exploration UI
├─ examples/                   # Simple executable usage examples
│  └─ demo.py                  # Former main.py demonstration script
├─ manifests/                  # Generated manifest JSON artifacts (not source code)
│  └─ component_files_manifest_...json
├─ notebooks/                  # Exploratory & development Jupyter notebooks
│  ├─ nhanes_demographics_link_finder.ipynb
│  ├─ nhanes_explorer_demo.ipynb
│  ├─ nhanes_url_testing.ipynb
│  ├─ observatory_exploration.ipynb
│  └─ README.md
├─ pophealth_observatory/      # Library source (core observatory & explorer classes)
├─ tests/                      # Automated tests (unit / integration)
├─ requirements.txt            # Python dependencies
├─ pyproject.toml / setup.py   # Packaging configuration
├─ CHANGELOG.md                # Versioned change log
└─ README.md                   # Project documentation (this file)
```

### Apps Directory

`apps/streamlit_app.py` provides an interactive interface to:
- Select NHANES cycle and view merged demographics + clinical metrics
- Slice metrics by demographic categories with summary statistics
- Inspect laboratory and questionnaire file inventory via manifest sampling
- Preview raw merged data (first N rows) for QA

Future additions may include:
- CLI data export tool (e.g., `apps/nhanes_export.py`)
- Dashboard variants (e.g., multi-page Streamlit or FastAPI backend)


### From Source (Development)

1. Clone:
   ```
   git clone https://github.com/paulboys/PopHealth-Observatory.git
   cd PopHealth-Observatory
   ```
2. (Recommended) Create & activate a virtual environment.
3. Install in editable mode with dev extras:
   ```
   pip install -e .[dev]
   ```

### (Future) From PyPI
Once published:
```
pip install pophealth-observatory
```
Until then, use the source install above.

## Quick Start

```python
from pophealth_observatory import NHANESExplorer

# Initialize the explorer (NHANES-focused implementation)
explorer = NHANESExplorer()

# Download and merge demographics, body measures, and blood pressure data
data = explorer.create_merged_dataset('2017-2018')

# Generate a summary report
print(explorer.generate_summary_report(data))

# Analyze BMI by race/ethnicity
bmi_by_race = explorer.analyze_by_demographics(data, 'bmi', 'race_ethnicity_label')
print(bmi_by_race)

# Create visualization
explorer.create_demographic_visualization(data, 'bmi', 'race_ethnicity_label')
```

## Interactive App (Streamlit)

An interactive exploration UI is provided via `streamlit_app.py`.

Run locally:
```bash
streamlit run streamlit_app.py
```

Features:
- Select NHANES cycle
- Choose metric & demographic for aggregation (mean / median / count)
- View summary table & bar chart
- Inspect laboratory & questionnaire manifest sample (schema-aligned)
- Optional raw data preview (first 500 rows)

Requirements: `streamlit` (installed via `requirements.txt`).


## Metadata Manifest (NHANES Component Tables)

The explorer can build a structured manifest of NHANES component listing tables (Demographics, Examination, Laboratory, Dietary, Questionnaire) including:

Fields per row:
- `year_raw`, `year_normalized` (e.g. `2005_2006`)
- `data_file_name`
- `doc_file_url`, `doc_file_label`
- `data_file_url`, `data_file_label`
- `data_file_type` (XPT | ZIP | FTP | OTHER)
- `data_file_size` (e.g. `3.4 MB` if present)
- `date_published`
- `original_filename`, `derived_local_filename` (cycle-year appended for XPT when possible)

Schema control:
- Top-level manifest includes `schema_version` (semantic version; current: `1.0.0`) and `generated_at` (UTC ISO timestamp).
- Future structural changes will increment the manifest schema version (MAJOR = breaking, MINOR = additive, PATCH = non-breaking fixes).

### Generate a Manifest

```python
from pophealth_observatory.observatory import NHANESExplorer
e = NHANESExplorer()
manifest = e.get_detailed_component_manifest(
   components=['Demographics','Laboratory'],
   file_types=['XPT'],            # optional filter
   year_range=('2005','2014'),    # inclusive overlap on normalized spans
   as_dataframe=True              # attach pandas DataFrame
)
print(manifest['schema_version'], manifest['total_file_rows'])
print(manifest['summary_counts'])
df = manifest['dataframe']
print(df.head())
```

### Persist to JSON

```python
e.save_detailed_component_manifest(
   'nhanes_manifest.json',
   file_types=['XPT','ZIP'],
   year_range=('1999','2022')
)
```

### Overriding Schema Version (Advanced)

You can pass a custom `schema_version` if producing a forked or experimental layout:

```python
e.get_detailed_component_manifest(schema_version='1.1.0-exp')
```

### Caching & Refresh

- Component listing HTML pages are cached in-memory per session.
- Use `force_refresh=True` to re-fetch a component page.

### Filtering Logic

- `year_range=('2005','2010')` keeps any row whose normalized span overlaps that interval.
- `file_types=['XPT']` restricts to XPT transport files.

### Summary Structure

`summary_counts` is a nested dict: `{ component: { data_file_type: count } }` for quick inventory.

---


## Example Analyses

### BMI by Race/Ethnicity
Analyze how Body Mass Index (BMI) varies across different racial and ethnic groups.

### Blood Pressure by Gender
Compare systolic and diastolic blood pressure measurements between males and females.

### Health Metrics by Education Level
Explore how health indicators vary by educational attainment.

## Data Components (Current Bundle)

The current implementation exposes the following NHANES components:
- Demographics (DEMO)
- Body Measurements (BMX)
- Blood Pressure (BPX)
- Cholesterol (TCHOL)
- Diabetes (GLU)
- Dietary Intake (DR1TOT)
- Physical Activity (PAQ)
- Smoking (SMQ)
- Alcohol Use (ALQ)

## Roadmap (Planned Enhancements)

- Additional NHANES components (lab panels, dietary day 2, activity monitors)
- Weighted analyses helper utilities (survey design integration)
- Cross-cycle variable harmonization registry
- BRFSS / other public health dataset adapters
- Optional DuckDB / Parquet caching for large multi-cycle assemblies
- CLI interface for scripted batch exports

## License

This project is licensed under the MIT License - see the `LICENSE` file for details.

## Contributing
Contributions are welcome. Open issues for: feature requests, new NHANES components, performance improvements, documentation gaps. Use conventional commits where possible.

### Dev Workflow
```bash
# Lint
ruff check .

# Format (check) / apply
black --check .
black .

# Run tests with coverage
pytest -q
coverage run -m pytest && coverage report -m
```

### Pull Requests
- Keep changes focused
- Add/extend tests for new logic
- Update `CHANGELOG.md` if user-facing changes
- Ensure CI passes (lint, tests, build)

## Acknowledgments & Disclaimer

- Data provided by the [National Health and Nutrition Examination Survey](https://www.cdc.gov/nchs/nhanes/?CDC_AAref_Val=https://www.cdc.gov/nchs/nhanes/index.htm)
- Centers for Disease Control and Prevention (CDC) / National Center for Health Statistics (NCHS)

PopHealth Observatory is an independent open-source project and is not affiliated with, endorsed by, or sponsored by CDC or NCHS. Always review official NHANES documentation for variable definitions and analytic guidance, especially regarding complex survey design and weighting.

---

Tagline: Population health analytics from acquisition to insight.

Suggested GitHub Topics: `population-health`, `epidemiology`, `public-health`, `nutrition`, `analytics`, `data-science`, `health-disparities`, `python`, `nhanes`, `visualization`

© 2025 Paul Boys and PopHealth Observatory contributors
