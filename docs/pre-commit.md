# Pre-commit Setup

This project uses [pre-commit](https://pre-commit.com/) to enforce code quality checks before commits.

## Installation

After cloning the repository and setting up your virtual environment:

```bash
# Install development dependencies (includes pre-commit)
pip install -e .[dev]

# Install the pre-commit hooks
pre-commit install
```

## What Gets Checked

The pre-commit hooks automatically run:

1. **Black** - Code formatting (Python 3.10+ style, 120 char line length)
2. **Ruff** - Fast Python linter with auto-fixes
3. **Trailing whitespace** - Remove trailing spaces
4. **End of file fixer** - Ensure files end with newline
5. **YAML syntax** - Validate YAML files
6. **Large files** - Prevent commits of files >2MB
7. **Merge conflicts** - Detect unresolved merge markers
8. **Line endings** - Normalize to LF

## Usage

### Automatic (Recommended)

Once installed, hooks run automatically on `git commit`. If any check fails, the commit is blocked and issues are reported.

```bash
git add .
git commit -m "feat: add new feature"
# Hooks run automatically
```

### Manual Run

Run checks on all files without committing:

```bash
# Check all files
pre-commit run --all-files

# Check specific files
pre-commit run --files path/to/file.py
```

### Bypassing Hooks (Use Sparingly)

In rare cases where you need to commit without running hooks:

```bash
git commit --no-verify -m "emergency fix"
```

⚠️ **Warning**: Bypassing hooks may cause CI failures. Use only when necessary.

## Updating Hooks

Pre-commit hooks are versioned in `.pre-commit-config.yaml`. To update to latest versions:

```bash
pre-commit autoupdate
```

## Troubleshooting

### Hooks not running

```bash
# Reinstall hooks
pre-commit uninstall
pre-commit install
```

### Clear hook cache

```bash
pre-commit clean
pre-commit install --install-hooks
```

### Skip specific hooks

Add to commit message or set environment variable:

```bash
# Skip a specific hook
SKIP=black git commit -m "message"

# Skip all hooks (same as --no-verify)
SKIP=all git commit -m "message"
```

## CI Integration

The same checks run in GitHub Actions CI (`ci.yml`), so passing pre-commit locally ensures CI will pass.

## Configuration

Pre-commit configuration is in `.pre-commit-config.yaml`:
- Hook versions are pinned for reproducibility
- Notebooks and site directories are excluded
- Black/Ruff settings match `pyproject.toml` configuration

For more details, see: https://pre-commit.com/
