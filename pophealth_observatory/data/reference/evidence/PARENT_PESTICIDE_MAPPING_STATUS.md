# Parent Pesticide Mapping - Current Status

## Problem Statement

The AI-generated `pesticide_reference.csv` file contained unverified `parent_pesticide` mappings. This file has been renamed to `pesticide_reference_legacy_ai.csv` and should **NOT** be used for analysis without explicit acknowledgment of its untrusted provenance.

## Remediation Plan Status

### ✅ Completed Steps

1. **Legacy File Quarantine**: Renamed `pesticide_reference.csv` → `pesticide_reference_legacy_ai.csv`
2. **Guard Logic Implemented**: `pesticide_context.py` now raises `ValueError` when attempting to load the legacy AI file without `allow_legacy_ai=True`
3. **Extraction Script Created**: `scripts/derive_parent_pesticide_mapping.py` implements documentation-based extraction

### ❌ Blocked: NHANES Codebook URLs Unavailable

The CDC NHANES website has reorganized, and **direct codebook HTML pages are no longer accessible** via programmatic URL patterns. All tested URL formats return 404 or generic "Page Not Found" responses:

**Tested URL Patterns (all failed)**:
- `https://wwwn.cdc.gov/Nchs/Nhanes/{cycle}/{file}.htm`
- `https://wwwn.cdc.gov/Nchs/Nhanes/{cycle}/Lab/{file}.htm`
- `https://wwwn.cdc.gov/nchs/data/nhanes/{cycle}/labdoc/{file}.htm`

**Examples**:
- PSTPOL_D (2005-2006 pooled pesticides): ❌ Not found
- L24PP_C (2003-2004 urinary pesticides): ❌ Not found

## Current Workaround: Manual Verification Required

Until CDC restores programmatic access to codebook documentation, `parent_pesticide` mappings must be verified manually.

### Manual Verification Process

1. **Locate NHANES Documentation**:
   - Visit: https://wwwn.cdc.gov/nchs/nhanes/search/datapage.aspx
   - Search for the data file name (e.g., "L24PP_C" for urinary pesticides)
   - Download the associated **Data Documentation** (usually a PDF or DOC file)

2. **Extract Parent Relationships**:
   Look for language patterns in the "Laboratory Method" or "Analyte Description" sections:
   - "X is a metabolite of [pesticide name]"
   - "Common metabolite of [pesticide A], [pesticide B], ..."
   - "Non-specific biomarker of organophosphate pesticides"
   - "Persistent environmental metabolite of DDT"

3. **Classification**:
   - `specific_parent`: One-to-one mapping (e.g., TCPy → Chlorpyrifos)
   - `multi_parent_family`: Multiple specific parents listed (e.g., 3-PBA → Permethrin, Cypermethrin)
   - `persistent_metabolite`: Environmental breakdown product (e.g., p,p'-DDE → DDT)
   - `non_specific_family`: Family-level only (e.g., DAP metabolites → "Organophosphates")
   - `parent_compound`: Parent itself measured directly
   - `unmapped`: No explicit relationship stated in documentation

4. **Record Evidence**:
   For each verified mapping, document:
   - Source document title and URL
   - Exact quote containing the relationship
   - Classification type
   - Date verified

### Template for Manual Entries

```jsonl
{
  "analyte_name": "URX3PBA",
  "variable_name": "URX3PBA",
  "data_file_name": "L24PP_C",
  "earliest_cycle": 2003,
  "source_url": "https://wwwn.cdc.gov/Nchs/Nhanes/2003-2004/L24PP_C.htm",
  "source_document": "Laboratory Procedure Manual, L24PP_C.pdf",
  "mapping_type": "multi_parent_family",
  "parent_pesticides": ["Permethrin", "Cypermethrin", "Deltamethrin", "Cyfluthrin"],
  "evidence_sentences": [
    "3-phenoxybenzoic acid (3-PBA) is a common urinary metabolite of several pyrethroid insecticides including permethrin, cypermethrin, deltamethrin, and cyfluthrin."
  ],
  "verification_date": "2025-11-08",
  "verified_by": "manual"
}
```

## Next Steps

1. **Monitor CDC for URL restoration**: Periodically test if codebook HTML pages become available again
2. **Alternative data sources**:
   - Check if NHANES provides a structured API or JSON endpoint for variable metadata
   - Contact CDC/NCHS to request programmatic access documentation
   - Explore R package `nhanesA` to see if it has metadata extraction capabilities
3. **Build manual verification dataset**: Create `parent_pesticide_mapping_manual.jsonl` with verified entries
4. **Merge with curated reference**: Once sufficient coverage achieved, generate `pesticide_reference_verified.csv`

## Usage Until Verified File Exists

To use existing functionality while parent mappings are unverified:

```python
from pophealth_observatory.pesticide_context import load_analyte_reference

# This will now RAISE an error
# analytes = load_analyte_reference()  # ValueError!

# Must explicitly acknowledge untrusted data
analytes = load_analyte_reference(
    path=Path("data/reference/pesticide_reference_legacy_ai.csv"),
    allow_legacy_ai=True  # Required flag
)
```

**Warning will be displayed**:
```
Attempted to load AI-generated legacy file: data/reference/pesticide_reference_legacy_ai.csv
This file contains unverified parent_pesticide mappings.
To use this file for historical reproduction only, set allow_legacy_ai=True.
Preferred: Use pesticide_reference_verified.csv (run derive_parent_pesticide_mapping.py first).
```

## Status Summary

| Component | Status |
|-----------|--------|
| Legacy file quarantine | ✅ Complete |
| Guard logic in code | ✅ Complete |
| Automated extraction script | ✅ Created (blocked by CDC URLs) |
| NHANES codebook access | ❌ Not available |
| Manual verification process | 📋 Documented |
| Verified reference file | ❌ Not yet created |

**Recommendation**: Proceed with manual verification for high-priority analytes (e.g., those measured across multiple cycles or in active research). Defer comprehensive mapping until CDC restores programmatic documentation access or provides an alternative API.
