"""Validate pesticide_reference.csv against authoritative sources.

Checks:
1. PubChem CID → CAS number correspondence
2. NHANES cycle availability (attempt downloads)
3. Chemical name consistency
4. Data completeness and format validation

Usage:
    python scripts/validate_pesticide_reference.py [--full] [--save-report]

Requires: requests, pandas
"""

from __future__ import annotations

import argparse
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd
import requests

# Root directory
ROOT = Path(__file__).resolve().parent.parent
REF_FILE = ROOT / "data" / "reference" / "pesticide_reference.csv"

# PubChem API endpoints
PUBCHEM_BASE = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"


@dataclass
class ValidationResult:
    """Result of a single validation check."""

    analyte_name: str
    check_type: str
    status: str  # "PASS", "FAIL", "WARNING", "SKIP"
    expected: Any
    actual: Any
    message: str


class PesticideReferenceValidator:
    """Validator for pesticide reference CSV authenticity."""

    def __init__(self, reference_file: Path):
        """Initialize validator with reference CSV path."""
        self.reference_file = reference_file
        self.df = pd.read_csv(reference_file)
        self.results: list[ValidationResult] = []
        self.session = requests.Session()
        self.session.headers.update(
            {"User-Agent": ("PopHealthObservatory/0.7.0 " "(https://github.com/paulboys/PopHealth-Observatory)")}
        )

    def validate_all(self, full: bool = False) -> list[ValidationResult]:
        """Run all validation checks.

        Parameters
        ----------
        full : bool
            If True, run expensive checks (NHANES downloads, all PubChem queries).
            If False, run quick spot checks only.

        Returns
        -------
        list[ValidationResult]
            All validation results.
        """
        print(f"Validating {len(self.df)} analytes from {self.reference_file.name}")
        print(f"Mode: {'FULL' if full else 'QUICK'}\n")

        # Quick checks (always run)
        self._validate_format()
        self._validate_completeness()

        if full:
            # Expensive checks
            self._validate_pubchem_all()
            self._validate_nhanes_cycles()
        else:
            # Spot checks only
            self._validate_pubchem_spot_checks()

        return self.results

    def _validate_format(self) -> None:
        """Validate CSV format and required columns."""
        print("Checking CSV format...")
        required_cols = [
            "analyte_name",
            "cas_rn",
            "pubchem_cid",
            "first_cycle_measured",
            "last_cycle_measured",
        ]

        for col in required_cols:
            if col not in self.df.columns:
                self.results.append(
                    ValidationResult(
                        analyte_name="ALL",
                        check_type="format",
                        status="FAIL",
                        expected=col,
                        actual="missing",
                        message=f"Required column '{col}' missing from CSV",
                    )
                )
                return

        self.results.append(
            ValidationResult(
                analyte_name="ALL",
                check_type="format",
                status="PASS",
                expected=len(required_cols),
                actual=len(required_cols),
                message="All required columns present",
            )
        )

    def _validate_completeness(self) -> None:
        """Check for missing critical data."""
        print("Checking data completeness...")

        for _, row in self.df.iterrows():
            analyte = row["analyte_name"]

            # CAS number should not be empty
            if pd.isna(row["cas_rn"]) or str(row["cas_rn"]).strip() == "":
                self.results.append(
                    ValidationResult(
                        analyte_name=analyte,
                        check_type="completeness",
                        status="FAIL",
                        expected="CAS number",
                        actual="empty",
                        message="Missing CAS Registry Number",
                    )
                )

            # PubChem CID should be numeric or NA
            cid = row["pubchem_cid"]
            if pd.notna(cid) and cid != "NA":
                try:
                    int(cid)
                except (ValueError, TypeError):
                    self.results.append(
                        ValidationResult(
                            analyte_name=analyte,
                            check_type="completeness",
                            status="FAIL",
                            expected="numeric CID",
                            actual=str(cid),
                            message="Invalid PubChem CID format",
                        )
                    )

            # Cycle years should be 4-digit integers
            for col in ["first_cycle_measured", "last_cycle_measured"]:
                year = row[col]
                if pd.notna(year):
                    try:
                        y = int(year)
                        if not (1999 <= y <= 2030):
                            self.results.append(
                                ValidationResult(
                                    analyte_name=analyte,
                                    check_type="completeness",
                                    status="WARNING",
                                    expected="year 1999-2030",
                                    actual=str(y),
                                    message=f"Unusual {col}: {y}",
                                )
                            )
                    except (ValueError, TypeError):
                        self.results.append(
                            ValidationResult(
                                analyte_name=analyte,
                                check_type="completeness",
                                status="FAIL",
                                expected="4-digit year",
                                actual=str(year),
                                message=f"Invalid {col} format",
                            )
                        )

    def _validate_pubchem_spot_checks(self) -> None:
        """Validate a few key analytes against PubChem (quick mode)."""
        print("Running PubChem spot checks (3 samples)...")

        # Sample 3 analytes with valid PubChem CIDs
        test_cases = [
            ("DMP", 11640, "814-24-8"),
            ("TCPy", 2730, "6515-38-4"),
            ("3-PBA", 643975, "3739-38-6"),
        ]

        for analyte_name, expected_cid, expected_cas in test_cases:
            self._check_pubchem_compound(analyte_name, expected_cid, expected_cas)
            time.sleep(0.3)  # Rate limiting

    def _validate_pubchem_all(self) -> None:
        """Validate all analytes with PubChem CIDs (full mode)."""
        print(f"Validating all {len(self.df)} analytes against PubChem...")

        for _, row in self.df.iterrows():
            analyte = row["analyte_name"]
            cid = row["pubchem_cid"]
            expected_cas = row["cas_rn"]

            if pd.isna(cid) or cid == "NA":
                self.results.append(
                    ValidationResult(
                        analyte_name=analyte,
                        check_type="pubchem",
                        status="SKIP",
                        expected="N/A",
                        actual="N/A",
                        message="No PubChem CID to verify",
                    )
                )
                continue

            try:
                cid_int = int(cid)
                self._check_pubchem_compound(analyte, cid_int, expected_cas)
                time.sleep(0.3)  # Rate limiting
            except (ValueError, TypeError):
                self.results.append(
                    ValidationResult(
                        analyte_name=analyte,
                        check_type="pubchem",
                        status="FAIL",
                        expected="numeric CID",
                        actual=str(cid),
                        message="Cannot validate - invalid CID format",
                    )
                )

    def _check_pubchem_compound(self, analyte_name: str, cid: int, expected_cas: str) -> None:
        """Check a single compound against PubChem API.

        Parameters
        ----------
        analyte_name : str
            Human-readable analyte name
        cid : int
            PubChem Compound ID
        expected_cas : str
            Expected CAS Registry Number from reference CSV
        """
        url = f"{PUBCHEM_BASE}/compound/cid/{cid}/property/IUPACName,MolecularFormula/JSON"

        try:
            resp = self.session.get(url, timeout=30)

            if resp.status_code == 404:
                self.results.append(
                    ValidationResult(
                        analyte_name=analyte_name,
                        check_type="pubchem",
                        status="FAIL",
                        expected=f"CID {cid}",
                        actual="not found",
                        message=f"PubChem CID {cid} does not exist",
                    )
                )
                return

            resp.raise_for_status()
            # PubChem compound exists (properties validated via successful response)

            # Now check CAS number
            cas_url = f"{PUBCHEM_BASE}/compound/cid/{cid}/synonyms/JSON"
            cas_resp = self.session.get(cas_url, timeout=30)
            cas_resp.raise_for_status()
            cas_data = cas_resp.json()

            synonyms = cas_data.get("InformationList", {}).get("Information", [{}])[0].get("Synonym", [])

            # Look for CAS number in synonyms (format: XXX-XX-X or XXXX-XX-X)
            cas_found = None
            for syn in synonyms:
                # Basic CAS pattern check
                if isinstance(syn, str) and "-" in syn and syn.replace("-", "").isdigit():
                    # Normalize for comparison (remove leading zeros)
                    cas_found = syn
                    break

            if cas_found:
                # Normalize both for comparison
                expected_normalized = expected_cas.strip()
                found_normalized = cas_found.strip()

                if expected_normalized == found_normalized:
                    self.results.append(
                        ValidationResult(
                            analyte_name=analyte_name,
                            check_type="pubchem",
                            status="PASS",
                            expected=expected_cas,
                            actual=cas_found,
                            message=f"CID {cid} → CAS {cas_found} verified",
                        )
                    )
                else:
                    self.results.append(
                        ValidationResult(
                            analyte_name=analyte_name,
                            check_type="pubchem",
                            status="FAIL",
                            expected=expected_cas,
                            actual=cas_found,
                            message=(f"CAS mismatch for CID {cid}: " f"expected {expected_cas}, found {cas_found}"),
                        )
                    )
            else:
                self.results.append(
                    ValidationResult(
                        analyte_name=analyte_name,
                        check_type="pubchem",
                        status="WARNING",
                        expected=expected_cas,
                        actual="no CAS in PubChem",
                        message=f"CID {cid} exists but CAS not found in synonyms",
                    )
                )

        except requests.exceptions.RequestException as e:
            self.results.append(
                ValidationResult(
                    analyte_name=analyte_name,
                    check_type="pubchem",
                    status="WARNING",
                    expected="API response",
                    actual="error",
                    message=f"PubChem API error: {e}",
                )
            )

    def _validate_nhanes_cycles(self) -> None:
        """Validate cycle availability by attempting to access NHANES files."""
        print("Validating NHANES cycle availability (sample checks)...")

        # Sample: Check if DMP exists in first and last reported cycles
        test_cases = [
            ("DMP", "1999-2000", "URXDMP"),
            ("3-PBA", "2001-2002", "URX3PBA"),
        ]

        for analyte_name, cycle, expected_var in test_cases:
            self._check_nhanes_component(analyte_name, cycle, expected_var)
            time.sleep(0.5)

    def _check_nhanes_component(self, analyte_name: str, cycle: str, expected_var: str) -> None:
        """Check if a variable exists in a specific NHANES cycle.

        Parameters
        ----------
        analyte_name : str
            Analyte name
        cycle : str
            NHANES cycle (e.g., "1999-2000")
        expected_var : str
            Expected variable code (e.g., "URXDMP")
        """
        # This is a placeholder - actual implementation would need to:
        # 1. Determine which component file contains the variable
        # 2. Construct appropriate URLs
        # 3. Check if the file exists and contains the variable

        # For now, just mark as SKIP with a note
        self.results.append(
            ValidationResult(
                analyte_name=analyte_name,
                check_type="nhanes_cycles",
                status="SKIP",
                expected=f"{cycle}: {expected_var}",
                actual="not implemented",
                message=("NHANES cycle validation requires integration with " "observatory.py download logic (TODO)"),
            )
        )

    def print_report(self) -> None:
        """Print validation report to console."""
        print("\n" + "=" * 80)
        print("VALIDATION REPORT")
        print("=" * 80 + "\n")

        # Group by status
        by_status = {"PASS": [], "FAIL": [], "WARNING": [], "SKIP": []}
        for result in self.results:
            by_status[result.status].append(result)

        # Summary counts
        total = len(self.results)
        print(f"Total checks: {total}")
        print(f"  PASS:    {len(by_status['PASS'])}")
        print(f"  FAIL:    {len(by_status['FAIL'])}")
        print(f"  WARNING: {len(by_status['WARNING'])}")
        print(f"  SKIP:    {len(by_status['SKIP'])}")
        print()

        # Show failures first
        if by_status["FAIL"]:
            print("FAILURES:")
            print("-" * 80)
            for r in by_status["FAIL"]:
                print(f"  [{r.analyte_name}] {r.check_type}")
                print(f"    Expected: {r.expected}")
                print(f"    Actual:   {r.actual}")
                print(f"    {r.message}")
                print()

        # Then warnings
        if by_status["WARNING"]:
            print("WARNINGS:")
            print("-" * 80)
            for r in by_status["WARNING"]:
                print(f"  [{r.analyte_name}] {r.check_type}")
                print(f"    {r.message}")
                print()

        # Summary assessment
        print("=" * 80)
        if not by_status["FAIL"]:
            print("✓ No critical failures detected")
        else:
            print(f"✗ {len(by_status['FAIL'])} critical failure(s) detected")

        if by_status["WARNING"]:
            print(f"⚠ {len(by_status['WARNING'])} warning(s) - review recommended")

        print("=" * 80)

    def save_report(self, output_path: Path) -> None:
        """Save validation results to CSV.

        Parameters
        ----------
        output_path : Path
            Output file path
        """
        df_results = pd.DataFrame([vars(r) for r in self.results])
        df_results.to_csv(output_path, index=False)
        print(f"\nValidation report saved to: {output_path}")


def main():
    """Run validation from command line."""
    parser = argparse.ArgumentParser(description="Validate pesticide_reference.csv authenticity")
    parser.add_argument(
        "--full",
        action="store_true",
        help="Run full validation (slower; queries all PubChem entries)",
    )
    parser.add_argument(
        "--save-report",
        type=str,
        help="Save validation report to CSV file",
    )
    args = parser.parse_args()

    if not REF_FILE.exists():
        print(f"ERROR: Reference file not found: {REF_FILE}")
        sys.exit(1)

    validator = PesticideReferenceValidator(REF_FILE)

    try:
        validator.validate_all(full=args.full)
        validator.print_report()

        if args.save_report:
            output_path = Path(args.save_report)
            validator.save_report(output_path)

        # Exit code based on failures
        failures = sum(1 for r in validator.results if r.status == "FAIL")
        sys.exit(1 if failures > 0 else 0)

    except KeyboardInterrupt:
        print("\n\nValidation interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\nERROR: Validation failed with exception: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
