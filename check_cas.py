import pandas as pd

df = pd.read_csv("data/reference/pesticide_reference_minimal.csv")

print(f"Total analytes: {len(df)}")
print(f"With non-empty CAS: {df['cas_rn'].notna().sum()}")
print(f"Empty CAS: {df['cas_rn'].isna().sum() + (df['cas_rn'] == '').sum()}")
print(f"Verified source = 'pubchem_api': {(df['cas_verified_source'] == 'pubchem_api').sum()}")
print(f"Verified source empty: {(df['cas_verified_source'] == '').sum()}")

print("\nSample of unverified analytes:")
unverified = df[df["cas_verified_source"] == ""]
print(unverified[["variable_name", "analyte_name", "cas_rn"]].head(10))
