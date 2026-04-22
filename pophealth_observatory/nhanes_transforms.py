"""NHANES harmonization transforms.

Pure transformation helpers extracted from explorer orchestration methods.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def harmonize_demographics(demo_df: pd.DataFrame) -> pd.DataFrame:
    """Harmonize NHANES demographics fields into project schema."""
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


def harmonize_body_measures(bmx_df: pd.DataFrame) -> pd.DataFrame:
    """Harmonize NHANES body measures and derive BMI category."""
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


def harmonize_blood_pressure(bp_df: pd.DataFrame) -> pd.DataFrame:
    """Harmonize NHANES blood pressure readings and derive BP categories."""
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
        choices = [
            "Normal",
            "Elevated",
            "Stage 1 Hypertension",
            "Stage 2 Hypertension",
        ]
        bp_clean["bp_category"] = np.select(conditions, choices, default="Unknown")

    return bp_clean
