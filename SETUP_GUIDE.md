# PopHealth Observatory – Setup & Usage Guide

Human-facing setup instructions for using the Python toolkit. Internal agent / generation rules live in `.github/copilot-instructions.md` and are intentionally excluded here.

---
## 1. Prerequisites

| Requirement | Notes |
|-------------|-------|
| Python 3.10+ | Tested on 3.11 / 3.12 |
| Git | For cloning + version control |
| Optional: virtual env | `python -m venv .venv` or `conda create -n pophealth python=3.11` |
| Optional: Streamlit | For the interactive app (`pip install streamlit`) |

> R is not required. A future optional R layer will use Apache Arrow for file interchange (no Python–R bridging needed).

---
## 2. Install

```powershell
git clone https://github.com/paulboys/PopHealth-Observatory.git
cd PopHealth-Observatory
python -m venv .venv
./.venv/Scripts/Activate.ps1  # Windows PowerShell
pip install -e .[dev]
```

Minimal verification:
```powershell
pytest -q
python -c "import pophealth_observatory as p; print(p.__version__)"
```

---
## 3. Core Workflow

```python
from pophealth_observatory.observatory import NHANESExplorer

explorer = NHANESExplorer()

# Download & merge demographics, body measures, and blood pressure
# Note: create_merged_dataset() currently merges all three components by default
df = explorer.create_merged_dataset(cycle="2017-2018")

# Validate integrity against CDC metadata
report = explorer.validate(cycle="2017-2018", components=["demographics", "body_measures", "blood_pressure"])
print(f"Validation status: {report['status']}")

# Weighted mean (experimental survey helper - auto-detects survey weights)
result = explorer.calculate_weighted_mean(df, variable="body_mass_index")
print(f"Weighted BMI mean: {result['weighted_mean']:.2f}")
```

---
## 4. Key Concepts

| Concept | Description | Output |
|---------|-------------|--------|
| Ingestion | Robust multi-URL NHANES file download | DataFrames |
| Harmonization | Column selection + semantic renaming + derived metrics | Standardized schema |
| Manifest | Structured inventory of component listing tables | JSON / DataFrame |
| Validation | Row count & source checks for integrity | Report object |
| Pesticide snippets | Regex-based analyte sentence windows | JSONL lines |
| RAG (experimental) | Embedding + similarity retrieval of snippet context | Ranked snippet dicts |

---
## 5. Data Outputs & Locations

| Artifact | Path | Format |
|----------|------|--------|
| Manifest JSON | `manifests/` | `.json` |
| Pesticide snippets | `data/processed/pesticides/` | `.jsonl` |
| Reference tables | `data/reference/` | `.csv` / `.yml` |
| Raw pesticide text | `data/raw/pesticides/` | `.txt` |

Parquet caching for large multi-cycle merges is planned (will locate under a future `shared_data/` or `data/processed/` subdirectory with date-stamped filenames).

---
## 6. Validation Strategy

1. Programmatic: `validate()` compares ingested data vs. CDC published metadata (rows, availability).
2. Analytical (in progress): `reproducibility/` notebooks re-derive published aggregate stats to confirm end-to-end correctness.

Edge cases handled: missing downloads → empty DataFrame; mismatch in participant IDs triggers warning; missing expected columns raise `ValueError`.

---
## 7. Survey Weights (Experimental Helpers)

Functions:
```python
explorer.get_survey_weight(cycle: str, component: str) -> str
explorer.calculate_weighted_mean(data: pd.DataFrame, variable: str, weight_var: str = None, min_weight: float = 0) -> dict
```

The `calculate_weighted_mean` function auto-detects survey weights (exam_weight, interview_weight, or dietary_day1_weight) if not specified. Returns a dictionary with `weighted_mean`, `unweighted_mean`, `n_obs`, and `sum_weights`.

Currently covers standard 2-year weights. Planned: variance estimation & multi-cycle normalized weighting.

---
## 8. Development Tasks

```powershell
# Lint & format
ruff check .
black --check .

# Tests & coverage
pytest -q
coverage run -m pytest && coverage report -m

# Build docs
mkdocs build
```

Install/update pre-commit hooks:
```powershell
pre-commit install
pre-commit run --all-files
```

---
## 9. Contributing

1. Open an issue describing feature/bug.
2. Create a branch (`feat/<short>` or `fix/<short>`).
3. Add type hints & NumPy-style docstrings for new public functions.
4. Add tests (use `tmp_path` for filesystem side-effects). Focus on deterministic helpers.
5. Update `CHANGELOG.md` for user-facing changes.
6. Ensure CI passes before requesting review.

---
## 10. Planned R Layer (Future)

The R layer will: parse harmonized parquet outputs via `arrow`, produce advanced survey or longitudinal analyses, and optionally write derived metrics back to shared parquet. There is no S4 implementation yet; ignore any historical Bioconductor references found in older commits.

---
## 11. FAQ

| Question | Answer |
|----------|--------|
| Do I need R? | No—pure Python usage today. |
| Why JSONL for snippets? | Efficient line-wise streaming & indexing. |
| How do I regenerate a manifest? | Use `get_detailed_component_manifest` or `save_detailed_component_manifest`. |
| Can I add new analyte domains? | Follow the pattern in `pesticide_ingestion.py` (compile regex once, yield dataclass instances). |
| How do I trust weights? | Helpers are early-stage; cross-check with NHANES analytic guidance. |

---
## 12. Troubleshooting Quick Reference

| Symptom | Likely Cause | Action |
|---------|--------------|--------|
| Empty DataFrame | All URL attempts failed | Re-run with network available; inspect cycle code |
| Validation mismatch | Source metadata changed | Open issue; update scraper logic |
| No snippet matches | Patterns too strict | Inspect reference file; broaden regex tokens |
| Slow merge | Large multi-cycle join | Future caching; consider subset of cycles |

---
## 13. Ethical / Usage Notes

Not a clinical decision tool. Verify methodology when publishing. Cite NHANES appropriately.

---
## 14. Next Milestones

See `ROADMAP.md` for: harmonization registry, time trend utilities, caching backend, coverage gating.

---
## 15. License

MIT License – see the [LICENSE](https://github.com/paulboys/PopHealth-Observatory/blob/main/LICENSE) file on GitHub or the in-site copy on the [License page](license.md).

---
*Last updated: 2025-11-03*

<!-- INTERNAL_INSTRUCTIONS_EXCLUDED_FROM_DOCS -->

## 2. Install VS Code Extensions

### Essential Extensions
1. **GitHub Copilot** (`GitHub.copilot`)
2. **GitHub Copilot Chat** (`GitHub.copilot-chat`)
3. **R** (`REditorSupport.r`)
4. **Python** (`ms-python.python`)
5. **Pylance** (`ms-python.vscode-pylance`)
6. **Jupyter** (`ms-toolsai.jupyter`)
7. **Quarto** (`quarto.quarto`)
8. **Better Comments** (`aaron-bond.better-comments`) - optional but helpful

### Install via Command Palette
Press `Ctrl+Shift+P` (Windows/Linux) or `Cmd+Shift+P` (Mac), type "Install Extensions", then search and install each.

---

## 3. Configure VS Code Settings

Press `Ctrl+,` (Windows/Linux) or `Cmd+,` (Mac) to open Settings, then click the "Open Settings (JSON)" icon in the top right.

Add these configurations:

```json
{
    "r.rterm.windows": "C:\\Program Files\\R\\R-4.4.0\\bin\\R.exe",
    "r.rterm.mac": "/usr/local/bin/R",
    "r.rterm.linux": "/usr/bin/R",
    "r.lsp.enabled": true,
    "r.lsp.debug": false,
    "r.alwaysUseActiveTerminal": true,
    "r.bracketedPaste": true,
    "r.plot.useHttpgd": true,

    "python.defaultInterpreterPath": "python",
    "python.analysis.typeCheckingMode": "basic",
    "python.analysis.autoImportCompletions": true,

    "github.copilot.enable": {
        "*": true,
        "r": true,
        "python": true,
        "markdown": true
    },

    "files.associations": {
        "*.qmd": "markdown"
    },

    "editor.formatOnSave": false,
    "editor.tabSize": 2,
    "[python]": {
        "editor.tabSize": 4,
        "editor.formatOnSave": true
    },
    "[r]": {
        "editor.tabSize": 2
    }
}
```

**Note**: Adjust the R path to match your installation.

---

## 4. Project Structure

Create this folder structure for your project:

```
my-bioconductor-ml-project/
├── .github/
│   ├── copilot-instructions.md
│   ├── workflows/
│   │   └── copilot-setup-steps.yml
│   └── agents/
│       ├── bioconductor-agent.yml
│       └── ml-agent.yml
├── .vscode/
│   ├── settings.json
│   └── extensions.json
├── r/
│   ├── .copilot-instructions.md
│   ├── DESCRIPTION
│   ├── NAMESPACE
│   ├── R/
│   │   └── analysis_functions.R
│   ├── man/
│   └── tests/
│       └── testthat/
├── python/
│   ├── .copilot-instructions.md
│   ├── requirements.txt
│   ├── src/
│   │   └── models.py
│   └── tests/
│       └── test_models.py
├── shared_data/
│   ├── README.md
│   └── .gitignore
├── notebooks/
│   ├── exploration.qmd
│   └── analysis.qmd
├── docs/
├── .gitignore
└── README.md
```

---

## 5. GitHub Copilot Instructions Files

### Main Instructions: `.github/copilot-instructions.md`

```markdown
# Bioconductor + ML Pipeline Project

## Project Overview
This project combines R/Bioconductor for genomic data analysis with Python for advanced machine learning. Data is exchanged via Apache Arrow (Parquet format) - NEVER use reticulate.

## Technology Stack

### R Environment
- R 4.4+
- Bioconductor 3.19+
- Key packages: SummarizedExperiment, GenomicRanges, DESeq2
- Data export: arrow package

### Python Environment
- Python 3.11+
- ML: scikit-learn, TensorFlow/PyTorch
- Data loading: pyarrow, pandas
- Testing: pytest

## Data Interchange Protocol

**CRITICAL**: Never use reticulate for Python-R communication.

### From R to Python:
```r
library(arrow)
write_parquet(dataframe, "shared_data/output.parquet")
```

### From Python to R:
```python
import pyarrow.parquet as pq
df = pq.read_table("shared_data/output.parquet").to_pandas()
```

## Coding Standards

### R Code - Bioconductor Guidelines
- Use `<-` for assignment, never `=`
- Use `TRUE`/`FALSE`, never `T`/`F`
- Prefer S4 classes over S3 for complex objects
- Use CamelCase for S4 class names
- Use snake_case for function names
- Re-use existing Bioconductor classes (SummarizedExperiment, GRanges, etc.)
- All functions must have roxygen2 documentation
- Include input validation for all functions
- Write unit tests with testthat
- Must pass BiocCheck with no errors/warnings

### Python Code - PEP 8 + Type Hints
- Follow PEP 8 style guide strictly
- Type hints required for all function signatures
- Use pathlib for file paths, never string concatenation
- Docstrings in NumPy format
- Use dataclasses or Pydantic for data structures
- Write unit tests with pytest
- Use scikit-learn pipelines for ML workflows

## Build, Run, Test Commands

### R Testing:
```bash
R CMD check .
Rscript -e "BiocCheck::BiocCheck('.')"
Rscript -e "testthat::test_dir('tests')"
```

### Python Testing:
```bash
pytest python/tests/
python -m mypy python/src/
```

## File Naming Conventions
- R files: `snake_case.R`
- Python files: `snake_case.py`
- Quarto notebooks: `descriptive-name.qmd`
- Data files: `YYYY-MM-DD_descriptor.parquet`

## Git Workflow
- Never commit data files > 100MB
- Never commit `.Rdata`, `.RHistory`, or `__pycache__`
- Commit `.parquet` files in `shared_data/` only if < 10MB
```

---

### R-Specific Instructions: `r/.copilot-instructions.md`

```markdown
applyTo: "r/**/*.R"

# R/Bioconductor Specific Constraints

## Bioconductor Package Standards

When generating R code in this directory, follow Bioconductor package guidelines:

### Function Documentation (roxygen2)
Every function must have:
```r
#' @title Short title
#' @description Detailed description
#' @param paramName Description of parameter
#' @return Description of return value
#' @examples
#' # Example usage
#' @export
```

### S4 Class Definitions
```r
#' @title ClassName
#' @description Class description
#' @slot slotName Description
setClass("ClassName",
    slots = c(
        slotName = "character"
    )
)
```

### Input Validation
Always validate inputs:
```r
stopifnot(is(input, "SummarizedExperiment"))
if (!all(lengths > 0)) stop("All lengths must be positive")
```

### Bioconductor Class Usage
Prefer existing Bioconductor classes:
- Use `SummarizedExperiment` for assay + metadata
- Use `GRanges` for genomic coordinates
- Use `GRangesList` for grouped ranges
- Use `DataFrame` instead of `data.frame` when in Bioconductor objects

### Dependencies
Declare in DESCRIPTION:
- `Imports:` for required packages
- `Suggests:` for optional/test packages
- Use `BiocGenerics` functions when available

### Testing
Use testthat framework:
```r
test_that("function works correctly", {
    result <- my_function(input)
    expect_is(result, "SummarizedExperiment")
    expect_equal(ncol(result), 10)
})
```

### Code Style
- Max 80 characters per line
- 2-space indentation
- Use spaces around operators: `x <- y + z`
- No trailing whitespace
```

---

### Python-Specific Instructions: `python/.copilot-instructions.md`

```markdown
applyTo: "python/**/*.py"

# Python ML Specific Constraints

## Type Hints Required

All functions must have complete type hints:
```python
from typing import Optional, List, Tuple
import pandas as pd
from pathlib import Path

def process_data(
    input_path: Path,
    columns: Optional[List[str]] = None
) -> Tuple[pd.DataFrame, dict]:
    """Process data and return results."""
    ...
```

## ML Pipeline Standards

Use scikit-learn pipelines:
```python
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestClassifier

pipeline = Pipeline([
    ('scaler', StandardScaler()),
    ('classifier', RandomForestClassifier())
])
```

## Data Loading from R

Always load Parquet files from shared_data/:
```python
import pyarrow.parquet as pq
from pathlib import Path

data_path = Path("shared_data/from_r.parquet")
df = pq.read_table(data_path).to_pandas()
```

## Error Handling

Use specific exceptions:
```python
if not data_path.exists():
    raise FileNotFoundError(f"Data file not found: {data_path}")

if df.empty:
    raise ValueError("DataFrame is empty, cannot proceed")
```

## Testing with pytest

Write comprehensive tests:
```python
import pytest
from pathlib import Path

def test_model_training():
    """Test that model trains without error."""
    model = MyModel()
    X_train, y_train = load_test_data()
    model.fit(X_train, y_train)
    assert model.is_fitted_

def test_invalid_input():
    """Test proper error handling."""
    with pytest.raises(ValueError):
        process_invalid_data()
```

## Docstring Format (NumPy Style)

```python
def train_model(X: pd.DataFrame, y: pd.Series, n_estimators: int = 100) -> object:
    """
    Train a random forest model.

    Parameters
    ----------
    X : pd.DataFrame
        Feature matrix with shape (n_samples, n_features)
    y : pd.Series
        Target variable with shape (n_samples,)
    n_estimators : int, default=100
        Number of trees in the forest

    Returns
    -------
    model : RandomForestClassifier
        Trained model instance

    Raises
    ------
    ValueError
        If X and y have mismatched lengths
    """
```

## File Operations

Use pathlib:
```python
from pathlib import Path

# Good
data_path = Path("shared_data") / "results.parquet"
if data_path.exists():
    df = pd.read_parquet(data_path)

# Bad - don't do this
data_path = "shared_data/results.parquet"
```
```

---

## 6. Agent Workflow Setup

### Create `.github/workflows/copilot-setup-steps.yml`

```yaml
name: copilot-setup-steps

on:
  workflow_dispatch:

jobs:
  copilot-setup-steps:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Setup R
        uses: r-lib/actions/setup-r@v2
        with:
          r-version: '4.4.0'

      - name: Install R dependencies
        run: |
          Rscript -e "install.packages(c('languageserver', 'arrow', 'testthat', 'roxygen2'))"
          Rscript -e "BiocManager::install(c('BiocCheck', 'SummarizedExperiment'))"

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install Python dependencies
        run: |
          pip install -r python/requirements.txt
          pip install pytest mypy

      - name: Verify BiocCheck
        run: Rscript -e "BiocCheck::BiocCheck('r/')"

      - name: Run Python tests
        run: pytest python/tests/
```

---

## 7. Using GitHub Copilot Effectively

### Enable Copilot Agent Mode
1. Press `Ctrl+Shift+P` / `Cmd+Shift+P`
2. Type "GitHub Copilot: Chat"
3. In chat window, type `@workspace` to give context about entire project

### Agent Commands for Your Workflow

**For R/Bioconductor tasks:**
```
@workspace Create a new S4 class for storing RNA-seq results that extends SummarizedExperiment. Include slots for normalized counts and differential expression results. Follow Bioconductor standards.
```

**For Python ML tasks:**
```
@workspace Build a scikit-learn pipeline that loads data from shared_data/preprocessed.parquet, performs feature scaling, trains a random forest, and exports predictions back to parquet. Include type hints and pytest tests.
```

**For data handoff:**
```
@workspace Write an R function that processes a SummarizedExperiment object and exports the assay data and colData to shared_data/ as a parquet file that Python can load.
```

### Copilot Chat Best Practices
- Always mention if you're working in R or Python context
- Reference your instruction files: "Following the standards in .github/copilot-instructions.md..."
- Ask for tests: "...and include testthat/pytest tests"
- Request documentation: "...with roxygen2/NumPy docstrings"

---

## 8. Keyboard Shortcuts

### Essential Copilot Shortcuts
- **Ctrl+I** / **Cmd+I**: Inline Copilot chat
- **Ctrl+Shift+I** / **Cmd+Shift+I**: Open Copilot chat panel
- **Tab**: Accept Copilot suggestion
- **Alt+]**: Next suggestion
- **Alt+[**: Previous suggestion

### VS Code Shortcuts
- **Ctrl+`**: Toggle terminal
- **Ctrl+Shift+P**: Command palette
- **Ctrl+P**: Quick file open
- **F12**: Go to definition
- **Shift+F12**: Find references

---

## 9. Testing Your Setup

### Test R Integration
1. Create `test.R` in your r/ folder
2. Type: `library(arrow)`
3. Copilot should auto-complete
4. In terminal: `Rscript test.R`

### Test Python Integration
1. Create `test.py` in your python/ folder
2. Type: `import pyarrow`
3. Copilot should auto-complete
4. In terminal: `python test.py`

### Test Data Handoff
Create this test workflow:

**R script (r/export_test.R):**
```r
library(arrow)
df <- data.frame(gene = paste0("gene", 1:100), expression = rnorm(100))
write_parquet(df, "../shared_data/test.parquet")
```

**Python script (python/import_test.py):**
```python
import pyarrow.parquet as pq
from pathlib import Path

df = pq.read_table("../shared_data/test.parquet").to_pandas()
print(f"Loaded {len(df)} rows")
```

Run both and verify data transfer works without reticulate!

---

## 10. Troubleshooting

### R Language Server Not Working
- Restart VS Code
- Check R path in settings
- Reinstall: `install.packages("languageserver")`

### Copilot Not Suggesting
- Check GitHub Copilot status (bottom right)
- Reload window: `Ctrl+Shift+P` > "Reload Window"
- Verify instructions files are named correctly

### BiocCheck Fails
- Review: https://bioconductor.org/packages/release/bioc/vignettes/BiocCheck/inst/doc/BiocCheck.html
- Common issues: Missing roxygen2, wrong class usage

---

## Next Steps

1. **Initialize your project** with the folder structure above
2. **Create all instruction files** from this guide
3. **Test Copilot agent mode** with a simple task
4. **Iterate on instructions** as you discover project-specific patterns
5. **Document your workflow** in project README

Your Copilot agents will now understand:
- When to use R vs Python
- Bioconductor-specific standards
- How to exchange data via Arrow (no reticulate!)
- Testing requirements for both languages
- Documentation standards for each language

**Remember**: Copilot learns from your instructions over time. The more specific you are in `.github/copilot-instructions.md`, the better your agents will perform!
