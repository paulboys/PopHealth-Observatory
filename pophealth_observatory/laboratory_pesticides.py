"""NHANES pesticide laboratory analyte ingestion and harmonization.

This module provides structured ingestion of NHANES pesticide biomonitoring data
from urinary metabolites (organophosphates, pyrethroids, herbicides) and serum
persistent organochlorines (legacy pesticides).

Key functions:
  - get_pesticide_metabolites: Load and harmonize analytes for a given cycle
  - Automatic file pattern matching (OPD, UPHOPM, PP series)
  - Column mapping via data/reference/pesticide_reference.csv
  - Derived fields: log concentration, detection flags

Schema compliance: docs/pesticide_biomonitoring_plan.md § 6

SPDX-License-Identifier: MIT
"""

from __future__ import annotations

import io
from pathlib import Path

import numpy as np
import pandas as pd
import requests


def load_analyte_code_map(map_path: Path | None = None) -> dict[str, str]:
    """Load analyte code → name mapping for URX*/LBX* variable translation.

    Parameters
    ----------
    map_path : Path | None
        Path to analyte_code_map.csv; defaults to data/reference/config/analyte_code_map.csv

    Returns
    -------
    dict[str, str]
        Mapping from variable_name (e.g., 'URX3PBA') to analyte_name (e.g., '3-PBA')
    """
    if map_path is None:
        map_path = Path(__file__).parent.parent / "data" / "reference" / "config" / "analyte_code_map.csv"

    if not map_path.exists():
        return {}

    df = pd.read_csv(map_path)
    if df.empty or "variable_name" not in df.columns or "analyte_name" not in df.columns:
        return {}

    return dict(zip(df["variable_name"], df["analyte_name"], strict=True))


def load_pesticide_reference(ref_path: Path | None = None) -> pd.DataFrame:
    """Load curated pesticide analyte reference CSV.

    Parameters
    ----------
    ref_path : Path | None
        Path to pesticide_reference.csv; defaults to data/reference/pesticide_reference.csv

    Returns
    -------
    pd.DataFrame
        Reference table with columns: analyte_name, parent_pesticide, metabolite_class,
        cas_rn, typical_matrix, unit, first_cycle_measured, last_cycle_measured, etc.
    """
    if ref_path is None:
        ref_path = Path(__file__).parent.parent / "data" / "reference" / "pesticide_reference.csv"

    if not ref_path.exists():
        return pd.DataFrame()

    return pd.read_csv(ref_path)


def _parse_cycle_years(cycle: str) -> tuple[int, int]:
    """Extract start and end year from cycle string.

    Parameters
    ----------
    cycle : str
        NHANES cycle in format YYYY-YYYY (e.g., '2017-2018')

    Returns
    -------
    tuple[int, int]
        (start_year, end_year)

    Raises
    ------
    ValueError
        If cycle format invalid
    """
    if not cycle or "-" not in cycle:
        raise ValueError(f"Invalid cycle format: {cycle}. Expected YYYY-YYYY.")

    parts = cycle.split("-")
    if len(parts) != 2:
        raise ValueError(f"Invalid cycle format: {cycle}. Expected YYYY-YYYY.")

    try:
        start_year = int(parts[0])
        end_year = int(parts[1])
        return start_year, end_year
    except ValueError as e:
        # Preserve original parsing error context (ruff B904)
        raise ValueError(f"Cannot parse years from cycle {cycle}: {e}") from e


def _get_cycle_letter_suffix(cycle: str) -> str:
    """Map cycle to NHANES file letter suffix.

    Parameters
    ----------
    cycle : str
        NHANES cycle (e.g., '2017-2018')

    Returns
    -------
    str
        Letter suffix (e.g., 'J' for 2017-2018)

    Raises
    ------
    ValueError
        If cycle not in known mapping
    """
    cycle_suffix_map = {
        "2021-2022": "L",
        "2019-2020": "K",
        "2017-2018": "J",
        "2015-2016": "I",
        "2013-2014": "H",
        "2011-2012": "G",
        "2009-2010": "F",
        "2007-2008": "E",
        "2005-2006": "D",
        "2003-2004": "C",
        "2001-2002": "B",
        "1999-2000": "A",
    }

    if cycle not in cycle_suffix_map:
        raise ValueError(
            f"No letter suffix mapping for cycle '{cycle}'. " f"Supported cycles: {list(cycle_suffix_map.keys())}"
        )

    return cycle_suffix_map[cycle]


def _build_pesticide_file_candidates(cycle: str) -> list[tuple[str, str]]:
    """Generate candidate file patterns for pesticide components.

    NHANES pesticide data appears in multiple file series:
    - OPD: Organophosphate dialkyl phosphate metabolites
    - UPHOPM: Pyrethroids, Herbicides, & Organophosphorus Metabolites (combined)
    - PP: Priority Pesticides / Current Use
    - DOXPOL: Legacy organochlorine pesticides (some cycles)

    Parameters
    ----------
    cycle : str
        NHANES cycle

    Returns
    -------
    list[tuple[str, str]]
        List of (component_code, description) tuples to attempt
    """
    # Validate suffix (previous unused variable triggered F841); ensure cycle recognized
    _get_cycle_letter_suffix(cycle)

    # Priority order based on observed NHANES patterns
    return [
        ("UPHOPM", "Pyrethroids, Herbicides, & OP Metabolites"),
        ("OPD", "Organophosphate Dialkyl Phosphate Metabolites"),
        ("PP", "Priority Pesticides - Current Use"),
        ("DOXPOL", "Dioxins, Furans, & Coplanar PCBs - Pooled"),  # may contain organochlorines
    ]


def _download_xpt_flexible(cycle: str, component: str, timeout: int = 30) -> pd.DataFrame:
    """Download XPT file with multiple URL fallback patterns.

    Mirrors the resilient download logic from PopHealthObservatory.download_data.

    Parameters
    ----------
    cycle : str
        NHANES cycle
    component : str
        File component code (e.g., 'UPHOPM')
    timeout : int
        Request timeout in seconds

    Returns
    -------
    pd.DataFrame
        Parsed XPT data or empty DataFrame if all patterns fail
    """
    letter = _get_cycle_letter_suffix(cycle)
    cycle_year = cycle.split("-")[0]

    base_url = "https://wwwn.cdc.gov/Nchs/Nhanes"
    alt_base_url = "https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public"

    url_patterns = [
        f"{alt_base_url}/{cycle_year}/DataFiles/{component}_{letter}.xpt",
        f"{base_url}/{cycle}/{component}_{letter}.XPT",
        f"{base_url}/{cycle}/{component}_{letter}.xpt",
        f"{base_url}/{cycle}/{component.lower()}_{letter}.XPT",
        f"{base_url}/{cycle}/{component.lower()}_{letter}.xpt",
        f"https://wwwn.cdc.gov/Nchs/Data/Nhanes/{cycle}/{component}_{letter}.XPT",
    ]

    for url in url_patterns:
        try:
            response = requests.get(url, timeout=timeout)
            if response.status_code == 200:
                df = pd.read_sas(io.BytesIO(response.content), format="xport")
                if not df.empty:
                    return df
        except Exception:
            continue  # Try next pattern

    return pd.DataFrame()


def _normalize_column_names(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize column names to lowercase for consistent matching.

    Parameters
    ----------
    df : pd.DataFrame
        Raw XPT DataFrame

    Returns
    -------
    pd.DataFrame
        DataFrame with lowercase column names
    """
    df.columns = [c.lower() for c in df.columns]
    return df


def _extract_analyte_columns(df: pd.DataFrame, ref_df: pd.DataFrame) -> pd.DataFrame:
    """Extract and reshape analyte concentration columns into long format.

    NHANES pesticide files typically have:
    - SEQN (participant ID)
    - Multiple URX*/LBX* columns (analyte concentrations)
    - Optional LOD columns

    Parameters
    ----------
    df : pd.DataFrame
        Raw component DataFrame (normalized columns)
    ref_df : pd.DataFrame
        Reference table with analyte metadata

    Returns
    -------
    pd.DataFrame
        Long-format DataFrame with columns:
        participant_id, analyte_code, concentration_raw
    """
    if df.empty or "seqn" not in df.columns:
        return pd.DataFrame()

    # Identify concentration columns (URX* or LBX* pattern)
    conc_cols = [c for c in df.columns if c.startswith(("urx", "lbx")) and not c.endswith(("lc", "si"))]

    if not conc_cols:
        return pd.DataFrame()

    # Pivot to long format
    id_cols = ["seqn"]
    value_vars = conc_cols

    df_long = df.melt(id_vars=id_cols, value_vars=value_vars, var_name="analyte_code", value_name="concentration_raw")

    df_long = df_long.rename(columns={"seqn": "participant_id"})

    return df_long


def _map_to_reference(
    df_long: pd.DataFrame, ref_df: pd.DataFrame, code_map: dict[str, str] | None = None
) -> pd.DataFrame:
    """Map raw analyte codes to normalized reference names and metadata.

    Parameters
    ----------
    df_long : pd.DataFrame
        Long-format data with analyte_code column
    ref_df : pd.DataFrame
        Reference table
    code_map : dict[str, str] | None
        Variable name to analyte name mapping (optional)

    Returns
    -------
    pd.DataFrame
        Enriched DataFrame with canonical analyte_name instead of raw code
    """
    if df_long.empty:
        return df_long

    # Apply code mapping if available (URX*/LBX* → canonical names)
    if code_map:
        # Convert analyte_code to uppercase for case-insensitive matching
        df_long["analyte_code_upper"] = df_long["analyte_code"].str.upper()
        df_long["analyte_name"] = df_long["analyte_code_upper"].map(code_map)
        # Fallback to raw code if unmapped
        df_long["analyte_name"] = df_long["analyte_name"].fillna(df_long["analyte_code"])
        df_long.drop(columns=["analyte_code_upper"], inplace=True)
    else:
        # No map available; use raw code as analyte_name
        df_long["analyte_name"] = df_long["analyte_code"]

    return df_long


def _derive_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """Add derived fields: log concentration, detection flag.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame with concentration_raw column

    Returns
    -------
    pd.DataFrame
        DataFrame with added columns: log_concentration, detected_flag
    """
    if df.empty or "concentration_raw" not in df.columns:
        return df

    # Log transform (only positive values)
    df["log_concentration"] = df["concentration_raw"].apply(lambda x: np.log(x) if pd.notna(x) and x > 0 else np.nan)

    # Detection flag (simple: any positive value considered detected)
    df["detected_flag"] = df["concentration_raw"] > 0

    return df


def get_pesticide_metabolites(cycle: str, ref_path: Path | None = None, timeout: int = 30) -> pd.DataFrame:
    """Load and harmonize pesticide laboratory analytes for a given NHANES cycle.

    This function:
    1. Attempts to download pesticide component files (OPD, UPHOPM, PP series)
    2. Normalizes column names
    3. Extracts analyte concentration columns
    4. Maps to reference metadata (analyte name, parent pesticide, class)
    5. Derives log concentration and detection flags
    6. Returns structured DataFrame per schema (docs/pesticide_biomonitoring_plan.md § 6)

    Parameters
    ----------
    cycle : str
        NHANES cycle (e.g., '2017-2018')
    ref_path : Path | None
        Optional path to pesticide_reference.csv
    timeout : int
        Download timeout in seconds

    Returns
    -------
    pd.DataFrame
        Harmonized pesticide analyte data with schema:
        - participant_id: int
        - cycle: str
        - analyte_name: str
        - parent_pesticide: str
        - metabolite_class: str
        - matrix: str
        - concentration_raw: float
        - unit: str
        - log_concentration: float
        - detected_flag: bool
        - source_file: str

        Returns empty DataFrame if cycle has no pesticide data or download fails.

    Raises
    ------
    ValueError
        If cycle format invalid or not in known mapping

    Examples
    --------
    >>> explorer = NHANESExplorer()
    >>> pest_df = get_pesticide_metabolites('2017-2018')
    >>> print(pest_df[['participant_id', 'analyte_name', 'concentration_raw']].head())
    """
    # Validate cycle format
    _parse_cycle_years(cycle)

    # Load reference metadata
    ref_df = load_pesticide_reference(ref_path)

    if ref_df.empty:
        print("Warning: pesticide_reference.csv not found or empty. Proceeding without metadata.")

    # Load analyte code mapping for URX*/LBX* → canonical name translation
    code_map = load_analyte_code_map()

    # Try each candidate file pattern
    candidates = _build_pesticide_file_candidates(cycle)

    all_dfs = []

    for component, _description in candidates:  # description unused (ruff B007)
        df_raw = _download_xpt_flexible(cycle, component, timeout=timeout)

        if df_raw.empty:
            continue

        # Normalize and extract
        df_norm = _normalize_column_names(df_raw)
        df_long = _extract_analyte_columns(df_norm, ref_df)

        if df_long.empty:
            continue

        # Add cycle and source metadata
        df_long["cycle"] = cycle
        df_long["source_file"] = f"{component}_{_get_cycle_letter_suffix(cycle)}"

        # Map to reference (apply code→name translation)
        df_mapped = _map_to_reference(df_long, ref_df, code_map)

        # Derive metrics
        df_final = _derive_metrics(df_mapped)

        all_dfs.append(df_final)

    if not all_dfs:
        # No pesticide data found for this cycle
        return pd.DataFrame()

    # Concatenate all sources
    result = pd.concat(all_dfs, ignore_index=True)

    # Add placeholder fields for full schema compliance (to be populated in Phase 2)
    if "analyte_name" not in result.columns:
        result["analyte_name"] = result["analyte_code"]  # Fallback
    if "parent_pesticide" not in result.columns:
        result["parent_pesticide"] = "Unknown"
    if "metabolite_class" not in result.columns:
        result["metabolite_class"] = "Unknown"
    if "matrix" not in result.columns:
        result["matrix"] = "urine"  # Default assumption (most pesticide metabolites)
    if "unit" not in result.columns:
        result["unit"] = "ug/L"  # Common urinary unit

    # Reorder columns per schema
    schema_cols = [
        "participant_id",
        "cycle",
        "analyte_name",
        "parent_pesticide",
        "metabolite_class",
        "matrix",
        "concentration_raw",
        "unit",
        "log_concentration",
        "detected_flag",
        "source_file",
    ]

    # Include only columns that exist
    final_cols = [c for c in schema_cols if c in result.columns]

    return result[final_cols]


def get_pesticide_panel(cycles: list[str], ref_path: Path | None = None, timeout: int = 30) -> pd.DataFrame:
    """Load and stack pesticide laboratory analytes for multiple NHANES cycles.

    Convenience wrapper around `get_pesticide_metabolites` for multi-cycle longitudinal analysis.
    Automatically skips missing cycles (returns empty for that cycle) and concatenates results.

    Parameters
    ----------
    cycles : list[str]
        List of NHANES cycles (e.g., ['2015-2016', '2017-2018'])
    ref_path : Path | None
        Optional path to pesticide_reference.csv
    timeout : int
        Download timeout in seconds

    Returns
    -------
    pd.DataFrame
        Stacked DataFrame with all available analytes across specified cycles.
        Returns empty DataFrame if no cycles yield data.

    Raises
    ------
    ValueError
        If any cycle format is invalid (even if data unavailable, format must be valid)

    Examples
    --------
    >>> panel = get_pesticide_panel(['2015-2016', '2017-2018'])
    >>> panel.groupby('cycle')['participant_id'].nunique()
    cycle
    2015-2016    8000
    2017-2018    7500
    Name: participant_id, dtype: int64

    Notes
    -----
    - Missing cycle files do NOT raise exceptions; empty frames are skipped.
    - Cycles with partial data (some components missing) are included if at least one component succeeds.
    - Use for temporal trend analysis, demographic comparisons, or correlation studies.
    """
    frames = []

    for cycle in cycles:
        df = get_pesticide_metabolites(cycle, ref_path=ref_path, timeout=timeout)
        if not df.empty:
            frames.append(df)
        # Silently skip empty cycles (already logged by get_pesticide_metabolites)

    if not frames:
        print(f"⚠ No valid data retrieved for any of the {len(cycles)} requested cycles.")
        return pd.DataFrame()

    # Concatenate all cycles
    stacked = pd.concat(frames, ignore_index=True)
    return stacked
