Data directory layout.

Current subdirectories:
- `raw/pesticides/` : source narrative text excerpts (sample only).
- `processed/pesticides/` : generated snippet JSONL and embedding cache (after running ingestion/RAG prep).
- `reference/` : curated pesticide analyte CSV and source registry YAML.

Planned additions:
- `shared_data/` : Parquet artifacts for future R/Python cross-language exchange (not yet implemented).

Guidelines:
- Do not commit large (>10MB) Parquet or intermediate artifacts.
- Reference files must remain UTF-8 encoded.
- Generated embedding arrays should be cached locally but may be excluded from version control if size grows.
