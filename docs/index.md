# PopHealth Observatory

Open-source population health & nutrition analytics toolkit focused initially on NHANES.

![PopHealth Observatory Overview](assets/images/PopHealth_Observatory.png)

## Features
- Resilient multi-pattern XPT downloads
- Rich metadata manifest generation with filtering
- Convenience merging & analytic helpers
- Streamlit exploratory app
- Versioned schema for component manifests

## Install
```bash
pip install pophealth-observatory
```

## Quick Start
```python
from pophealth_observatory.observatory import NHANESExplorer
explorer = NHANESExplorer()
manifest = explorer.get_detailed_component_manifest(as_dataframe=True)
print(manifest['dataframe'].head())
```

## Project Goals
Provide transparent, reproducible access and lightweight analytics for national health & nutrition survey data.
