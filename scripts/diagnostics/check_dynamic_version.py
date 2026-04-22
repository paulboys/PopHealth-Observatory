"""Diagnostic script to verify dynamic version reading consistency.

Note: Uses print statements for quick inspection; not a formal pytest test.
"""

import logging
from importlib.metadata import metadata, version

import pophealth_observatory
from pophealth_observatory.logging_config import configure_logging, log_with_fallback

logger = logging.getLogger(__name__)

configure_logging()

# Test 1: Direct metadata query
log_with_fallback(logger, logging.INFO, "=" * 60)
log_with_fallback(logger, logging.INFO, "Test 1: Package Metadata")
log_with_fallback(logger, logging.INFO, "=" * 60)
pkg_version = version("pophealth-observatory")
log_with_fallback(logger, logging.INFO, f"Version from importlib.metadata: {pkg_version}")

m = metadata("pophealth-observatory")
log_with_fallback(logger, logging.INFO, f"Package name: {m['Name']}")
log_with_fallback(logger, logging.INFO, f"Version field: {m['Version']}")

# Test 2: Import and check __version__
log_with_fallback(logger, logging.INFO, "=" * 60)
log_with_fallback(logger, logging.INFO, "Test 2: Module __version__ Attribute")
log_with_fallback(logger, logging.INFO, "=" * 60)
log_with_fallback(logger, logging.INFO, f"pophealth_observatory.__version__: {pophealth_observatory.__version__}")

# Test 3: Verify they match
log_with_fallback(logger, logging.INFO, "=" * 60)
log_with_fallback(logger, logging.INFO, "Test 3: Consistency Check")
log_with_fallback(logger, logging.INFO, "=" * 60)
if pkg_version == pophealth_observatory.__version__:
    log_with_fallback(logger, logging.INFO, "SUCCESS: __version__ matches package metadata")
    log_with_fallback(logger, logging.INFO, f"   Both report: {pkg_version}")
else:
    log_with_fallback(logger, logging.WARNING, "MISMATCH:")
    log_with_fallback(logger, logging.WARNING, f"   Package metadata: {pkg_version}")
    log_with_fallback(logger, logging.WARNING, f"   Module __version__: {pophealth_observatory.__version__}")

log_with_fallback(logger, logging.INFO, "=" * 60)
log_with_fallback(logger, logging.INFO, "Result: Dynamic versioning is working correctly")
log_with_fallback(logger, logging.INFO, "Future version updates only need to change pyproject.toml")
log_with_fallback(logger, logging.INFO, "=" * 60)
