# Legacy Pesticide Reference Placeholder

This directory is required by `tests/test_packaging_integrity.py` to ensure expected reference subdirectory structure.

Currently no legacy pesticide reference files are maintained here. Once historical or deprecated versions of the pesticide reference become available, they should be added to this directory with clear provenance notes.

Provenance expectations:
- Filename pattern: `pesticide_reference_legacy_<year>.csv`
- Documentation: include a README entry describing source (e.g., earlier NHANES codebook releases) and differences from current minimal/classified references.

Until such files exist, this placeholder ensures the directory is tracked in Git and CI integrity tests pass.
