"""NHANES analysis and reporting service helpers."""

from __future__ import annotations

import pandas as pd


def analyze_by_demographics(df: pd.DataFrame, metric: str, demographic: str) -> pd.DataFrame:
    """Group a metric by demographic and compute descriptive statistics."""
    if metric not in df.columns or demographic not in df.columns:
        return pd.DataFrame()

    subset = df[[demographic, metric]].dropna()
    stats = subset.groupby(demographic)[metric].agg(["count", "mean", "median", "std", "min", "max"]).round(2)
    stats.columns = ["Count", "Mean", "Median", "Std Dev", "Min", "Max"]
    return stats


def create_demographic_visualization(df: pd.DataFrame, metric: str, demographic: str) -> None:
    """Render boxplot and mean bar chart for a metric grouped by demographic."""
    if metric not in df.columns or demographic not in df.columns:
        return

    try:
        import matplotlib.pyplot as plt  # type: ignore
        import seaborn as sns  # type: ignore
    except Exception as exc:  # noqa: BLE001
        print(f"Visualization dependencies not available: {exc}")
        return

    fig, axes = plt.subplots(1, 2, figsize=(15, 6))
    subset = df[[demographic, metric]].dropna()

    sns.boxplot(data=subset, x=demographic, y=metric, ax=axes[0])
    axes[0].set_title(f"{metric} by {demographic}")
    axes[0].tick_params(axis="x", rotation=45)

    means = subset.groupby(demographic)[metric].mean()
    means.plot(kind="bar", ax=axes[1], color="skyblue")
    axes[1].set_title(f"Mean {metric} by {demographic}")
    axes[1].tick_params(axis="x", rotation=45)
    axes[1].set_ylabel(f"Mean {metric}")

    plt.tight_layout()
    plt.show()


def generate_summary_report(df: pd.DataFrame) -> str:
    """Generate textual summary of demographics and selected health metrics."""
    report = [
        "PopHealth Observatory Summary Report",
        "=" * 40,
        f"Total Participants: {len(df):,}",
        f"Total Variables: {len(df.columns)}",
        "",
    ]

    if "age_years" in df.columns:
        age_stats = df["age_years"].describe()
        report += [
            "Age Distribution:",
            f"  Mean age: {age_stats['mean']:.1f} years",
            f"  Age range: {age_stats['min']:.0f} - {age_stats['max']:.0f} years",
            "",
        ]

    if "gender_label" in df.columns:
        gender_counts = df["gender_label"].value_counts()
        report.append("Gender Distribution:")
        for gender, count in gender_counts.items():
            pct = (count / len(df)) * 100
            report.append(f"  {gender}: {count:,} ({pct:.1f}%)")
        report.append("")

    if "race_ethnicity_label" in df.columns:
        race_counts = df["race_ethnicity_label"].value_counts()
        report.append("Race/Ethnicity Distribution:")
        for race, count in race_counts.items():
            pct = (count / len(df)) * 100
            report.append(f"  {race}: {count:,} ({pct:.1f}%)")
        report.append("")

    metrics = ["bmi", "avg_systolic", "avg_diastolic", "weight_kg", "height_cm"]
    available_metrics = [metric for metric in metrics if metric in df.columns]
    if available_metrics:
        report.append("Health Metrics Summary:")
        for metric in available_metrics:
            stats = df[metric].describe()
            missing = df[metric].isna().sum()
            report += [
                f"  {metric}:",
                f"    Mean: {stats['mean']:.2f}",
                f"    Range: {stats['min']:.2f} - {stats['max']:.2f}",
                f"    Missing: {missing:,} ({(missing / len(df)) * 100:.1f}%)",
            ]
        report.append("")

    return "\n".join(report)
