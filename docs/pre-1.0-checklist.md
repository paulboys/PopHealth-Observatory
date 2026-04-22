# Pre-1.0 Release Readiness Checklist

This checklist tracks final stabilization tasks before a 1.0 release.

> Archived after v1.0.0 release.
> This page is retained as release history evidence and no longer reflects active work.

## Documentation and Deprecation Policy

- [x] Deprecation policy documented in README (`Deprecation and Compatibility Policy` section)
- [x] Deprecation/removal contract documented in `docs/versioning.md`
- [x] Unreleased changelog entries include deprecation timeline guidance
- [x] Root-level compatibility shim timeline documented (`no earlier than 2.0.0`; target date: `2027-06-30`)

## API and Compatibility Safeguards

- [x] Root export shims emit `DeprecationWarning` with explicit replacement imports
- [x] Root export shims include explicit planned removal version (`2.0.0`) and firm target date (`2027-06-30`)
- [x] Shim behavior covered by contract tests (`tests/test_init_shims.py`)
- [x] Protocol adapter composition preserves public explorer behavior

## CI and Quality Gates

- [x] Lint checks enforced in CI
- [x] Test matrix enforced in CI
- [x] Decomposition contract suite enforced in CI
- [x] Coverage fail-under for decomposition modules enabled in CI

## Pre-1.0 Final Gate (To Execute at Release Time)

- [x] Decide final action for deprecated root exports: retain through 1.0 and defer removal to no earlier than 2.0.0 (`2027-06-30` target)
- [x] If removing shims, update all docs/examples to submodule imports only (N/A: shims retained through 1.x)
- [x] Add a dedicated `1.0.0` release-notes page with migration guidance
- [x] Validate no unresolved deprecation-policy inconsistencies in docs
- [x] Run full repository test and strict docs build at tag time (CI-enforced)
