"""Scrape NHANES laboratory variable list to find all pesticide-related variables.

This script visits the NHANES variable list page and identifies all pesticide
measurements by filtering the Data File Description for 'pesticide'.

Usage:
    python scripts/discover_nhanes_pesticides.py [--cycle CYCLE] [--save output.csv]

Requires: requests, beautifulsoup4, pandas
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

import pandas as pd
import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent.parent

NHANES_VAR_LIST_BASE = "https://wwwn.cdc.gov/nchs/nhanes/search/variablelist.aspx?Component=Laboratory"


def scrape_pesticide_variables(cycle: str | None = None) -> pd.DataFrame:
    """Scrape NHANES laboratory variable list for pesticide variables.

    Parameters
    ----------
    cycle : str, optional
        NHANES cycle (e.g., "2017-2018"). If None, scrapes all cycles.

    Returns
    -------
    pd.DataFrame
        Columns: variable_name, variable_description, data_file_description,
                 data_file_name, cycle
    """
    url = NHANES_VAR_LIST_BASE
    if cycle:
        url += f"&Cycle={cycle}"

    print(f"Fetching: {url}")

    session = requests.Session()
    session.headers.update(
        {"User-Agent": ("PopHealthObservatory/0.7.0 " "(https://github.com/paulboys/PopHealth-Observatory)")}
    )

    try:
        resp = session.get(url, timeout=30)
        resp.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"ERROR: Failed to fetch page: {e}")
        sys.exit(1)

    soup = BeautifulSoup(resp.text, "html.parser")

    # Find the results table
    # The page typically has a GridView table with variable information
    table = soup.find("table", {"id": lambda x: x and "gridView" in x.lower()})

    if not table:
        # Try finding any table with relevant headers
        tables = soup.find_all("table")
        for t in tables:
            headers = [th.get_text(strip=True) for th in t.find_all("th")]
            if "Variable Name" in headers or "Variable" in headers:
                table = t
                break

    if not table:
        print("ERROR: Could not find variable table on page")
        print("Available tables:")
        for t in soup.find_all("table"):
            print(f"  Table ID: {t.get('id', 'no-id')}")
        sys.exit(1)

    # Parse table
    rows = table.find_all("tr")
    if not rows:
        print("ERROR: No rows found in table")
        sys.exit(1)

    # Extract headers
    headers = [th.get_text(strip=True) for th in rows[0].find_all("th")]
    print(f"Found headers: {headers}")

    # Parse data rows
    data: list[dict[str, Any]] = []
    for row in rows[1:]:
        cells = row.find_all("td")
        if len(cells) != len(headers):
            continue

        row_data = {headers[i]: cells[i].get_text(strip=True) for i in range(len(cells))}
        data.append(row_data)

    print(f"Total rows extracted: {len(data)}")

    # Convert to DataFrame
    df = pd.DataFrame(data)

    if df.empty:
        print("ERROR: No data extracted from table")
        sys.exit(1)

    # Normalize column names (handle variations)
    col_mapping = {}
    for col in df.columns:
        col_lower = col.lower()
        if "variable" in col_lower and "name" in col_lower:
            col_mapping[col] = "variable_name"
        elif "variable" in col_lower and "desc" in col_lower:
            col_mapping[col] = "variable_description"
        elif "data file" in col_lower and "desc" in col_lower:
            col_mapping[col] = "data_file_description"
        elif "data file" in col_lower and "name" in col_lower:
            col_mapping[col] = "data_file_name"
        elif "begin year" in col_lower or "cycle" in col_lower:
            col_mapping[col] = "cycle"

    df = df.rename(columns=col_mapping)

    print(f"Normalized columns: {list(df.columns)}")

    # Filter for pesticide-related variables
    if "data_file_description" not in df.columns:
        print("ERROR: 'data_file_description' column not found")
        print(f"Available columns: {list(df.columns)}")
        sys.exit(1)

    df_pesticide = df[df["data_file_description"].str.contains("pesticide", case=False, na=False)].copy()

    print(f"\nFound {len(df_pesticide)} pesticide-related variables")

    return df_pesticide


def is_chemical_variable(var_name: str, description: str) -> bool:
    """Determine if a variable represents a chemical analyte concentration.

    Exclude non-chemical variables such as:
    - Administrative/identifiers (pool IDs, sequence numbers)
    - Demographics (age, gender, ethnicity)
    - Survey weights (MEC, jackknife replicates)
    - Comment codes (detection flags)
    - Normalization helpers (creatinine)
    - Sampling metadata

    Parameters
    ----------
    var_name : str
        Variable name
    description : str
        Variable description

    Returns
    -------
    bool
        True if variable is a chemical analyte, False otherwise
    """
    v = var_name.lower()
    d = description.lower()

    # Exclude weight variables (survey weights, replicate weights)
    if v.startswith("wt"):
        return False

    # Exclude comment code variables (typically end with LC)
    if v.endswith("lc"):
        return False

    # Exclude common non-chemical keywords in descriptions
    non_chemical_keywords = [
        "comment",
        "comment code",
        "weight",
        "jack knife",
        "jackknife",
        "creatinine",
        "pool id",
        "sequence number",
        "age group",
        "gender",
        "ethnicity",
        "race",
        "recode",
        "subsample",
        "number of samples",
        "identification number",
    ]

    for keyword in non_chemical_keywords:
        if keyword in d:
            return False

    return True


def filter_to_chemical_variables(df: pd.DataFrame) -> pd.DataFrame:
    """Filter DataFrame to retain only chemical analyte variables.

    Parameters
    ----------
    df : pd.DataFrame
        Scraped pesticide variables

    Returns
    -------
    pd.DataFrame
        Filtered DataFrame containing only chemical variables
    """
    if "variable_name" not in df.columns or "variable_description" not in df.columns:
        print("ERROR: Required columns not found for filtering")
        print(f"Available columns: {list(df.columns)}")
        return df

    mask = df.apply(
        lambda row: is_chemical_variable(row["variable_name"], row["variable_description"]),
        axis=1,
    )

    filtered = df[mask].copy()
    removed_count = len(df) - len(filtered)

    print(f"Filtered out {removed_count} non-chemical variables")
    print(f"Retained {len(filtered)} chemical analyte variables")

    return filtered


def get_unique_variables(df: pd.DataFrame) -> pd.DataFrame:
    """Get unique combinations of variable name and description.

    Parameters
    ----------
    df : pd.DataFrame
        Scraped pesticide variables

    Returns
    -------
    pd.DataFrame
        Unique variable_name, variable_description pairs with counts
    """
    if "variable_name" not in df.columns or "variable_description" not in df.columns:
        print("ERROR: Required columns not found")
        print(f"Available columns: {list(df.columns)}")
        sys.exit(1)

    unique = (
        df.groupby(
            [
                "variable_name",
                "variable_description",
                "data_file_description",
                "data_file_name",
            ]
        )
        .size()
        .reset_index(name="occurrence_count")
        .sort_values("variable_name")
    )

    return unique


def main():
    """Run scraper from command line."""
    parser = argparse.ArgumentParser(description="Discover all pesticide variables in NHANES laboratory data")
    parser.add_argument(
        "--cycle",
        type=str,
        help="Specific NHANES cycle (e.g., '2017-2018'). If omitted, scrapes all cycles.",
    )
    parser.add_argument("--save", type=str, help="Save results to CSV file (e.g., pesticide_vars.csv)")
    parser.add_argument(
        "--detailed",
        action="store_true",
        help="Show detailed results (all cycles) instead of unique summary",
    )
    parser.add_argument(
        "--include-non-chemicals",
        action="store_true",
        help="Include non-chemical variables (weights, IDs, demographics, etc.)",
    )
    args = parser.parse_args()

    # Scrape data
    df_pesticide = scrape_pesticide_variables(cycle=args.cycle)

    if df_pesticide.empty:
        print("\nNo pesticide variables found.")
        sys.exit(0)

    # Filter to chemical variables unless user explicitly wants all
    if not args.include_non_chemicals:
        df_pesticide = filter_to_chemical_variables(df_pesticide)

        if df_pesticide.empty:
            print("\nNo chemical variables remaining after filtering.")
            sys.exit(0)

    # Get unique variables
    if args.detailed:
        result = df_pesticide[
            [
                "variable_name",
                "variable_description",
                "data_file_description",
                "data_file_name",
                "cycle",
            ]
        ].sort_values(["variable_name", "cycle"])
        print("\n" + "=" * 80)
        print("DETAILED PESTICIDE VARIABLES (All Cycles)")
        print("=" * 80)
    else:
        result = get_unique_variables(df_pesticide)
        print("\n" + "=" * 80)
        print("UNIQUE PESTICIDE VARIABLES (Variable Name + Description)")
        print("=" * 80)

    print(result["variable_description"].drop_duplicates().to_string(index=False))
    print("\n" + "=" * 80)
    print(f"Total unique variables: {len(result)}")
    print("=" * 80)

    # Save if requested
    if args.save:
        output_path = Path(args.save)
        result.to_csv(output_path, index=False)
        print(f"\n✓ Results saved to: {output_path}")


if __name__ == "__main__":
    main()
