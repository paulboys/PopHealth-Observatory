"""Diagnostic script for blood pressure component download.

Note: Intended for manual troubleshooting; not part of automated test suite.
"""

import logging

from pophealth_observatory.logging_config import configure_logging, log_with_fallback
from pophealth_observatory.observatory import NHANESExplorer

logger = logging.getLogger(__name__)

configure_logging()

explorer = NHANESExplorer()
cycle = "2017-2018"  # Known working cycle

log_with_fallback(logger, logging.INFO, "=" * 70)
log_with_fallback(logger, logging.INFO, f"Testing blood pressure download for cycle: {cycle}")
log_with_fallback(logger, logging.INFO, "=" * 70)

# Download raw BPX data
log_with_fallback(logger, logging.INFO, "1. Downloading raw BPX data...")
bp_df = explorer.download_data(cycle, explorer.components["blood_pressure"])

log_with_fallback(logger, logging.INFO, f"Raw DataFrame shape: {bp_df.shape}")
log_with_fallback(logger, logging.INFO, f"Raw DataFrame columns ({len(bp_df.columns)} total):")
log_with_fallback(logger, logging.INFO, str(list(bp_df.columns)))

# Check for expected columns
expected_cols = ["SEQN", "BPXSY1", "BPXDI1", "BPXSY2", "BPXDI2", "BPXSY3", "BPXDI3"]
log_with_fallback(logger, logging.INFO, "2. Checking for expected columns...")
for col in expected_cols:
    status = "OK" if col in bp_df.columns else "MISSING"
    level = logging.INFO if status == "OK" else logging.WARNING
    log_with_fallback(logger, level, f"  {status} {col}")

# Try get_blood_pressure
log_with_fallback(logger, logging.INFO, "3. Testing get_blood_pressure() method...")
bp_clean = explorer.get_blood_pressure(cycle)
log_with_fallback(logger, logging.INFO, f"Cleaned DataFrame shape: {bp_clean.shape}")
log_with_fallback(logger, logging.INFO, "Cleaned DataFrame columns:")
log_with_fallback(logger, logging.INFO, str(list(bp_clean.columns)))

if bp_clean.empty or len(bp_clean.columns) <= 1:
    log_with_fallback(
        logger,
        logging.WARNING,
        "PROBLEM CONFIRMED: get_blood_pressure returns empty or nearly-empty DataFrame",
    )
    log_with_fallback(logger, logging.WARNING, "   Even though download_data reported 'Success'")
else:
    log_with_fallback(logger, logging.INFO, "Blood pressure data looks OK")
    log_with_fallback(logger, logging.INFO, "Sample data:")
    log_with_fallback(logger, logging.INFO, f"\n{bp_clean.head()}")
