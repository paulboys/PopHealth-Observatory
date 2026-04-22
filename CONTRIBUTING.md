# Contributing to PopHealth Observatory

Thanks for contributing. This guide is the single source of truth for contribution workflow, quality gates, and review expectations.

## Before You Start

1. Search existing issues/PRs for related work.
2. Open an issue (bug, feature, design) for non-trivial changes before implementation.
3. Keep PR scope focused: one change theme per PR.

## Environment Setup

Prerequisites:
- Python 3.10+
- Quarto (required)
- SciClaw 0.2.8+ (minimum supported)

Setup:

```bash
git clone https://github.com/paulboys/PopHealth-Observatory.git
cd PopHealth-Observatory
python -m venv .venv
# Windows PowerShell
./.venv/Scripts/Activate.ps1
pip install -e .[dev]
```

Validate tooling:

```bash
quarto check
sciclaw --version
pre-commit install
```

## Branching and Commits

Branch naming:
- `feat/<short-description>`
- `fix/<short-description>`
- `docs/<short-description>`
- `chore/<short-description>`

Use conventional commits whenever possible:
- `feat:` for new functionality
- `fix:` for bug fixes
- `docs:` for docs-only changes
- `test:` for test changes
- `refactor:` for internal behavior-preserving refactors
- `chore:` for maintenance

Version automation details live in [docs/versioning.md](docs/versioning.md).

## Code Standards

1. Use `Path` for filesystem paths.
2. Add type hints to all public functions and methods.
3. Keep transformations separate from I/O where practical.
4. Precompile regex patterns before iteration-heavy loops.
5. Prefer narrow exceptions and explicit failure behavior.
6. Use NumPy-style docstrings for new public APIs.

## Tests and Quality Gates

Run locally before opening a PR:

```bash
pre-commit run --all-files
ruff check .
black --check .
pytest -q
```

When touching critical logic, also run coverage:

```bash
coverage run -m pytest && coverage report -m
```

Testing guidance:
- Add deterministic tests for any new behavior.
- Use `tmp_path` for filesystem side effects.
- Cover edge cases (empty input, malformed records, boundary conditions).

Pre-commit behavior and troubleshooting live in [docs/pre-commit.md](docs/pre-commit.md).

## Documentation Expectations

Update docs in the same PR when behavior changes:
- `README.md` for user-facing usage changes.
- `docs/` pages for detailed guidance.
- `CHANGELOG.md` for user-visible changes.

For architecture-impacting changes, update [docs/architecture.md](docs/architecture.md).

## Pull Request Checklist

Before requesting review, verify:

1. Tests pass locally.
2. Lint/format checks pass.
3. Docs are updated for changed behavior.
4. `CHANGELOG.md` is updated if user-facing.
5. PR description explains intent, approach, and validation done.

## Review and Merge Expectations

1. Keep review comments actionable and specific.
2. Prefer follow-up commits (no force-push required unless requested).
3. Resolve CI failures before requesting re-review.
4. Squash or merge strategy follows repository maintainers' preference.

## Security and Data Handling

1. Do not commit secrets, tokens, or credentials.
2. Avoid committing large generated artifacts (>10MB) unless explicitly required.
3. Keep external network calls bounded with explicit timeouts.

## Questions

Open a GitHub issue or discussion for design questions before large refactors.
