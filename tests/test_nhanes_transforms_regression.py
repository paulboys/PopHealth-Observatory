import numpy as np
import pandas as pd
from pandas.testing import assert_series_equal

from pophealth_observatory.nhanes_transforms import (
    harmonize_blood_pressure,
    harmonize_body_measures,
    harmonize_demographics,
)


def _legacy_demographics_transform(demo_df: pd.DataFrame) -> pd.DataFrame:
    if demo_df.empty:
        return demo_df

    demo_vars = {
        "SEQN": "participant_id",
        "RIAGENDR": "gender",
        "RIDAGEYR": "age_years",
        "RIDRETH3": "race_ethnicity",
        "DMDEDUC2": "education",
        "INDFMPIR": "poverty_ratio",
        "WTMEC2YR": "exam_weight",
        "WTINT2YR": "interview_weight",
        "WTDRD1": "dietary_day1_weight",
        "SDMVPSU": "psu",
        "SDMVSTRA": "strata",
    }
    available = [c for c in demo_vars if c in demo_df.columns]
    demo_clean = demo_df[available].copy().rename(columns={k: v for k, v in demo_vars.items() if k in available})
    if "gender" in demo_clean.columns:
        demo_clean["gender_label"] = demo_clean["gender"].map({1: "Male", 2: "Female"})
    if "race_ethnicity" in demo_clean.columns:
        race_labels = {
            1: "Mexican American",
            2: "Other Hispanic",
            3: "Non-Hispanic White",
            4: "Non-Hispanic Black",
            6: "Non-Hispanic Asian",
            7: "Other/Multi-racial",
        }
        demo_clean["race_ethnicity_label"] = demo_clean["race_ethnicity"].map(race_labels)
    return demo_clean


def _legacy_body_measures_transform(bmx_df: pd.DataFrame) -> pd.DataFrame:
    if bmx_df.empty:
        return bmx_df

    body_vars = {
        "SEQN": "participant_id",
        "BMXWT": "weight_kg",
        "BMXHT": "height_cm",
        "BMXBMI": "bmi",
        "BMXWAIST": "waist_cm",
    }
    available = [c for c in body_vars if c in bmx_df.columns]
    body_clean = bmx_df[available].copy().rename(columns={k: v for k, v in body_vars.items() if k in available})
    if "bmi" in body_clean.columns:
        body_clean["bmi_category"] = pd.cut(
            body_clean["bmi"],
            bins=[0, 18.5, 25, 30, float("inf")],
            labels=["Underweight", "Normal", "Overweight", "Obese"],
            right=False,
        )
    return body_clean


def _legacy_blood_pressure_transform(bp_df: pd.DataFrame) -> pd.DataFrame:
    if bp_df.empty:
        return bp_df

    bp_vars = {
        "SEQN": "participant_id",
        "BPXSY1": "systolic_bp_1",
        "BPXDI1": "diastolic_bp_1",
        "BPXSY2": "systolic_bp_2",
        "BPXDI2": "diastolic_bp_2",
        "BPXSY3": "systolic_bp_3",
        "BPXDI3": "diastolic_bp_3",
    }
    available = [c for c in bp_vars if c in bp_df.columns]
    bp_clean = bp_df[available].copy().rename(columns={k: v for k, v in bp_vars.items() if k in available})
    systolic_cols = [c for c in bp_clean.columns if "systolic" in c]
    diastolic_cols = [c for c in bp_clean.columns if "diastolic" in c]
    if systolic_cols:
        bp_clean["avg_systolic"] = bp_clean[systolic_cols].mean(axis=1)
    if diastolic_cols:
        bp_clean["avg_diastolic"] = bp_clean[diastolic_cols].mean(axis=1)
    if "avg_systolic" in bp_clean.columns and "avg_diastolic" in bp_clean.columns:
        conditions = [
            (bp_clean["avg_systolic"] < 120) & (bp_clean["avg_diastolic"] < 80),
            (bp_clean["avg_systolic"] < 130) & (bp_clean["avg_diastolic"] < 80),
            ((bp_clean["avg_systolic"] >= 130) & (bp_clean["avg_systolic"] < 140))
            | ((bp_clean["avg_diastolic"] >= 80) & (bp_clean["avg_diastolic"] < 90)),
            (bp_clean["avg_systolic"] >= 140) | (bp_clean["avg_diastolic"] >= 90),
        ]
        choices = ["Normal", "Elevated", "Stage 1 Hypertension", "Stage 2 Hypertension"]
        bp_clean["bp_category"] = np.select(conditions, choices, default="Unknown")
    return bp_clean


def test_demographics_transform_regression_columns_and_derived_fields():
    source = pd.DataFrame(
        {
            "SEQN": [1, 2, 3],
            "RIAGENDR": [1, 2, 9],
            "RIDAGEYR": [25, 40, 65],
            "RIDRETH3": [3, 1, 7],
            "DMDEDUC2": [4, 3, 2],
            "INDFMPIR": [1.0, 2.2, 0.7],
            "WTMEC2YR": [1000.0, 2000.0, 1500.0],
            "WTINT2YR": [1200.0, 2200.0, 1700.0],
            "WTDRD1": [900.0, 1600.0, 1300.0],
            "SDMVPSU": [1, 1, 2],
            "SDMVSTRA": [10, 10, 11],
        }
    )

    legacy = _legacy_demographics_transform(source)
    extracted = harmonize_demographics(source)

    assert list(extracted.columns) == list(legacy.columns)
    assert_series_equal(extracted["gender_label"], legacy["gender_label"], check_names=False)
    assert_series_equal(extracted["race_ethnicity_label"], legacy["race_ethnicity_label"], check_names=False)


def test_body_measures_transform_regression_columns_and_derived_fields():
    source = pd.DataFrame(
        {
            "SEQN": [1, 2, 3, 4],
            "BMXWT": [55.0, 70.0, 85.0, 95.0],
            "BMXHT": [170.0, 170.0, 170.0, 170.0],
            "BMXBMI": [19.0, 24.9, 27.2, 33.0],
            "BMXWAIST": [70.0, 82.0, 95.0, 105.0],
        }
    )

    legacy = _legacy_body_measures_transform(source)
    extracted = harmonize_body_measures(source)

    assert list(extracted.columns) == list(legacy.columns)
    assert_series_equal(
        extracted["bmi_category"].astype(str),
        legacy["bmi_category"].astype(str),
        check_names=False,
    )


def test_blood_pressure_transform_regression_columns_and_derived_fields():
    source = pd.DataFrame(
        {
            "SEQN": [1, 2, 3, 4],
            "BPXSY1": [118, 125, 134, 145],
            "BPXDI1": [76, 78, 85, 95],
            "BPXSY2": [119, 126, 133, 144],
            "BPXDI2": [77, 79, 84, 94],
            "BPXSY3": [120, 124, 132, 146],
            "BPXDI3": [78, 77, 86, 96],
        }
    )

    legacy = _legacy_blood_pressure_transform(source)
    extracted = harmonize_blood_pressure(source)

    assert list(extracted.columns) == list(legacy.columns)
    assert_series_equal(extracted["avg_systolic"], legacy["avg_systolic"], check_names=False)
    assert_series_equal(extracted["avg_diastolic"], legacy["avg_diastolic"], check_names=False)
    assert_series_equal(extracted["bp_category"], legacy["bp_category"], check_names=False)
