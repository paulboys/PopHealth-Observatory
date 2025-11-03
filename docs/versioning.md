# Automated Version Bumping & Publishing

## Overview
This repository uses automated semantic versioning via GitHub Actions. When code is pushed to `main`, the version is automatically bumped based on commit message conventions, and a new release is published to PyPI.

## Commit Message Convention

The version bump type is determined by your commit message:

| Commit Message Pattern | Version Bump | Example |
|------------------------|--------------|---------|
| Contains `[major]` or `BREAKING CHANGE` | **MAJOR** (x.0.0) | `feat: new API [major]` → 0.2.1 → 1.0.0 |
| Starts with `feat` or contains `[minor]` or `[feature]` | **MINOR** (0.x.0) | `feat: add new loader` → 0.2.1 → 0.3.0 |
| All other commits | **PATCH** (0.0.x) | `fix: typo in docstring` → 0.2.1 → 0.2.2 |

### Examples

```bash
# PATCH bump (0.2.1 → 0.2.2)
git commit -m "fix: correct BMI calculation edge case"
git commit -m "docs: update README examples"
git commit -m "refactor: simplify regex pattern"

# MINOR bump (0.2.1 → 0.3.0)
git commit -m "feat: add dietary intake loader"
git commit -m "feature: add export to CSV [minor]"

# MAJOR bump (0.2.1 → 1.0.0)
git commit -m "feat: redesign API with async support [major]"
git commit -m "BREAKING CHANGE: remove deprecated methods"
```

## Skipping Auto-Version

To push changes without triggering a version bump:

```bash
git commit -m "chore: update CI config [skip-version]"
```

The workflow also automatically skips commits it creates (those containing "Bump version to").

## Workflow Details

### Trigger Paths
The auto-version workflow only runs when these paths change:
- `pophealth_observatory/**` (library code)
- `tests/**` (test suite)
- `pyproject.toml` (package metadata)
- `requirements.txt` (dependencies)

Changes to docs, notebooks, or CI configs won't trigger version bumps unless you explicitly want them to.

### What Happens Automatically

1. **Version Bump**: `.github/workflows/auto-version.yml` parses your commit message
2. **Update pyproject.toml**: Version string is updated
3. **Commit & Push**: Automated commit with message like `Bump version to 0.2.2 [skip-ci]`
4. **Create Tag**: Git tag `v0.2.2` is created and pushed
5. **Publish to PyPI**: The tag push triggers `.github/workflows/publish.yml` which:
   - Builds the wheel and source distribution
   - Verifies the wheel can be imported
   - Publishes to PyPI (requires `PYPI_API_TOKEN` secret)
   - Deploys documentation to GitHub Pages

### Required GitHub Secrets

- `PYPI_API_TOKEN`: PyPI API token for automated publishing (already configured)

## Manual Publishing

If you need to publish manually:

```bash
# Update version in pyproject.toml
vim pyproject.toml  # Change version = "0.2.1" to "0.2.2"

# Build and publish
python -m build
twine check dist/*
twine upload dist/*

# Tag and push
git tag v0.2.2
git push origin v0.2.2
```

## Version History

Check `CHANGELOG.md` for the full version history and release notes.

## Troubleshooting

**Q: My commit didn't trigger a version bump**
- Verify your commit touched one of the trigger paths
- Check that the commit message doesn't contain `[skip-version]` or "Bump version to"
- Review the Actions tab in GitHub for workflow logs

**Q: PyPI publish failed**
- Check that `PYPI_API_TOKEN` secret is valid
- Verify the version doesn't already exist on PyPI (PyPI doesn't allow re-uploading the same version)
- Review build logs for setuptools/metadata issues

**Q: I want to publish without waiting for CI**
- Use the manual publishing steps above
- Or create a tag manually: `git tag v0.2.2 && git push origin v0.2.2`
