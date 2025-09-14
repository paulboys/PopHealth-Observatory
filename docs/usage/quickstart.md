# Quick Start

```python
from pophealth_observatory.observatory import NHANESExplorer
exp = NHANESExplorer()
merged = exp.create_merged_dataset('2017-2018')
print(merged.head())
```

## Generate Manifest (XPT only, 2017-2022)
```python
manifest = exp.get_detailed_component_manifest(
    as_dataframe=True,
    year_range=("2017","2022"),
    file_types=["XPT"],
)
print(manifest['summary_counts'])
```
