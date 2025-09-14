"""PopHealth Observatory core and NHANESExplorer implementation.

SPDX-License-Identifier: MIT
Copyright (c) 2025 Paul Boys and PopHealth Observatory contributors
"""

import pandas as pd
import numpy as np
import requests
import io
import warnings
import re
import os
from datetime import datetime, timezone
from dataclasses import dataclass
from urllib.parse import urljoin
from typing import Optional, Dict, List, Any

warnings.filterwarnings('ignore')

class PopHealthObservatory:
    """Core observatory class for population health survey data (initial focus: NHANES)."""
    def __init__(self):
        # Primary cycle base for direct cycle folder structure (older & standard pattern)
        self.base_url = "https://wwwn.cdc.gov/Nchs/Nhanes"
        # Alternate base (newer public data file listing structure observed for recent cycles)
        self.alt_base_url = "https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public"
        self.data_cache: Dict[str, pd.DataFrame] = {}
        self.available_cycles = [
            '2021-2022',  # recent combined cycle (post-pandemic)
            '2019-2020',
            '2017-2018',
            '2015-2016',
            '2013-2014',
            '2011-2012',
            '2009-2010'
        ]
        # Map survey cycle to NHANES file letter suffix (partial set; extend as needed)
        self.cycle_suffix_map = {
            '2021-2022': 'L',
            '2019-2020': 'K',  # partial / limited release
            '2017-2018': 'J',
            '2015-2016': 'I',
            '2013-2014': 'H',
            '2011-2012': 'G',
            '2009-2010': 'F',
            # Earlier examples (not currently in available_cycles):
            '2007-2008': 'E',
            '2005-2006': 'D',
            '2003-2004': 'C',
            '2001-2002': 'B',
            '1999-2000': 'A'
        }
        self.components = {
            'demographics': 'DEMO',
            'body_measures': 'BMX',
            'blood_pressure': 'BPX',
            'cholesterol': 'TCHOL',
            'diabetes': 'GLU',
            'dietary': 'DR1TOT',
            'physical_activity': 'PAQ',
            'smoking': 'SMQ',
            'alcohol': 'ALQ'
        }

    def get_data_url(self, cycle: str, component: str) -> str:
        """Return the best-guess URL for a given cycle/component.

        NHANES file naming convention pairs a survey cycle with a letter code (e.g., 2017-2018 -> J)
        Files then follow pattern: <COMPONENT>_<LETTER>.XPT inside a folder named by full cycle
        (older pattern) or under the newer public data path.
        """
        letter = self.cycle_suffix_map.get(cycle)
        if not letter:
            raise ValueError(f"No letter suffix mapping for cycle '{cycle}'. Update cycle_suffix_map.")
        # Candidate URL patterns (order matters). We'll try each until one works in download.
        candidates = [
            f"{self.base_url}/{cycle}/{component}_{letter}.XPT",  # standard
            # Some recent hosting patterns use year start folder and DataFiles subfolder
            f"{self.alt_base_url}/{cycle.split('-')[0]}/DataFiles/{component}_{letter}.xpt",  # alt lower-case ext
            f"{self.alt_base_url}/{cycle.split('-')[0]}/DataFiles/{component}_{letter}.XPT",  # alt upper-case ext
        ]
        # Return first candidate; download will iterate if needed (implemented there)
        return candidates[0]

    def download_data(self, cycle: str, component: str) -> pd.DataFrame:
        """Download data for a specific component and cycle with flexible URL handling.
        
        This method tries multiple URL patterns to handle the different formats used across NHANES cycles.
        """
        key = f"{cycle}_{component}"
        if key in self.data_cache:
            return self.data_cache[key]
            
        letter = self.cycle_suffix_map.get(cycle, '')
        cycle_year = cycle.split('-')[0] if '-' in cycle else cycle
        
        # Define URL patterns to try (in order of preference)
        url_patterns = [
            # 2021+ pattern with Public subdirectory
            f"{self.alt_base_url}/{cycle_year}/DataFiles/{component}_{letter}.xpt",
            # Standard pattern (2007-2018)
            f"{self.base_url}/{cycle}/{component}_{letter}.XPT",
            # Lowercase variant
            f"{self.base_url}/{cycle}/{component}_{letter}.xpt",
            # Pre-2007 pattern (lowercase component)
            f"{self.base_url}/{cycle}/{component.lower()}_{letter}.XPT",
            # Pre-2007 pattern (lowercase component and extension)
            f"{self.base_url}/{cycle}/{component.lower()}_{letter}.xpt",
            # Alternative Data/Nhanes path
            f"https://wwwn.cdc.gov/Nchs/Data/Nhanes/{cycle}/{component}_{letter}.XPT",
            # Variant with cycle year suffix
            f"{self.base_url}/{cycle}/{component}_{cycle[-2:]}.XPT",
        ]
        
        # Try each URL pattern
        errors = []
        
        for url in url_patterns:
            try:
                print(f"Trying {component} URL: {url}")
                response = requests.get(url, timeout=30)
                
                if response.status_code == 200:
                    print(f"✓ Success loading {component} from: {url}")
                    df = pd.read_sas(io.BytesIO(response.content), format='xport')
                    self.data_cache[key] = df
                    return df
                else:
                    errors.append(f"Status {response.status_code} from {url}")
            except Exception as e:
                errors.append(f"Error with {url}: {str(e)}")
        
        print(f"Failed to download {component} for {cycle}. Errors: {errors}")
        return pd.DataFrame()

    # Reuse logic from legacy NHANESExplorer below for compatibility

class NHANESExplorer(PopHealthObservatory):
    """NHANES-focused explorer extending :class:`PopHealthObservatory`.

    Provides:
    - Robust cycle/component XPT downloads (inherited)
    - Metadata table parsing producing rich manifest entries
    - Convenience analytic helpers (merging, summaries, visuals)
    - Manifest persistence with schema versioning & filtering
    """
    # Methods identical to earlier implementation for now
    # --- Enhanced metadata parsing helpers (integrated from notebook Section 14a) ---
    _YEAR_RANGE_REGEX = re.compile(r"(20\d{2})\s*[-–]\s*(20\d{2})")
    _SIZE_TOKEN_REGEX = re.compile(r"(\d+(?:\.\d+)?)\s*(KB|MB|GB|TB)", re.I)
    _MANIFEST_SCHEMA_VERSION = "1.0.0"

    def _normalize_year_span(self, year_text: str) -> str:
        """Normalize raw year span text into canonical ``YYYY_YYYY`` form.

        Handles en-dash variations and falls back to safe underscore replacement
        if two four-digit years are not clearly extracted.
        """
        if not year_text:
            return ""
        yt = year_text.strip().replace('\u2013', '-').replace('\u2014', '-')
        m = self._YEAR_RANGE_REGEX.search(yt)
        if m:
            return f"{m.group(1)}_{m.group(2)}"
        nums = re.findall(r"20\d{2}", yt)
        if len(nums) >= 2:
            return f"{nums[0]}_{nums[1]}"
        return yt.replace('-', '_').replace(' ', '_')

    def _derive_local_filename(self, remote_url: str, year_norm: str) -> Optional[str]:
        """Derive a canonical local filename for an XPT file with year span.

        Returns None for non-XPT resources (ZIP / FTP / OTHER). Strips trailing
        single-letter suffix (e.g., ``DEMO_H`` -> ``DEMO``) before appending years.
        """
        if not remote_url:
            return None
        base = os.path.basename(remote_url)
        if not base.lower().endswith('.xpt'):
            return None
        stem = base[:-4]
        m = re.match(r"^([A-Za-z0-9]+?)(?:_[A-Z])$", stem)
        core = m.group(1) if m else stem
        if year_norm:
            return f"{core}_{year_norm}.xpt"
        return f"{core}.xpt"

    def _classify_data_file(self, href: str, label: str) -> str:
        """Classify file anchor into a coarse type.

        Priority order: XPT > ZIP > FTP > OTHER based on URL/label heuristics.
        """
        h = (href or '').lower()
        l = (label or '').lower()
        if h.endswith('.xpt') or '[xpt' in l:
            return 'XPT'
        if h.endswith('.zip') or '[zip' in l:
            return 'ZIP'
        if h.startswith('ftp://') or h.startswith('ftps://') or 'ftp' in h or '[ftp' in l:
            return 'FTP'
        return 'OTHER'

    def _extract_size(self, label: str) -> Optional[str]:
        """Extract human-readable size token (e.g. ``"3.4 MB"``) from link label.

        Returns None if no recognizable size pattern present.
        """
        if not label:
            return None
        m = self._SIZE_TOKEN_REGEX.search(label)
        if m:
            val, unit = m.groups()
            return f"{val} {unit.upper()}"
        return None

    def _parse_component_table(self, html: str, page_url: str) -> List[Dict[str, Any]]:
        """Parse a component listing table into structured dictionaries.

        Returns a list of row dicts with normalized year span, links, file
        classification, size token, original & derived filenames.
        Silently returns empty list if table structure not found or bs4 missing.
        """
        try:
            from bs4 import BeautifulSoup  # type: ignore
        except ImportError:
            print("BeautifulSoup (bs4) not installed; metadata table parsing unavailable.")
            return []
        soup = BeautifulSoup(html, 'html.parser')
        tables = soup.find_all('table')
        target_table = None
        for tbl in tables:
            header_texts = [th.get_text(strip=True) for th in tbl.find_all('th')]
            lower_join = ' '.join(h.lower() for h in header_texts)
            if ('year' in lower_join or 'years' in lower_join) and 'data file' in lower_join and 'doc' in lower_join:
                target_table = tbl
                break
        if not target_table:
            return []
        headers = [th.get_text(strip=True) for th in target_table.find_all('th')]
        header_index_map = {i: h for i, h in enumerate(headers)}
        records: List[Dict[str, Any]] = []
        for tr in target_table.find_all('tr'):
            tds = tr.find_all('td')
            if not tds:
                continue
            col_map: Dict[str, Any] = {}
            for idx, td in enumerate(tds):
                key = header_index_map.get(idx, f"col{idx}")
                col_map[key] = td
            year_cell = col_map.get('Years') or col_map.get('Year')
            data_name_cell = col_map.get('Data File Name')
            doc_cell = col_map.get('Doc File')
            data_cell = col_map.get('Data File')
            date_pub_cell = col_map.get('Date Published')
            if not (year_cell and data_cell):
                continue
            year_raw = year_cell.get_text(' ', strip=True)
            year_norm = self._normalize_year_span(year_raw)
            data_file_name = data_name_cell.get_text(' ', strip=True) if data_name_cell else ''
            doc_a = doc_cell.find('a', href=True) if doc_cell else None
            data_a = data_cell.find('a', href=True)
            if not data_a:
                continue
            doc_href = urljoin(page_url, doc_a['href']) if doc_a else None
            doc_label = doc_a.get_text(' ', strip=True) if doc_a else None
            data_href = urljoin(page_url, data_a['href'])
            data_label = data_a.get_text(' ', strip=True)
            file_type = self._classify_data_file(data_href, data_label)
            size_token = self._extract_size(data_label)
            original_filename = os.path.basename(data_href) if file_type in ('XPT','ZIP') else None
            derived_local_filename = self._derive_local_filename(data_href, year_norm) if file_type == 'XPT' else original_filename
            date_published = date_pub_cell.get_text(' ', strip=True) if date_pub_cell else ''
            records.append({
                'year_raw': year_raw,
                'year_normalized': year_norm,
                'data_file_name': data_file_name,
                'doc_file_url': doc_href,
                'doc_file_label': doc_label,
                'data_file_url': data_href,
                'data_file_label': data_label,
                'data_file_type': file_type,
                'data_file_size': size_token,
                'date_published': date_published,
                'original_filename': original_filename,
                'derived_local_filename': derived_local_filename,
            })
        return records

    def _fetch_component_page(self, component_name: str) -> Optional[str]:
        """Fetch component page HTML with simple multi-URL retry & cache."""
        # Simple in-memory cache
        if not hasattr(self, '_component_page_cache'):
            self._component_page_cache: Dict[str, str] = {}
        if component_name in self._component_page_cache:
            return self._component_page_cache[component_name]
        # Basic mapping; can be extended or discovered dynamically.
        keyword_map = {
            'Demographics': 'Demographics',
            'Examination': 'Examination',
            'Laboratory': 'Laboratory',
            'Dietary': 'Dietary',
            'Questionnaire': 'Questionnaire'
        }
        base_listing = "https://wwwn.cdc.gov/nchs/nhanes/Default.aspx"
        # Direct deep-link patterns observed (these may evolve):
        # We'll try a small set of known anchor patterns first.
        trial_urls = [
            f"https://wwwn.cdc.gov/nchs/nhanes/search/datapage.aspx?Component={component_name}",
            base_listing,
        ]
        for u in trial_urls:
            for attempt in range(3):  # retry with backoff
                try:
                    resp = requests.get(u, timeout=25)
                    if resp.status_code == 200 and 'nhanes' in resp.text.lower():
                        if u == base_listing and component_name.lower() not in resp.text.lower():
                            break  # try next URL
                        self._component_page_cache[component_name] = resp.text
                        return resp.text
                except Exception:
                    pass
                # simple exponential backoff
                import time as _t
                _t.sleep(0.5 * (2 ** attempt))
        return None

    def get_detailed_component_manifest(self,
                                        components: Optional[List[str]] = None,
                                        as_dataframe: bool = False,
                                        year_range: Optional[tuple[str,str]] = None,
                                        file_types: Optional[List[str]] = None,
                                        force_refresh: bool = False,
                                        schema_version: Optional[str] = None) -> Dict[str, Any]:
        """Build enriched metadata manifest for selected component pages.

        Parameters
        ----------
        components : list[str] | None
            Subset of component pages among: Demographics, Examination, Laboratory, Dietary, Questionnaire.
            If None, all are attempted.
        as_dataframe : bool
            If True, attaches flattened DataFrame under key 'dataframe'.
        year_range : tuple[str,str] | None
            Inclusive start/end years; rows overlapping this span retained.
        file_types : list[str] | None
            Filter to only these data_file_type values (e.g. ['XPT','ZIP']).
        force_refresh : bool
            If True, bypass cached component page HTML.
        schema_version : str | None
            Override emitted schema version tag (advanced / experimental).

        Returns
        -------
        dict
            Manifest containing per-component records and summary counts.
            Top-level keys:
              - schema_version
              - generated_at (UTC ISO8601)
              - detailed_year_records (raw grouped rows)
              - summary_counts (nested counts by component and file type)
              - component_count
              - total_file_rows (post-filter)
        """
        target_components = components or ['Demographics','Examination','Laboratory','Dietary','Questionnaire']
        detailed: Dict[str, List[Dict[str, Any]]] = {}
        for comp in target_components:
            if force_refresh and hasattr(self, '_component_page_cache') and comp in self._component_page_cache:
                self._component_page_cache.pop(comp, None)
            html = self._fetch_component_page(comp)
            if not html:
                detailed[comp] = []
                continue
            try:
                records = self._parse_component_table(html, f"https://wwwn.cdc.gov/nchs/nhanes/search/datapage.aspx?Component={comp}")
            except Exception:
                records = []
            detailed[comp] = records
        # Flatten & summarize
        flat_rows = [dict(component=k, **rec) for k, rows in detailed.items() for rec in rows]
        # Filtering
        if year_range:
            ys, ye = year_range
            def overlaps(r):
                span = r.get('year_normalized','')
                if '_' in span:
                    try:
                        a,b = span.split('_',1)
                        # Keep row if interval [a,b] intersects [ys,ye]
                        return (a <= ye) and (b >= ys)
                    except Exception:
                        return False
                return False
            flat_rows = [r for r in flat_rows if overlaps(r)]
        if file_types:
            ftset = {f.upper() for f in file_types}
            # Restrict to desired file types (e.g., only XPT rows)
            flat_rows = [r for r in flat_rows if r.get('data_file_type') in ftset]
        summary = {}
        for row in flat_rows:
            summary.setdefault(row['component'], {}).setdefault(row['data_file_type'], 0)
            summary[row['component']][row['data_file_type']] += 1
        manifest = {
            'schema_version': schema_version or self._MANIFEST_SCHEMA_VERSION,
            'generated_at': datetime.now(timezone.utc).isoformat(),
            'detailed_year_records': detailed,
            'summary_counts': summary,
            'component_count': len(detailed),
            'total_file_rows': len(flat_rows)
        }
        if as_dataframe:
            try:
                manifest['dataframe'] = pd.DataFrame(flat_rows)
            except Exception:
                pass
        return manifest

    def save_detailed_component_manifest(self, path: str, **manifest_kwargs) -> str:
        """Generate and persist a detailed component manifest to JSON.

        Parameters
        ----------
        path : str
            Output JSON file path.
        **manifest_kwargs : Any
            Forwarded to ``get_detailed_component_manifest``.
        """
        manifest = self.get_detailed_component_manifest(**manifest_kwargs)
        try:
            import json
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(manifest, f, indent=2)
        except Exception as e:
            raise RuntimeError(f"Failed writing manifest to {path}: {e}")
        return path

    def get_demographics_data(self, cycle: str = '2017-2018') -> pd.DataFrame:
        """Download and harmonize demographics (DEMO) data for a cycle."""
        component = self.components['demographics']
        letter = self.cycle_suffix_map.get(cycle, '')
        
        # List of URL patterns to try (in order of preference)
        url_patterns = [
            # Newest pattern (2021+) - confirmed working
            f"https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/{cycle.split('-')[0]}/DataFiles/{component}_{letter}.xpt",
            # Older cycles (pre-2021) - standard pattern
            f"https://wwwn.cdc.gov/Nchs/Nhanes/{cycle}/{component}_{letter}.XPT",
            # Other variations
            f"https://wwwn.cdc.gov/Nchs/Nhanes/{cycle.replace('-', '')}/{component}_{cycle[-2:]}.XPT",
            f"https://wwwn.cdc.gov/Nchs/Data/Nhanes/{cycle}/{component}_{letter}.XPT",
            f"https://wwwn.cdc.gov/Nchs/Data/Nhanes/{cycle}/{component}_{letter}.xpt",
        ]
        
        # Try each URL pattern
        demo_df = pd.DataFrame()
        errors = []
        
        for url in url_patterns:
            try:
                print(f"Trying demographics URL: {url}")
                response = requests.get(url, timeout=30)
                if response.status_code == 200:
                    print(f"✓ Success loading demographics from: {url}")
                    demo_df = pd.read_sas(io.BytesIO(response.content), format='xport')
                    break
                else:
                    errors.append(f"Status {response.status_code} from {url}")
            except Exception as e:
                errors.append(f"Error with {url}: {str(e)}")
        
        if demo_df.empty:
            print(f"Failed to download demographics for {cycle}. Errors: {errors}")
            return demo_df
        demo_vars = {
            'SEQN': 'participant_id',
            'RIAGENDR': 'gender',
            'RIDAGEYR': 'age_years',
            'RIDRETH3': 'race_ethnicity',
            'DMDEDUC2': 'education',
            'INDFMPIR': 'poverty_ratio',
            'WTMEC2YR': 'exam_weight',
        }
        available = [c for c in demo_vars if c in demo_df.columns]
        demo_clean = demo_df[available].copy().rename(columns={k: v for k, v in demo_vars.items() if k in available})
        if 'gender' in demo_clean.columns:
            demo_clean['gender_label'] = demo_clean['gender'].map({1: 'Male', 2: 'Female'})
        if 'race_ethnicity' in demo_clean.columns:
            race_labels = {1: 'Mexican American',2: 'Other Hispanic',3: 'Non-Hispanic White',4: 'Non-Hispanic Black',6: 'Non-Hispanic Asian',7: 'Other/Multi-racial'}
            demo_clean['race_ethnicity_label'] = demo_clean['race_ethnicity'].map(race_labels)
        return demo_clean

    def get_body_measures(self, cycle: str = '2017-2018') -> pd.DataFrame:
        """Return body measures (BMX) with derived BMI categories."""
        bmx_df = self.download_data(cycle, self.components['body_measures'])
        if bmx_df.empty:
            return bmx_df
        body_vars = {'SEQN': 'participant_id','BMXWT': 'weight_kg','BMXHT': 'height_cm','BMXBMI': 'bmi','BMXWAIST': 'waist_cm'}
        available = [c for c in body_vars if c in bmx_df.columns]
        body_clean = bmx_df[available].copy().rename(columns={k: v for k, v in body_vars.items() if k in available})
        if 'bmi' in body_clean.columns:
            body_clean['bmi_category'] = pd.cut(body_clean['bmi'], bins=[0, 18.5, 25, 30, float('inf')], labels=['Underweight','Normal','Overweight','Obese'], right=False)
        return body_clean

    def get_blood_pressure(self, cycle: str = '2017-2018') -> pd.DataFrame:
        """Return BPX readings plus averaged and categorized blood pressure."""
        bp_df = self.download_data(cycle, self.components['blood_pressure'])
        if bp_df.empty:
            return bp_df
        bp_vars = {'SEQN': 'participant_id','BPXSY1': 'systolic_bp_1','BPXDI1': 'diastolic_bp_1','BPXSY2': 'systolic_bp_2','BPXDI2': 'diastolic_bp_2','BPXSY3': 'systolic_bp_3','BPXDI3': 'diastolic_bp_3'}
        available = [c for c in bp_vars if c in bp_df.columns]
        bp_clean = bp_df[available].copy().rename(columns={k: v for k, v in bp_vars.items() if k in available})
        systolic_cols = [c for c in bp_clean.columns if 'systolic' in c]
        diastolic_cols = [c for c in bp_clean.columns if 'diastolic' in c]
        if systolic_cols:
            bp_clean['avg_systolic'] = bp_clean[systolic_cols].mean(axis=1)
        if diastolic_cols:
            bp_clean['avg_diastolic'] = bp_clean[diastolic_cols].mean(axis=1)
        if 'avg_systolic' in bp_clean.columns and 'avg_diastolic' in bp_clean.columns:
            conditions = [
                (bp_clean['avg_systolic'] < 120) & (bp_clean['avg_diastolic'] < 80),
                (bp_clean['avg_systolic'] < 130) & (bp_clean['avg_diastolic'] < 80),
                ((bp_clean['avg_systolic'] >= 130) & (bp_clean['avg_systolic'] < 140)) | ((bp_clean['avg_diastolic'] >= 80) & (bp_clean['avg_diastolic'] < 90)),
                (bp_clean['avg_systolic'] >= 140) | (bp_clean['avg_diastolic'] >= 90)
            ]
            choices = ['Normal','Elevated','Stage 1 Hypertension','Stage 2 Hypertension']
            bp_clean['bp_category'] = np.select(conditions, choices, default='Unknown')
        return bp_clean

    def create_merged_dataset(self, cycle: str = '2017-2018') -> pd.DataFrame:
        """Merge DEMO, BMX, BPX slices on participant_id."""
        print(f"Creating merged dataset for {cycle}...")
        demo_df = self.get_demographics_data(cycle)
        body_df = self.get_body_measures(cycle)
        bp_df = self.get_blood_pressure(cycle)
        merged = demo_df.copy()
        if not body_df.empty:
            merged = merged.merge(body_df, on='participant_id', how='left')
        if not bp_df.empty:
            merged = merged.merge(bp_df, on='participant_id', how='left')
        print(f"Merged dataset created with {len(merged)} participants and {len(merged.columns)} variables")
        return merged

    def analyze_by_demographics(self, df: pd.DataFrame, metric: str, demographic: str) -> pd.DataFrame:
        """Group metric by demographic and compute standard descriptive stats."""
        if metric not in df.columns or demographic not in df.columns:
            return pd.DataFrame()
        sub = df[[demographic, metric]].dropna()
        stats = sub.groupby(demographic)[metric].agg(['count','mean','median','std','min','max']).round(2)
        stats.columns = ['Count','Mean','Median','Std Dev','Min','Max']
        return stats

    def create_demographic_visualization(self, df: pd.DataFrame, metric: str, demographic: str):
        """Boxplot + mean bar chart for metric by demographic (if available)."""
        if metric not in df.columns or demographic not in df.columns:
            return
        try:
            import matplotlib.pyplot as plt  # type: ignore
            import seaborn as sns  # type: ignore
        except Exception as e:
            print(f"Visualization dependencies not available: {e}")
            return
        fig, axes = plt.subplots(1, 2, figsize=(15, 6))
        sub = df[[demographic, metric]].dropna()
        sns.boxplot(data=sub, x=demographic, y=metric, ax=axes[0])
        axes[0].set_title(f'{metric} by {demographic}')
        axes[0].tick_params(axis='x', rotation=45)
        means = sub.groupby(demographic)[metric].mean()
        means.plot(kind='bar', ax=axes[1], color='skyblue')
        axes[1].set_title(f'Mean {metric} by {demographic}')
        axes[1].tick_params(axis='x', rotation=45)
        axes[1].set_ylabel(f'Mean {metric}')
        plt.tight_layout()
        plt.show()

    def generate_summary_report(self, df: pd.DataFrame) -> str:
        """Generate textual summary of demographics & selected health metrics."""
        report = ["PopHealth Observatory Summary Report", "="*40, f"Total Participants: {len(df):,}", f"Total Variables: {len(df.columns)}", ""]
        if 'age_years' in df.columns:
            age_stats = df['age_years'].describe()
            report += ["Age Distribution:", f"  Mean age: {age_stats['mean']:.1f} years", f"  Age range: {age_stats['min']:.0f} - {age_stats['max']:.0f} years", ""]
        if 'gender_label' in df.columns:
            gender_counts = df['gender_label'].value_counts()
            report.append("Gender Distribution:")
            for g,c in gender_counts.items():
                pct = (c/len(df))*100
                report.append(f"  {g}: {c:,} ({pct:.1f}%)")
            report.append("")
        if 'race_ethnicity_label' in df.columns:
            race_counts = df['race_ethnicity_label'].value_counts()
            report.append("Race/Ethnicity Distribution:")
            for r,c in race_counts.items():
                pct = (c/len(df))*100
                report.append(f"  {r}: {c:,} ({pct:.1f}%)")
            report.append("")
        metrics = ['bmi','avg_systolic','avg_diastolic','weight_kg','height_cm']
        avail = [m for m in metrics if m in df.columns]
        if avail:
            report.append("Health Metrics Summary:")
            for m in avail:
                stats = df[m].describe()
                miss = df[m].isna().sum()
                report += [f"  {m}:", f"    Mean: {stats['mean']:.2f}", f"    Range: {stats['min']:.2f} - {stats['max']:.2f}", f"    Missing: {miss:,} ({(miss/len(df))*100:.1f}%)"]
            report.append("")
        return "\n".join(report)
