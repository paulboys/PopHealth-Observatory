# Manifest Reference

The manifest produced by `get_detailed_component_manifest` includes:

| Key | Description |
| --- | ----------- |
| schema_version | Version of manifest schema |
| generated_at | UTC ISO timestamp |
| detailed_year_records | Raw grouped rows per component |
| summary_counts | Aggregated counts by component & file type |
| component_count | Number of component pages processed |
| total_file_rows | Row count after filtering |
| dataframe (optional) | Flattened DataFrame if requested |

## Filtering Logic
- Year range keeps rows whose interval overlaps the requested span.
- File types are matched against upper-cased set (e.g. `XPT`, `ZIP`).

## Example
```python
m = exp.get_detailed_component_manifest(as_dataframe=True,
                                        file_types=["XPT"],
                                        year_range=("2015","2022"))
print(m['total_file_rows'])
```
