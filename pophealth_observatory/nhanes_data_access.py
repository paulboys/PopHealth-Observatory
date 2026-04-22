"""NHANES data access helpers.

Centralizes URL pattern generation and resilient XPT download behavior used by
multiple observatory entry points.
"""

from __future__ import annotations

import io

import pandas as pd
import requests


def build_nhanes_xpt_url_patterns(
    cycle: str,
    component: str,
    letter: str,
    base_url: str,
    alt_base_url: str,
) -> list[str]:
    """Build candidate NHANES XPT URLs for a component/cycle pair.

    Parameters
    ----------
    cycle : str
        NHANES cycle (for example ``"2017-2018"``).
    component : str
        Component code (for example ``"DEMO"``).
    letter : str
        NHANES cycle suffix letter (for example ``"J"``).
    base_url : str
        Standard NHANES base URL.
    alt_base_url : str
        Alternate NHANES public data base URL.

    Returns
    -------
    list[str]
        Ordered URL candidates to attempt in sequence.
    """
    cycle_year = cycle.split("-")[0] if "-" in cycle else cycle
    return [
        f"{alt_base_url}/{cycle_year}/DataFiles/{component}_{letter}.xpt",
        f"{base_url}/{cycle}/{component}_{letter}.XPT",
        f"{base_url}/{cycle}/{component}_{letter}.xpt",
        f"{base_url}/{cycle}/{component.lower()}_{letter}.XPT",
        f"{base_url}/{cycle}/{component.lower()}_{letter}.xpt",
        f"https://wwwn.cdc.gov/Nchs/Data/Nhanes/{cycle}/{component}_{letter}.XPT",
        f"{base_url}/{cycle.replace('-', '')}/{component}_{cycle[-2:]}.XPT",
        f"{base_url}/{cycle}/{component}_{cycle[-2:]}.XPT",
    ]


def try_download_xpt(
    url_patterns: list[str],
    timeout_seconds: int = 30,
) -> tuple[pd.DataFrame | None, str | None, list[str]]:
    """Try downloading and parsing the first valid XPT among URL candidates.

    Parameters
    ----------
    url_patterns : list[str]
        Ordered candidate URLs.
    timeout_seconds : int, default=30
        Request timeout in seconds.

    Returns
    -------
    tuple[pd.DataFrame | None, str | None, list[str]]
        Parsed DataFrame (or None), successful URL (or None), and collected
        error summaries for failed attempts.
    """
    errors: list[str] = []
    for url in url_patterns:
        try:
            response = requests.get(url, timeout=timeout_seconds)
            if response.status_code != 200:
                errors.append(f"Status {response.status_code} from {url}")
                continue

            df = pd.read_sas(io.BytesIO(response.content), format="xport")
            if df.empty:
                errors.append(f"Empty DataFrame from {url}")
                continue

            return df, url, errors
        except Exception as exc:  # noqa: BLE001
            errors.append(f"Error with {url}: {str(exc)}")

    return None, None, errors
