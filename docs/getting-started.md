# Getting Started

## Prerequisites
- Python 3.10+
- pip / virtual environment recommended
- Quarto (required)
- SciClaw 0.2.8+ (required for scientific authoring workflows)

Validate toolchain before running workflows:
```bash
quarto check
sciclaw --version
```

## Installation
```bash
pip install pophealth-observatory
```

From source (development):
```bash
git clone https://github.com/paulboys/PopHealth-Observatory.git
cd PopHealth-Observatory
pip install -e .[dev,docs]
```

## First Manifest
```python
from pophealth_observatory.observatory import NHANESExplorer
exp = NHANESExplorer()
manifest = exp.get_detailed_component_manifest(as_dataframe=True)
print(manifest['summary_counts'])
manifest['dataframe'].head()
```

## Quick Validation
```python
report = exp.validate('2017-2018', ['demographics', 'body_measures'])
print(report['status'])  # 'PASS' | 'WARN' | 'FAIL'
```

## Survey-Weighted Mean
```python
df = exp.create_merged_dataset('2017-2018')
result = exp.calculate_weighted_mean(df, variable='bmi')  # weight auto-detected
print(f"Weighted mean BMI: {result['weighted_mean']:.2f}")
```

## Next Steps
- [Quickstart usage](usage/quickstart.md)
- [Validation report structure](usage/validation.md)
- [Component manifest filtering](usage/manifest.md)
- [BRFSS state-level indicators](usage/brfss.md)
- [Logging configuration](usage/logging.md)
- [Full API reference](api.md)

## Streamlit App
```bash
streamlit run apps/streamlit_app.py
```
