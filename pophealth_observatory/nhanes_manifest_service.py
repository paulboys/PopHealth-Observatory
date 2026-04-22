"""NHANES manifest parsing and assembly services."""

from __future__ import annotations

import logging
import os
import re
import time
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urljoin

import pandas as pd
import requests

from .logging_config import log_with_fallback

logger = logging.getLogger(__name__)

YEAR_RANGE_REGEX = re.compile(r"(20\d{2})\s*[-–]\s*(20\d{2})")
SIZE_TOKEN_REGEX = re.compile(r"(\d+(?:\.\d+)?)\s*(KB|MB|GB|TB)", re.I)


def normalize_year_span(year_text: str | None) -> str:
    """Normalize raw year text into canonical YYYY_YYYY form."""
    if not year_text:
        return ""
    yt = year_text.strip().replace("\u2013", "-").replace("\u2014", "-")
    match = YEAR_RANGE_REGEX.search(yt)
    if match:
        return f"{match.group(1)}_{match.group(2)}"
    nums = re.findall(r"20\d{2}", yt)
    if len(nums) >= 2:
        return f"{nums[0]}_{nums[1]}"
    return yt.replace("-", "_").replace(" ", "_")


def derive_local_filename(remote_url: str, year_norm: str) -> str | None:
    """Derive canonical local XPT filename with year span suffix."""
    if not remote_url:
        return None
    base = os.path.basename(remote_url)
    if not base.lower().endswith(".xpt"):
        return None
    stem = base[:-4]
    match = re.match(r"^([A-Za-z0-9]+?)(?:_[A-Z])$", stem)
    core = match.group(1) if match else stem
    if year_norm:
        return f"{core}_{year_norm}.xpt"
    return f"{core}.xpt"


def classify_data_file(href: str, label: str) -> str:
    """Classify coarse data file type from URL/label heuristics."""
    href_lower = (href or "").lower()
    label_lower = (label or "").lower()
    if href_lower.endswith(".xpt") or "[xpt" in label_lower:
        return "XPT"
    if href_lower.endswith(".zip") or "[zip" in label_lower:
        return "ZIP"
    if (
        href_lower.startswith("ftp://")
        or href_lower.startswith("ftps://")
        or "ftp" in href_lower
        or "[ftp" in label_lower
    ):
        return "FTP"
    return "OTHER"


def extract_size(label: str) -> str | None:
    """Extract a human-readable size token from link text."""
    if not label:
        return None
    match = SIZE_TOKEN_REGEX.search(label)
    if match:
        value, unit = match.groups()
        return f"{value} {unit.upper()}"
    return None


def parse_component_table(html: str, page_url: str) -> list[dict[str, Any]]:
    """Parse NHANES component table into normalized row records."""
    try:
        from bs4 import BeautifulSoup  # type: ignore
    except ImportError:
        log_with_fallback(
            logger,
            logging.WARNING,
            "BeautifulSoup (bs4) not installed; metadata table parsing unavailable.",
        )
        return []

    soup = BeautifulSoup(html, "html.parser")
    tables = soup.find_all("table")
    target_table = None
    for table in tables:
        header_texts = [th.get_text(strip=True) for th in table.find_all("th")]
        lower_join = " ".join(h.lower() for h in header_texts)
        if ("year" in lower_join or "years" in lower_join) and "data file" in lower_join and "doc" in lower_join:
            target_table = table
            break

    if not target_table:
        return []

    headers = [th.get_text(strip=True) for th in target_table.find_all("th")]
    header_index_map = {idx: header for idx, header in enumerate(headers)}
    records: list[dict[str, Any]] = []

    for tr in target_table.find_all("tr"):
        tds = tr.find_all("td")
        if not tds:
            continue
        col_map: dict[str, Any] = {}
        for idx, td in enumerate(tds):
            key = header_index_map.get(idx, f"col{idx}")
            col_map[key] = td

        year_cell = col_map.get("Years") or col_map.get("Year")
        data_name_cell = col_map.get("Data File Name")
        doc_cell = col_map.get("Doc File")
        data_cell = col_map.get("Data File")
        date_pub_cell = col_map.get("Date Published")
        if not (year_cell and data_cell):
            continue

        year_raw = year_cell.get_text(" ", strip=True)
        year_norm = normalize_year_span(year_raw)
        data_file_name = data_name_cell.get_text(" ", strip=True) if data_name_cell else ""
        doc_anchor = doc_cell.find("a", href=True) if doc_cell else None
        data_anchor = data_cell.find("a", href=True)
        if not data_anchor:
            continue

        doc_href = urljoin(page_url, doc_anchor["href"]) if doc_anchor else None
        doc_label = doc_anchor.get_text(" ", strip=True) if doc_anchor else None
        data_href = urljoin(page_url, data_anchor["href"])
        data_label = data_anchor.get_text(" ", strip=True)
        file_type = classify_data_file(data_href, data_label)
        size_token = extract_size(data_label)
        original_filename = os.path.basename(data_href) if file_type in ("XPT", "ZIP") else None
        derived_local = derive_local_filename(data_href, year_norm) if file_type == "XPT" else original_filename
        date_published = date_pub_cell.get_text(" ", strip=True) if date_pub_cell else ""

        records.append(
            {
                "year_raw": year_raw,
                "year_normalized": year_norm,
                "data_file_name": data_file_name,
                "doc_file_url": doc_href,
                "doc_file_label": doc_label,
                "data_file_url": data_href,
                "data_file_label": data_label,
                "data_file_type": file_type,
                "data_file_size": size_token,
                "date_published": date_published,
                "original_filename": original_filename,
                "derived_local_filename": derived_local,
            }
        )
    return records


def fetch_component_page(component_name: str, cache: dict[str, str]) -> str | None:
    """Fetch component listing page with retries and cache."""
    if component_name in cache:
        return cache[component_name]

    base_listing = "https://wwwn.cdc.gov/nchs/nhanes/Default.aspx"
    trial_urls = [
        f"https://wwwn.cdc.gov/nchs/nhanes/search/datapage.aspx?Component={component_name}",
        base_listing,
    ]
    for url in trial_urls:
        for attempt in range(3):
            try:
                response = requests.get(url, timeout=25)
                if response.status_code == 200 and "nhanes" in response.text.lower():
                    if url == base_listing and component_name.lower() not in response.text.lower():
                        break
                    cache[component_name] = response.text
                    return response.text
            except Exception:
                pass
            time.sleep(0.5 * (2**attempt))
    return None


def build_detailed_component_manifest(
    components: list[str] | None,
    as_dataframe: bool,
    year_range: tuple[str, str] | None,
    file_types: list[str] | None,
    force_refresh: bool,
    schema_version: str,
    cache: dict[str, str],
    fetch_page: Callable[[str], str | None],
    parse_table: Callable[[str, str], list[dict[str, Any]]],
) -> dict[str, Any]:
    """Build enriched component manifest from fetch/parse callbacks."""
    target_components = components or ["Demographics", "Examination", "Laboratory", "Dietary", "Questionnaire"]
    detailed: dict[str, list[dict[str, Any]]] = {}

    for comp in target_components:
        if force_refresh and comp in cache:
            cache.pop(comp, None)
        html = fetch_page(comp)
        if not html:
            detailed[comp] = []
            continue
        try:
            records = parse_table(html, f"https://wwwn.cdc.gov/nchs/nhanes/search/datapage.aspx?Component={comp}")
        except Exception:
            records = []
        detailed[comp] = records

    flat_rows = [dict(component=comp, **record) for comp, rows in detailed.items() for record in rows]

    if year_range:
        year_start, year_end = year_range

        def overlaps(row: dict[str, Any]) -> bool:
            span = row.get("year_normalized", "")
            if "_" in span:
                try:
                    start_year, end_year = span.split("_", 1)
                    return (start_year <= year_end) and (end_year >= year_start)
                except Exception:
                    return False
            return False

        flat_rows = [row for row in flat_rows if overlaps(row)]

    if file_types:
        allowed = {file_type.upper() for file_type in file_types}
        flat_rows = [row for row in flat_rows if row.get("data_file_type") in allowed]

    summary: dict[str, dict[str, int]] = {}
    for row in flat_rows:
        summary.setdefault(row["component"], {}).setdefault(row["data_file_type"], 0)
        summary[row["component"]][row["data_file_type"]] += 1

    manifest: dict[str, Any] = {
        "schema_version": schema_version,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "detailed_year_records": detailed,
        "summary_counts": summary,
        "component_count": len(detailed),
        "total_file_rows": len(flat_rows),
    }
    if as_dataframe:
        try:
            manifest["dataframe"] = pd.DataFrame(flat_rows)
        except Exception:
            pass
    return manifest
