"""Diagnostic script for blood pressure component download.

Note: Intended for manual troubleshooting; not part of automated test suite.
"""

from pophealth_observatory import NHANESExplorer

explorer = NHANESExplorer()
cycle = "2017-2018"  # Known working cycle

print("=" * 70)
print(f"Testing blood pressure download for cycle: {cycle}")
print("=" * 70)

# Download raw BPX data
print("\n1. Downloading raw BPX data...")
bp_df = explorer.download_data(cycle, explorer.components["blood_pressure"])

print(f"\nRaw DataFrame shape: {bp_df.shape}")
print(f"Raw DataFrame columns ({len(bp_df.columns)} total):")
print(list(bp_df.columns))

# Check for expected columns
expected_cols = ["SEQN", "BPXSY1", "BPXDI1", "BPXSY2", "BPXDI2", "BPXSY3", "BPXDI3"]
print("\n2. Checking for expected columns...")
for col in expected_cols:
    status = "✓" if col in bp_df.columns else "✗"
    print(f"  {status} {col}")

# Try get_blood_pressure
print("\n3. Testing get_blood_pressure() method...")
bp_clean = explorer.get_blood_pressure(cycle)
print(f"Cleaned DataFrame shape: {bp_clean.shape}")
print("Cleaned DataFrame columns:")
print(list(bp_clean.columns))

if bp_clean.empty or len(bp_clean.columns) <= 1:
    print("\n❌ PROBLEM CONFIRMED: get_blood_pressure returns empty or nearly-empty DataFrame")
    print("   Even though download_data reported 'Success'")
else:
    print("\n✓ Blood pressure data looks OK")
    print("Sample data:")
    print(bp_clean.head())
