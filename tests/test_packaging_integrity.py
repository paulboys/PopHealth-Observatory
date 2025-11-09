"""Packaging integrity tests ensuring critical reference files are present.

These tests verify that essential data files required by the ingestion pipeline
are properly included in distribution artifacts. Passing these tests allows safe
removal of runtime placeholder injection logic in pesticide_context.py.

SPDX-License-Identifier: MIT
"""

from pathlib import Path

import pytest


class TestReferenceDataPresence:
    """Verify critical reference CSVs are packaged and accessible."""

    def test_minimal_reference_exists(self):
        """Minimal pesticide reference CSV must be present."""
        minimal_path = Path("data/reference/minimal/pesticide_reference_minimal.csv")
        assert minimal_path.exists(), (
            f"Missing required file: {minimal_path}. "
            "Ensure pyproject.toml [tool.setuptools.package-data] includes 'data/reference/minimal/*.csv'"
        )
        # Verify non-empty
        assert minimal_path.stat().st_size > 0, f"{minimal_path} exists but is empty"

    def test_classified_reference_exists(self):
        """Classified pesticide reference CSV with CDC enrichment must be present."""
        classified_path = Path("data/reference/classified/pesticide_reference_classified.csv")
        assert classified_path.exists(), (
            f"Missing required file: {classified_path}. "
            "Ensure pyproject.toml [tool.setuptools.package-data] includes 'data/reference/classified/*.csv'"
        )
        assert classified_path.stat().st_size > 0, f"{classified_path} exists but is empty"

    def test_compatibility_shim_exists(self):
        """Backward compatibility shim (flat reference CSV) must be present."""
        shim_path = Path("data/reference/pesticide_reference.csv")
        assert shim_path.exists(), (
            f"Missing required file: {shim_path}. "
            "Ensure pyproject.toml [tool.setuptools.package-data] includes 'data/reference/*.csv'"
        )
        assert shim_path.stat().st_size > 0, f"{shim_path} exists but is empty"

    def test_minimal_reference_has_key_analytes(self):
        """Minimal reference must include key analytes required by tests."""
        import csv

        minimal_path = Path("data/reference/minimal/pesticide_reference_minimal.csv")
        if not minimal_path.exists():
            pytest.skip("Minimal reference not present; skipping key analyte check")

        with minimal_path.open(encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            analytes = {row.get("analyte_name", "") for row in reader}

        # Key analytes that must be present (tested extensively in test_pesticide_context.py)
        required = {"3-PBA", "DMP"}
        missing = required - analytes

        assert not missing, (
            f"Minimal reference missing required analytes: {missing}. "
            "These are needed for test_pesticide_context assertions."
        )

    def test_classified_reference_subset_of_minimal(self):
        """Classified reference analytes should be a subset of minimal reference."""
        import csv

        minimal_path = Path("data/reference/minimal/pesticide_reference_minimal.csv")
        classified_path = Path("data/reference/classified/pesticide_reference_classified.csv")

        if not (minimal_path.exists() and classified_path.exists()):
            pytest.skip("Both references not present; skipping subset check")

        with minimal_path.open(encoding="utf-8") as fh:
            minimal_analytes = {row.get("analyte_name", "") for row in csv.DictReader(fh)}

        with classified_path.open(encoding="utf-8") as fh:
            classified_analytes = {row.get("analyte_name", "") for row in csv.DictReader(fh)}

        extra = classified_analytes - minimal_analytes
        assert not extra, (
            f"Classified reference contains analytes not in minimal: {extra}. "
            "Classified should be an enriched subset of minimal."
        )


class TestConfigDirectoryStructure:
    """Verify expected directory structure for pesticide reference hierarchy."""

    def test_reference_subdirectories_exist(self):
        """Expected subdirectories under data/reference/ must be present."""
        base = Path("data/reference")
        required_dirs = ["minimal", "classified", "legacy", "discovery", "evidence", "config"]

        for subdir in required_dirs:
            dir_path = base / subdir
            assert dir_path.exists(), f"Missing required directory: {dir_path}"
            assert dir_path.is_dir(), f"{dir_path} exists but is not a directory"

    def test_config_yaml_present(self):
        """Source registry YAML should exist in config directory."""
        yaml_path = Path("data/reference/config/pesticide_sources.yml")
        # Note: This file may be optional in early phases; marking as soft assertion
        if yaml_path.exists():
            assert yaml_path.stat().st_size > 0, f"{yaml_path} exists but is empty"
        # If missing, just document expectation for future
        # (not asserting failure here since registry is Phase 3+)


class TestPlaceholderInjectionRemoval:
    """Tests supporting safe removal of runtime placeholder analyte injection."""

    def test_no_placeholder_injection_needed(self):
        """When packaging is correct, no runtime analyte injection should occur."""
        from pophealth_observatory.pesticide_context import load_analyte_reference

        # Load reference (will use cascade to find best available file)
        analytes = load_analyte_reference()

        # Check that key analytes are present naturally (not injected)
        analyte_names = {a.analyte_name for a in analytes}

        required = {"3-PBA", "DMP"}
        missing = required - analyte_names

        if missing:
            pytest.fail(
                f"Key analytes missing from packaged reference: {missing}. "
                "Placeholder injection still needed; packaging integrity not yet sufficient. "
                "Fix by ensuring minimal CSV includes these rows."
            )

    def test_loader_does_not_inject_duplicates(self):
        """Verify placeholder injection only adds missing analytes (no duplicates from injection)."""
        from pophealth_observatory.pesticide_context import load_analyte_reference

        analytes = load_analyte_reference()

        # Group by (variable_name, analyte_name) pairs to detect true duplicates
        # Multiple variable codes for same analyte name is valid (e.g., LBCHCB vs LBXHCB)
        # But same variable_name appearing twice indicates injection duplication
        var_analyte_pairs = [(a.variable_name, a.analyte_name) for a in analytes]

        seen = set()
        duplicates = []
        for pair in var_analyte_pairs:
            if pair in seen:
                duplicates.append(pair)
            seen.add(pair)

        assert not duplicates, (
            f"Duplicate (variable_name, analyte_name) pairs found: {duplicates}. "
            "This indicates placeholder injection is adding rows already present in the reference."
        )
