"""
Data validation module for PopHealth Observatory.

Provides programmatic validation of downloaded NHANES data against official CDC sources.
Validates URL correctness, row counts, and data integrity.
"""

import re
from dataclasses import dataclass

import pandas as pd
import requests
from bs4 import BeautifulSoup


@dataclass
class ValidationCheck:
    """
    Result of a single validation check.

    Attributes
    ----------
    name : str
        Name of the check (e.g., 'url_match', 'row_count')
    status : str
        Status: 'PASS', 'FAIL', or 'WARN'
    details : str
        Human-readable description of the result
    expected : Optional[object]
        Expected value (if applicable)
    actual : Optional[object]
        Actual value (if applicable)
    """

    name: str
    status: str
    details: str
    expected: object | None = None
    actual: object | None = None


@dataclass
class ComponentValidation:
    """
    Validation results for a single NHANES component.

    Attributes
    ----------
    component : str
        Component name (e.g., 'demographics', 'body_measures')
    status : str
        Overall status: 'PASS' if all checks pass, 'FAIL' if any fail, 'WARN' if warnings exist
    checks : List[ValidationCheck]
        List of individual validation checks performed
    """

    component: str
    status: str
    checks: list[ValidationCheck]


@dataclass
class ValidationReport:
    """
    Complete validation report for a cycle.

    Attributes
    ----------
    cycle : str
        NHANES cycle (e.g., '2017-2018')
    status : str
        Overall status: 'PASS', 'FAIL', or 'WARN'
    components : List[ComponentValidation]
        Validation results for each component
    """

    cycle: str
    status: str
    components: list[ComponentValidation]

    def to_dict(self) -> dict:
        """Convert report to dictionary format."""
        return {
            "cycle": self.cycle,
            "status": self.status,
            "components": {
                cv.component: {
                    "status": cv.status,
                    "checks": {
                        check.name: {
                            "status": check.status,
                            "details": check.details,
                            "expected": check.expected,
                            "actual": check.actual,
                        }
                        for check in cv.checks
                    },
                }
                for cv in self.components
            },
        }

    def __str__(self) -> str:
        """Generate human-readable report summary."""
        lines = [f"Validation Report for Cycle {self.cycle}", f"Overall Status: {self.status}", "=" * 60]

        for cv in self.components:
            lines.append(f"\nComponent: {cv.component} [{cv.status}]")
            for check in cv.checks:
                symbol = "✓" if check.status == "PASS" else ("⚠" if check.status == "WARN" else "✗")
                lines.append(f"  {symbol} {check.name}: {check.details}")
                if check.expected is not None:
                    lines.append(f"    Expected: {check.expected}, Actual: {check.actual}")

        return "\n".join(lines)


def _scrape_cdc_component_metadata(component_url: str, timeout: int = 10) -> dict[str, object]:
    """
    Scrape official CDC component page for metadata.

    Parameters
    ----------
    component_url : str
        URL to the CDC NHANES component page
    timeout : int
        Request timeout in seconds

    Returns
    -------
    Dict[str, object]
        Metadata containing 'record_count', 'data_file_url', 'doc_file_url'

    Raises
    ------
    requests.RequestException
        If the HTTP request fails
    ValueError
        If metadata cannot be parsed from the page
    """
    response = requests.get(component_url, timeout=timeout)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "lxml")

    # Find the data file link (typically ends with .XPT)
    data_link = None
    doc_link = None

    for link in soup.find_all("a", href=True):
        href = link["href"]
        if href.endswith(".XPT") or href.endswith(".xpt"):
            if "https://" not in href:
                # Make absolute URL if relative
                data_link = f"https://wwwn.cdc.gov{href}" if href.startswith("/") else href
            else:
                data_link = href
        elif "Doc" in href or "htm" in href.lower():
            if doc_link is None:  # Take first doc link
                doc_link = f"https://wwwn.cdc.gov{href}" if href.startswith("/") and "https://" not in href else href

    # Try to find record count in the page text
    # Common patterns: "9,254 records" or "Records: 9254"
    record_count = None
    text = soup.get_text()

    # Pattern 1: "X,XXX records" or "X records"
    match = re.search(r"(\d{1,3}(?:,\d{3})*)\s+records", text, re.IGNORECASE)
    if match:
        record_count = int(match.group(1).replace(",", ""))

    # Pattern 2: Look in tables for record count info
    if record_count is None:
        for table in soup.find_all("table"):
            table_text = table.get_text()
            if "record" in table_text.lower():
                match = re.search(r"(\d{1,3}(?:,\d{3})*)", table_text)
                if match:
                    record_count = int(match.group(1).replace(",", ""))
                    break

    return {"record_count": record_count, "data_file_url": data_link, "doc_file_url": doc_link}


def validate_component(
    explorer, cycle: str, component: str, downloaded_data: pd.DataFrame | None = None
) -> ComponentValidation:
    """
    Validate a single NHANES component.

    Parameters
    ----------
    explorer : NHANESExplorer
        The explorer instance (to access component URLs)
    cycle : str
        NHANES cycle (e.g., '2017-2018')
    component : str
        Component name (e.g., 'demographics', 'body_measures')
    downloaded_data : Optional[pd.DataFrame]
        Pre-downloaded data (if None, will download fresh)

    Returns
    -------
    ComponentValidation
        Validation results for this component
    """
    checks = []

    # Get the component URL from the explorer's component mapping
    component_info = explorer.components.get(component)
    if component_info is None:
        checks.append(
            ValidationCheck(
                name="component_exists",
                status="FAIL",
                details=f"Component '{component}' not found in explorer.components",
            )
        )
        return ComponentValidation(component=component, status="FAIL", checks=checks)

    # Determine which URL to use for validation
    # For now, we'll construct the expected CDC URL pattern
    # This is a simplified approach; in production you'd want more robust URL resolution
    cycle_letter = explorer._get_cycle_suffix(cycle)
    component_code = component_info["code"]

    # Common CDC URL patterns
    base_url = f"https://wwwn.cdc.gov/nchs/nhanes/{cycle.replace('-', '/')}/{component_code}_{cycle_letter}.htm"

    try:
        # Scrape official CDC metadata
        cdc_metadata = _scrape_cdc_component_metadata(base_url)

        # Check 1: Data file URL match
        expected_url = cdc_metadata.get("data_file_url")
        if expected_url:
            # Get the URL that our tool would generate
            # This is a simplified check; you might need to adjust based on your actual URL generation logic
            actual_url_pattern = f"{component_code}_{cycle_letter}.XPT"

            if actual_url_pattern.upper() in expected_url.upper():
                checks.append(
                    ValidationCheck(
                        name="url_pattern_match",
                        status="PASS",
                        details="Generated URL pattern matches CDC official URL",
                        expected=expected_url,
                        actual=actual_url_pattern,
                    )
                )
            else:
                checks.append(
                    ValidationCheck(
                        name="url_pattern_match",
                        status="WARN",
                        details="URL pattern may not match exactly",
                        expected=expected_url,
                        actual=actual_url_pattern,
                    )
                )

        # Check 2: Row count validation
        expected_count = cdc_metadata.get("record_count")

        if downloaded_data is None:
            # Download the data using the explorer
            try:
                if component == "demographics":
                    downloaded_data = explorer.get_demographics(cycle)
                elif component == "body_measures":
                    downloaded_data = explorer.get_body_measures(cycle)
                elif component == "blood_pressure":
                    downloaded_data = explorer.get_blood_pressure(cycle)
                else:
                    checks.append(
                        ValidationCheck(
                            name="data_download",
                            status="WARN",
                            details=f"No download method available for component '{component}'",
                        )
                    )
            except Exception as e:
                checks.append(
                    ValidationCheck(name="data_download", status="FAIL", details=f"Failed to download data: {str(e)}")
                )

        if downloaded_data is not None and expected_count is not None:
            actual_count = len(downloaded_data)

            if actual_count == expected_count:
                checks.append(
                    ValidationCheck(
                        name="row_count",
                        status="PASS",
                        details=f"Downloaded {actual_count} rows, matches expected count",
                        expected=expected_count,
                        actual=actual_count,
                    )
                )
            else:
                checks.append(
                    ValidationCheck(
                        name="row_count",
                        status="FAIL",
                        details="Row count mismatch",
                        expected=expected_count,
                        actual=actual_count,
                    )
                )
        elif expected_count is None:
            checks.append(
                ValidationCheck(
                    name="row_count", status="WARN", details="Could not determine expected row count from CDC page"
                )
            )

    except requests.RequestException as e:
        checks.append(ValidationCheck(name="cdc_scrape", status="FAIL", details=f"Failed to access CDC page: {str(e)}"))
    except Exception as e:
        checks.append(ValidationCheck(name="validation_error", status="FAIL", details=f"Validation error: {str(e)}"))

    # Determine overall component status
    if any(check.status == "FAIL" for check in checks):
        status = "FAIL"
    elif any(check.status == "WARN" for check in checks):
        status = "WARN"
    else:
        status = "PASS"

    return ComponentValidation(component=component, status=status, checks=checks)


def run_validation(explorer, cycle: str, components: list[str]) -> ValidationReport:
    """
    Run validation for multiple components in a cycle.

    Parameters
    ----------
    explorer : NHANESExplorer
        The explorer instance
    cycle : str
        NHANES cycle (e.g., '2017-2018')
    components : List[str]
        List of components to validate

    Returns
    -------
    ValidationReport
        Complete validation report
    """
    component_validations = []

    for component in components:
        cv = validate_component(explorer, cycle, component)
        component_validations.append(cv)

    # Determine overall status
    if any(cv.status == "FAIL" for cv in component_validations):
        overall_status = "FAIL"
    elif any(cv.status == "WARN" for cv in component_validations):
        overall_status = "WARN"
    else:
        overall_status = "PASS"

    return ValidationReport(cycle=cycle, status=overall_status, components=component_validations)
