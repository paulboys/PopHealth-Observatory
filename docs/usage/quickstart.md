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

## Pesticide Laboratory Quick Start
```python
from pophealth_observatory.laboratory_pesticides import (
    get_pesticide_metabolites,
    load_pesticide_reference,
)

ref = load_pesticide_reference()
df = get_pesticide_metabolites("2017-2018")

print(f"Reference analytes: {len(ref)}")
print(df[["participant_id", "analyte_name", "concentration_raw"]].head())
```

## Logging Controls

See `usage/logging.md` for logger setup, `LOGLEVEL`, and migration-era fallback print behavior.
