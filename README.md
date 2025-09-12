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

## Installation

1. Clone this repository:
   ```
   git clone https://github.com/your-username/pophealth-observatory.git
   cd pophealth-observatory
   ```

2. (Optional) Create and activate a virtual environment.

3. Install required packages:
   ```
   pip install -r requirements.txt
   ```

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

Contributions are welcome. Feel free to open issues for: feature requests, dataset component additions, performance improvements, or documentation gaps. Submit a Pull Request following conventional commit style if possible.

## Acknowledgments & Disclaimer

- Data provided by the [National Health and Nutrition Examination Survey](https://www.cdc.gov/nchs/nhanes/index.htm)
- Centers for Disease Control and Prevention (CDC) / National Center for Health Statistics (NCHS)

PopHealth Observatory is an independent open-source project and is not affiliated with, endorsed by, or sponsored by CDC or NCHS. Always review official NHANES documentation for variable definitions and analytic guidance, especially regarding complex survey design and weighting.

---

Tagline: Population health analytics from acquisition to insight.

Suggested GitHub Topics: `population-health`, `epidemiology`, `public-health`, `nutrition`, `analytics`, `data-science`, `health-disparities`, `python`, `nhanes`, `visualization`
