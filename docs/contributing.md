# Contributing

For the complete contribution workflow, use the repository-level guide: [CONTRIBUTING.md](https://github.com/paulboys/PopHealth-Observatory/blob/main/CONTRIBUTING.md).

## Quick Contributor Flow

1. Open or confirm an issue for non-trivial changes.
2. Create a focused branch (`feat/<short>`, `fix/<short>`, `docs/<short>`, or `chore/<short>`).
3. Run local quality checks:
   - `pre-commit run --all-files`
   - `ruff check .`
   - `black --check .`
   - `pytest -q`
4. Update docs and `CHANGELOG.md` for user-facing changes.
5. Open a PR with validation notes.

## Related Contributor Docs

- [Versioning & Releases](versioning.md)
- [Pre-commit Hooks](pre-commit.md)
- [Architecture](architecture.md)
