# Data Validation

PopHealth Observatory includes a comprehensive programmatic validation system that verifies downloaded NHANES data against official CDC metadata sources. This provides confidence in data integrity and completeness, essential for research and production use.

## Overview

The validation module automatically:

1. **Verifies URLs** - Confirms that data file URLs match CDC's official documentation
2. **Checks Row Counts** - Validates that downloaded data contains the expected number of records
3. **Generates Reports** - Produces structured validation reports with PASS/WARN/FAIL status

## Quick Start

```python
from pophealth_observatory import NHANESExplorer

# Initialize explorer
explorer = NHANESExplorer()

# Validate specific components for a cycle
report = explorer.validate(
    cycle='2017-2018',
    components=['demographics', 'body_measures']
)

# Check overall status
print(f"Validation Status: {report['status']}")  # PASS, WARN, or FAIL

# Review detailed results
for component, details in report['components'].items():
    print(f"\n{component}: {details['status']}")
    for check_name, check_result in details['checks'].items():
        print(f"  {check_name}: {check_result['status']}")
        print(f"    {check_result['details']}")
```

## Validation Report Structure

The validation report is a nested dictionary with the following structure:

```python
{
    'cycle': '2017-2018',
    'status': 'PASS',  # Overall status
    'components': {
        'demographics': {
            'status': 'PASS',
            'checks': {
                'url_pattern_match': {
                    'status': 'PASS',
                    'details': 'Generated URL pattern matches CDC official URL',
                    'expected': 'https://wwwn.cdc.gov/.../DEMO_J.XPT',
                    'actual': 'DEMO_J.XPT'
                },
                'row_count': {
                    'status': 'PASS',
                    'details': 'Downloaded 9254 rows, matches expected count',
                    'expected': 9254,
                    'actual': 9254
                }
            }
        }
    }
}
```

## Status Values

- **PASS**: All validation checks passed successfully
- **WARN**: Minor issues detected (e.g., could not parse metadata, but data appears correct)
- **FAIL**: Critical issues detected (e.g., row count mismatch, incorrect URL)

## Use Cases

### Pre-Analysis Validation

Validate data before running analysis to ensure data quality:

```python
explorer = NHANESExplorer()

# Validate before analysis
report = explorer.validate('2017-2018', ['demographics', 'body_measures'])

if report['status'] == 'PASS':
    # Safe to proceed with analysis
    data = explorer.get_merged_data('2017-2018')
    # ... perform analysis ...
else:
    print("Validation failed! Review report before proceeding.")
    print(report)
```

### CI/CD Integration

Include validation in automated testing pipelines:

```python
import pytest
from pophealth_observatory import NHANESExplorer

def test_nhanes_data_integrity():
    """Ensure NHANES data downloads are valid."""
    explorer = NHANESExplorer()
    report = explorer.validate('2017-2018', ['demographics'])
    assert report['status'] in ['PASS', 'WARN'], f"Validation failed: {report}"
```

### Demo Preparation

Verify data correctness before demonstrations or presentations:

```python
# Validate your demo use case
explorer = NHANESExplorer()
report = explorer.validate('2017-2018', ['demographics', 'body_measures'])

# Generate validation summary
print(f"Validation Report: {report['cycle']}")
print(f"Overall Status: {report['status']}")

for component in report['components']:
    comp_status = report['components'][component]['status']
    print(f"  {component}: {comp_status}")
```

## Behind the Scenes

The validation system:

1. **Scrapes CDC Pages**: Uses BeautifulSoup to parse official NHANES component documentation pages
2. **Extracts Metadata**: Parses record counts and data file URLs from CDC HTML
3. **Compares Results**: Downloads data using the explorer and compares against CDC metadata
4. **Reports Findings**: Structures results with clear PASS/WARN/FAIL status

## Handling Validation Failures

### Row Count Mismatch

If row counts don't match:

```python
# Check the specific mismatch
row_check = report['components']['demographics']['checks']['row_count']
print(f"Expected: {row_check['expected']}")
print(f"Actual: {row_check['actual']}")

# Possible causes:
# - Network interruption during download
# - CDC updated the dataset
# - Explorer URL resolution issue
```

**Resolution**:
- Clear cache and retry download
- Verify cycle and component names
- Check CDC website for dataset updates

### URL Pattern Mismatch

If URLs don't match:

```python
url_check = report['components']['demographics']['checks']['url_pattern_match']
print(f"Expected: {url_check['expected']}")
print(f"Actual: {url_check['actual']}")
```

**Resolution**:
- Verify cycle suffix mapping in `explorer.cycle_suffix_map`
- Check if CDC changed URL structure
- Review component code in `explorer.components`

### Network Errors

If CDC pages cannot be accessed:

```python
# Look for scraping errors
if 'cdc_scrape' in report['components']['demographics']['checks']:
    scrape_check = report['components']['demographics']['checks']['cdc_scrape']
    if scrape_check['status'] == 'FAIL':
        print(f"Network issue: {scrape_check['details']}")
```

**Resolution**:
- Check internet connectivity
- Verify CDC website is accessible
- Retry after a short delay

## Advanced Usage

### Custom Validation Logic

Extend validation for custom checks:

```python
from pophealth_observatory.validation import validate_component

# Run validation for a single component
comp_validation = validate_component(
    explorer=explorer,
    cycle='2017-2018',
    component='demographics'
)

# Access individual checks
for check in comp_validation.checks:
    print(f"{check.name}: {check.status}")
    if check.status == 'FAIL':
        print(f"  Issue: {check.details}")
        print(f"  Expected: {check.expected}")
        print(f"  Actual: {check.actual}")
```

### Batch Validation

Validate multiple cycles:

```python
cycles = ['2015-2016', '2017-2018', '2019-2020']
components = ['demographics', 'body_measures']

results = {}
for cycle in cycles:
    report = explorer.validate(cycle, components)
    results[cycle] = report['status']

print("Validation Summary:")
for cycle, status in results.items():
    print(f"  {cycle}: {status}")
```

## Technical Details

### Data Classes

The validation module uses dataclasses for structured results:

- `ValidationCheck`: Single check result (name, status, details, expected, actual)
- `ComponentValidation`: All checks for one component
- `ValidationReport`: Complete report for a cycle

### HTTP Scraping

- Uses `requests` for HTTP GET with 10-second timeout
- Parses HTML with `BeautifulSoup` (lxml parser)
- Extracts record counts via regex patterns
- Handles both absolute and relative CDC URLs

### Error Handling

- Network errors return FAIL status with error message
- Parsing failures return WARN status
- Missing metadata returns WARN (graceful degradation)

## Best Practices

1. **Always validate before critical analysis** - Ensures data integrity
2. **Review WARN status carefully** - May indicate partial data or parsing issues
3. **Cache validation results** - Avoid repeated CDC page scraping
4. **Include in test suites** - Catch data issues early in development
5. **Document validation outcomes** - Include in research methods/notes

## Future Enhancements

Planned improvements:

- Column-level validation (verify expected columns exist)
- Data type validation (ensure numeric fields are numeric)
- Range validation (check values within expected ranges)
- Cross-component consistency checks
- Historical validation result tracking

## Support

If validation consistently fails for known-good cycles/components:

1. Verify dependencies installed: `pip install beautifulsoup4 lxml`
2. Check CDC website accessibility
3. Review [GitHub Issues](https://github.com/yourusername/pophealth-observatory/issues)
4. File a bug report with validation report output

---

**Related Documentation**:
- [Getting Started](../getting-started.md) - Basic usage
- [API Reference](../api.md) - Full API documentation
- [Usage Examples](quickstart.md) - More code examples
