"""PopHealth Observatory core and NHANESExplorer implementation.

SPDX-License-Identifier: MIT
Copyright (c) 2025 Paul Boys and PopHealth Observatory contributors
"""

import pandas as pd
import numpy as np
import requests
import io
import warnings
from typing import Optional, Dict, List

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
    """Backward compatible class name; extends PopHealthObservatory."""
    # Methods identical to earlier implementation for now
    def get_demographics_data(self, cycle: str = '2017-2018') -> pd.DataFrame:
        """Get demographics data for a specific cycle with proper URL handling.
        
        NHANES changed URL patterns over time, so we try multiple patterns in sequence.
        """
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
        if metric not in df.columns or demographic not in df.columns:
            return pd.DataFrame()
        sub = df[[demographic, metric]].dropna()
        stats = sub.groupby(demographic)[metric].agg(['count','mean','median','std','min','max']).round(2)
        stats.columns = ['Count','Mean','Median','Std Dev','Min','Max']
        return stats

    def create_demographic_visualization(self, df: pd.DataFrame, metric: str, demographic: str):
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
