"""Entry point demo for PopHealth Observatory.

SPDX-License-Identifier: MIT
Copyright (c) 2025 Paul Boys and PopHealth Observatory contributors
"""

from pophealth_observatory import NHANESExplorer


def main():
    """Demonstrate NHANES data exploration capabilities."""

    # Initialize the explorer
    explorer = NHANESExplorer()

    print("PopHealth Observatory Demo")
    print("=" * 50)
    
    # Create merged dataset for latest cycle
    df = explorer.create_merged_dataset('2017-2018')
    
    if df.empty:
        print("No data available. Please check your internet connection.")
        return
    
    # Generate and display summary report
    print("\n" + explorer.generate_summary_report(df))
    
    # Example analyses
    print("\nExample Analysis: BMI by Race/Ethnicity")
    print("-" * 40)
    if 'bmi' in df.columns and 'race_ethnicity_label' in df.columns:
        bmi_by_race = explorer.analyze_by_demographics(df, 'bmi', 'race_ethnicity_label')
        print(bmi_by_race)
        
        # Create visualization
        explorer.create_demographic_visualization(df, 'bmi', 'race_ethnicity_label')
    
    print("\nExample Analysis: Blood Pressure by Gender")
    print("-" * 40)
    if 'avg_systolic' in df.columns and 'gender_label' in df.columns:
        bp_by_gender = explorer.analyze_by_demographics(df, 'avg_systolic', 'gender_label')
        print(bp_by_gender)
        
        # Create visualization
        explorer.create_demographic_visualization(df, 'avg_systolic', 'gender_label')
    
    return df

if __name__ == "__main__":
    # Run the main demonstration
    data = main()
