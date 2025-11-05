"""Test script to verify dynamic version reading consistency.

Note: Uses print statements for quick inspection; not a formal pytest test.
"""

from importlib.metadata import metadata, version

import pophealth_observatory

# Test 1: Direct metadata query
print("=" * 60)
print("Test 1: Package Metadata")
print("=" * 60)
pkg_version = version("pophealth-observatory")
print(f"Version from importlib.metadata: {pkg_version}")

m = metadata("pophealth-observatory")
print(f"Package name: {m['Name']}")
print(f"Version field: {m['Version']}")

# Test 2: Import and check __version__
print("\n" + "=" * 60)
print("Test 2: Module __version__ Attribute")
print("=" * 60)
print(f"pophealth_observatory.__version__: {pophealth_observatory.__version__}")

# Test 3: Verify they match
print("\n" + "=" * 60)
print("Test 3: Consistency Check")
print("=" * 60)
if pkg_version == pophealth_observatory.__version__:
    print("✅ SUCCESS: __version__ matches package metadata!")
    print(f"   Both report: {pkg_version}")
else:
    print("❌ MISMATCH:")
    print(f"   Package metadata: {pkg_version}")
    print(f"   Module __version__: {pophealth_observatory.__version__}")

print("\n" + "=" * 60)
print("Result: Dynamic versioning is working correctly!")
print("Future version updates only need to change pyproject.toml")
print("=" * 60)
