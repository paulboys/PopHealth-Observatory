import pandas as pd
import numpy as np
import requests
import io
import matplotlib.pyplot as plt
import seaborn as sns
from typing import Dict, List, Optional, Tuple
import warnings
warnings.filterwarnings('ignore')

class NHANESExplorer:
    """
    Main class for exploring NHANES (National Health and Nutrition Examination Survey) data.
    Provides functionality to download, process, and analyze health metrics across demographics.
    """
    
    def __init__(self):
        self.base_url = "https://wwwn.cdc.gov/Nchs/Nhanes"
        self.data_cache = {}
        self.available_cycles = ['2017-2018', '2015-2016', '2013-2014', '2011-2012', '2009-2010']
        
        # Common NHANES data components
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
        """Generate URL for NHANES data component."""
        cycle_code = cycle.replace('-', '')
        return f"{self.base_url}/{cycle_code}/{component}_{cycle_code[2:]}.XPT"
    
    def download_data(self, cycle: str, component: str) -> pd.DataFrame:
        """Download NHANES data component for specified cycle."""
        cache_key = f"{cycle}_{component}"
        
        if cache_key in self.data_cache:
            print(f"Using cached data for {component} {cycle}")
            return self.data_cache[cache_key]
        
        url = self.get_data_url(cycle, component)
        print(f"Downloading {component} data for {cycle}...")
        
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            # Read XPT file using pandas
            df = pd.read_sas(io.BytesIO(response.content), format='xport')
            
            # Cache the data
            self.data_cache[cache_key] = df
            print(f"Successfully downloaded {len(df)} records")
            
            return df
        
        except Exception as e:
            print(f"Error downloading {component} for {cycle}: {str(e)}")
            return pd.DataFrame()
    
    def get_demographics_data(self, cycle: str = '2017-2018') -> pd.DataFrame:
        """Get demographics data with key variables."""
        demo_df = self.download_data(cycle, self.components['demographics'])
        
        if demo_df.empty:
            return demo_df
        
        # Key demographic variables
        demo_vars = {
            'SEQN': 'participant_id',
            'RIAGENDR': 'gender',  # 1=Male, 2=Female
            'RIDAGEYR': 'age_years',
            'RIDRETH3': 'race_ethnicity',  # Race/ethnicity categories
            'DMDEDUC2': 'education',  # Education level
            'INDFMPIR': 'poverty_ratio',  # Poverty income ratio
            'WTMEC2YR': 'exam_weight',  # Examination weight
        }
        
        # Select and rename columns
        available_vars = [col for col in demo_vars.keys() if col in demo_df.columns]
        demo_clean = demo_df[available_vars].copy()
        demo_clean = demo_clean.rename(columns={k: v for k, v in demo_vars.items() if k in available_vars})
        
        # Add demographic labels
        if 'gender' in demo_clean.columns:
            demo_clean['gender_label'] = demo_clean['gender'].map({1: 'Male', 2: 'Female'})
        
        if 'race_ethnicity' in demo_clean.columns:
            race_labels = {
                1: 'Mexican American',
                2: 'Other Hispanic',
                3: 'Non-Hispanic White',
                4: 'Non-Hispanic Black',
                6: 'Non-Hispanic Asian',
                7: 'Other/Multi-racial'
            }
            demo_clean['race_ethnicity_label'] = demo_clean['race_ethnicity'].map(race_labels)
        
        return demo_clean
    
    def get_body_measures(self, cycle: str = '2017-2018') -> pd.DataFrame:
        """Get body measurements data."""
        bmx_df = self.download_data(cycle, self.components['body_measures'])
        
        if bmx_df.empty:
            return bmx_df
        
        body_vars = {
            'SEQN': 'participant_id',
            'BMXWT': 'weight_kg',
            'BMXHT': 'height_cm',
            'BMXBMI': 'bmi',
            'BMXWAIST': 'waist_cm'
        }
        
        available_vars = [col for col in body_vars.keys() if col in bmx_df.columns]
        body_clean = bmx_df[available_vars].copy()
        body_clean = body_clean.rename(columns={k: v for k, v in body_vars.items() if k in available_vars})
        
        # Calculate BMI categories
        if 'bmi' in body_clean.columns:
            body_clean['bmi_category'] = pd.cut(
                body_clean['bmi'],
                bins=[0, 18.5, 25, 30, float('inf')],
                labels=['Underweight', 'Normal', 'Overweight', 'Obese'],
                right=False
            )
        
        return body_clean
    
    def get_blood_pressure(self, cycle: str = '2017-2018') -> pd.DataFrame:
        """Get blood pressure measurements."""
        bp_df = self.download_data(cycle, self.components['blood_pressure'])
        
        if bp_df.empty:
            return bp_df
        
        bp_vars = {
            'SEQN': 'participant_id',
            'BPXSY1': 'systolic_bp_1',
            'BPXDI1': 'diastolic_bp_1',
            'BPXSY2': 'systolic_bp_2',
            'BPXDI2': 'diastolic_bp_2',
            'BPXSY3': 'systolic_bp_3',
            'BPXDI3': 'diastolic_bp_3'
        }
        
        available_vars = [col for col in bp_vars.keys() if col in bp_df.columns]
        bp_clean = bp_df[available_vars].copy()
        bp_clean = bp_clean.rename(columns={k: v for k, v in bp_vars.items() if k in available_vars})
        
        # Calculate average BP (from available readings)
        systolic_cols = [col for col in bp_clean.columns if 'systolic' in col]
        diastolic_cols = [col for col in bp_clean.columns if 'diastolic' in col]
        
        if systolic_cols:
            bp_clean['avg_systolic'] = bp_clean[systolic_cols].mean(axis=1)
        if diastolic_cols:
            bp_clean['avg_diastolic'] = bp_clean[diastolic_cols].mean(axis=1)
        
        # Add hypertension categories
        if 'avg_systolic' in bp_clean.columns and 'avg_diastolic' in bp_clean.columns:
            conditions = [
                (bp_clean['avg_systolic'] < 120) & (bp_clean['avg_diastolic'] < 80),
                (bp_clean['avg_systolic'] < 130) & (bp_clean['avg_diastolic'] < 80),
                ((bp_clean['avg_systolic'] >= 130) & (bp_clean['avg_systolic'] < 140)) | 
                ((bp_clean['avg_diastolic'] >= 80) & (bp_clean['avg_diastolic'] < 90)),
                (bp_clean['avg_systolic'] >= 140) | (bp_clean['avg_diastolic'] >= 90)
            ]
            choices = ['Normal', 'Elevated', 'Stage 1 Hypertension', 'Stage 2 Hypertension']
            bp_clean['bp_category'] = np.select(conditions, choices, default='Unknown')
        
        return bp_clean
    
    def create_merged_dataset(self, cycle: str = '2017-2018') -> pd.DataFrame:
        """Create a merged dataset with demographics and health metrics."""
        print(f"Creating merged dataset for {cycle}...")
        
        # Get main datasets
        demo_df = self.get_demographics_data(cycle)
        body_df = self.get_body_measures(cycle)
        bp_df = self.get_blood_pressure(cycle)
        
        # Start with demographics as base
        merged_df = demo_df.copy()
        
        # Merge body measures
        if not body_df.empty:
            merged_df = merged_df.merge(body_df, on='participant_id', how='left')
        
        # Merge blood pressure
        if not bp_df.empty:
            merged_df = merged_df.merge(bp_df, on='participant_id', how='left')
        
        print(f"Merged dataset created with {len(merged_df)} participants and {len(merged_df.columns)} variables")
        return merged_df
    
    def analyze_by_demographics(self, df: pd.DataFrame, metric: str, demographic: str) -> pd.DataFrame:
        """Analyze health metrics by demographic groups."""
        if metric not in df.columns or demographic not in df.columns:
            print(f"Column {metric} or {demographic} not found in dataset")
            return pd.DataFrame()
        
        # Remove missing values
        analysis_df = df[[demographic, metric]].dropna()
        
        # Calculate statistics by demographic group
        stats = analysis_df.groupby(demographic)[metric].agg([
            'count', 'mean', 'median', 'std', 'min', 'max'
        ]).round(2)
        
        stats.columns = ['Count', 'Mean', 'Median', 'Std Dev', 'Min', 'Max']
        return stats
    
    def create_demographic_visualization(self, df: pd.DataFrame, metric: str, demographic: str):
        """Create visualization of health metric by demographic group."""
        if metric not in df.columns or demographic not in df.columns:
            print(f"Cannot create visualization: missing columns")
            return
        
        fig, axes = plt.subplots(1, 2, figsize=(15, 6))
        
        # Remove missing values
        plot_df = df[[demographic, metric]].dropna()
        
        # Box plot
        sns.boxplot(data=plot_df, x=demographic, y=metric, ax=axes[0])
        axes[0].set_title(f'{metric} by {demographic}')
        axes[0].tick_params(axis='x', rotation=45)
        
        # Bar plot of means
        means = plot_df.groupby(demographic)[metric].mean()
        means.plot(kind='bar', ax=axes[1], color='skyblue')
        axes[1].set_title(f'Mean {metric} by {demographic}')
        axes[1].tick_params(axis='x', rotation=45)
        axes[1].set_ylabel(f'Mean {metric}')
        
        plt.tight_layout()
        plt.show()
    
    def generate_summary_report(self, df: pd.DataFrame) -> str:
        """Generate a summary report of the dataset."""
        report = []
        report.append("NHANES Data Summary Report")
        report.append("=" * 40)
        report.append(f"Total Participants: {len(df):,}")
        report.append(f"Total Variables: {len(df.columns)}")
        report.append("")
        
        # Demographics summary
        if 'age_years' in df.columns:
            report.append("Age Distribution:")
            age_stats = df['age_years'].describe()
            report.append(f"  Mean age: {age_stats['mean']:.1f} years")
            report.append(f"  Age range: {age_stats['min']:.0f} - {age_stats['max']:.0f} years")
            report.append("")
        
        if 'gender_label' in df.columns:
            report.append("Gender Distribution:")
            gender_counts = df['gender_label'].value_counts()
            for gender, count in gender_counts.items():
                pct = (count / len(df)) * 100
                report.append(f"  {gender}: {count:,} ({pct:.1f}%)")
            report.append("")
        
        if 'race_ethnicity_label' in df.columns:
            report.append("Race/Ethnicity Distribution:")
            race_counts = df['race_ethnicity_label'].value_counts()
            for race, count in race_counts.items():
                pct = (count / len(df)) * 100
                report.append(f"  {race}: {count:,} ({pct:.1f}%)")
            report.append("")
        
        # Health metrics summary
        health_metrics = ['bmi', 'avg_systolic', 'avg_diastolic', 'weight_kg', 'height_cm']
        available_metrics = [m for m in health_metrics if m in df.columns]
        
        if available_metrics:
            report.append("Health Metrics Summary:")
            for metric in available_metrics:
                stats = df[metric].describe()
                report.append(f"  {metric}:")
                report.append(f"    Mean: {stats['mean']:.2f}")
                report.append(f"    Range: {stats['min']:.2f} - {stats['max']:.2f}")
                report.append(f"    Missing: {df[metric].isna().sum():,} ({(df[metric].isna().sum()/len(df))*100:.1f}%)")
            report.append("")
        
        return "\n".join(report)
