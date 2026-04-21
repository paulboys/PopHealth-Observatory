# Getting Started

## Prerequisites
- Python 3.8+
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
```

## Streamlit App
```bash
streamlit run apps/streamlit_app.py
```
