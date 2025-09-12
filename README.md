# NHANES Data Explorer

A comprehensive tool for exploring health and nutrition metrics from the National Health and Nutrition Examination Survey (NHANES) data.

## Overview

This project provides a Python-based toolkit for downloading, processing, and analyzing NHANES data across different demographic groups and survey cycles. NHANES is a program of studies designed to assess the health and nutritional status of adults and children in the United States.

## Features

- **Easy Data Access**: Download NHANES data directly from CDC servers
- **Data Processing**: Clean and process raw NHANES data into analysis-ready formats
- **Demographic Analysis**: Analyze health metrics across various demographic groups
- **Visualization**: Create publication-quality visualizations of health trends
- **Multi-cycle Support**: Compare data across different NHANES survey cycles
- **Summary Reporting**: Generate comprehensive summary reports of health metrics

## Installation

1. Clone this repository:
   ```
   git clone https://github.com/your-username/nhanes-data-explorer.git
   cd nhanes-data-explorer
   ```

2. Install required packages:
   ```
   pip install -r requirements.txt
   ```

## Quick Start

```python
from nhanes_explorer import NHANESExplorer

# Initialize the explorer
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

## Data Components

The explorer includes access to the following NHANES components:
- Demographics (DEMO)
- Body Measurements (BMX)
- Blood Pressure (BPX)
- Cholesterol (TCHOL)
- Diabetes (GLU)
- Dietary Intake (DR1TOT)
- Physical Activity (PAQ)
- Smoking (SMQ)
- Alcohol Use (ALQ)

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Acknowledgments

- Data provided by the [National Health and Nutrition Examination Survey](https://www.cdc.gov/nchs/nhanes/index.htm)
- Centers for Disease Control and Prevention (CDC)
- National Center for Health Statistics (NCHS)
