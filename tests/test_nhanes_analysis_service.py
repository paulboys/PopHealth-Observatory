import pandas as pd

from pophealth_observatory.nhanes_analysis_service import analyze_by_demographics, generate_summary_report


def test_analysis_service_analyze_by_demographics_expected_stats_columns():
    df = pd.DataFrame(
        {
            "gender": ["Male", "Male", "Female", "Female"],
            "bmi": [25.5, 28.3, 22.1, 24.7],
        }
    )

    stats = analyze_by_demographics(df, "bmi", "gender")

    assert list(stats.columns) == ["Count", "Mean", "Median", "Std Dev", "Min", "Max"]
    assert stats.loc["Male", "Count"] == 2
    assert stats.loc["Female", "Count"] == 2


def test_analysis_service_analyze_by_demographics_missing_column_returns_empty():
    df = pd.DataFrame({"age": [25, 30]})
    result = analyze_by_demographics(df, "bmi", "gender")
    assert result.empty


def test_analysis_service_generate_summary_report_contains_key_sections():
    df = pd.DataFrame(
        {
            "age_years": [25, 40],
            "gender_label": ["Male", "Female"],
            "race_ethnicity_label": ["Non-Hispanic White", "Mexican American"],
            "bmi": [24.5, 31.2],
            "avg_systolic": [118.0, 142.0],
            "avg_diastolic": [76.0, 92.0],
            "weight_kg": [70.0, 88.0],
            "height_cm": [175.0, 168.0],
        }
    )

    report = generate_summary_report(df)

    assert "PopHealth Observatory Summary Report" in report
    assert "Age Distribution:" in report
    assert "Gender Distribution:" in report
    assert "Race/Ethnicity Distribution:" in report
    assert "Health Metrics Summary:" in report
