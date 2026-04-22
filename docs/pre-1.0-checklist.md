# Pre-1.0 Release Readiness Checklist

This checklist tracks final stabilization tasks before a 1.0 release.

## Documentation and Deprecation Policy

- [x] Deprecation policy documented in README (`Deprecation and Compatibility Policy` section)
- [x] Deprecation/removal contract documented in `docs/versioning.md`
- [x] Unreleased changelog entries include deprecation timeline guidance
- [x] Root-level compatibility shim timeline documented (`planned removal in 1.0.0`)

## API and Compatibility Safeguards

- [x] Root export shims emit `DeprecationWarning` with explicit replacement imports
- [x] Root export shims include explicit planned removal version (`1.0.0`)
- [x] Shim behavior covered by contract tests (`tests/test_init_shims.py`)
- [x] Protocol adapter composition preserves public explorer behavior

## CI and Quality Gates

- [x] Lint checks enforced in CI
- [x] Test matrix enforced in CI
- [x] Decomposition contract suite enforced in CI
- [x] Coverage fail-under for decomposition modules enabled in CI

## Pre-1.0 Final Gate (To Execute at Release Time)

- [ ] Decide final action for deprecated root exports: retain through 1.0 or remove in 1.0 with migration note
- [ ] If removing shims, update all docs/examples to submodule imports only
- [ ] Add a dedicated `1.0.0` release-notes page with migration guidance
- [ ] Validate no unresolved deprecation-policy inconsistencies in docs
- [ ] Run full repository test and docs build before tagging
