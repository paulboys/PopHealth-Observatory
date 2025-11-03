# Reproducibility Studies

This directory contains notebooks that **validate PopHealth Observatory by reproducing published research results** from CDC and peer-reviewed literature.

## Purpose

Analytical validation demonstrates that our tool doesn't just download correct data (data integrity validation) but also **produces correct research outputs** when that data is analyzed. This is the gold standard for tool validation in epidemiology and health research.

## Current Studies

### 1. CDC Blood Pressure Reproduction (`cdc_blood_pressure_reproduction.ipynb`)

**Objective:** Reproduce CDC's published weighted mean systolic blood pressure for U.S. adults aged 18+ from the 2017-2018 NHANES cycle.

**Reference:** [CDC NHANES Analytical Guidelines and Tutorial](https://wwwn.cdc.gov/nchs/nhanes/tutorials/default.aspx)

**Target Statistic:** Mean systolic BP ≈ 122.3 mmHg (survey-weighted estimate)

**What This Validates:**
- ✅ Data acquisition accuracy
- ✅ Dataset merging correctness
- ✅ Survey weight identification and application
- ✅ Statistical calculation precision

**Status:** 🟡 In Progress - Requires survey weight implementation

---

## Why Reproducibility Matters

### For Researchers
- **Trust:** If the tool can reproduce CDC's official statistics, it can be trusted for novel analyses
- **Transparency:** Open notebooks show exactly how results are calculated
- **Reusability:** Validated patterns can be adapted for custom research questions

### For Pharma/Industry
- **Regulatory Confidence:** Reproducibility studies provide evidence for regulatory submissions
- **Quality Assurance:** Demonstrates systematic validation, not just spot checks
- **Risk Mitigation:** Reduces risk of basing business decisions on incorrect data

### For Open Source Community
- **Scientific Rigor:** Sets high bar for data tools in public health
- **Knowledge Transfer:** Teaches correct NHANES analysis techniques
- **Collaborative Validation:** Community can verify and extend studies

---

## Validation Criteria

We consider a reproduction **PASSED** if:
1. **< 1% error:** Result within 1% of published value (excellent)
2. **< 5% error:** Result within 5% of published value (acceptable, may need investigation)
3. **> 5% error:** Significant discrepancy requiring investigation (failed)

---

## Roadmap for Additional Studies

### High Priority (Q1 2025)
- [ ] **Obesity Prevalence:** Reproduce CDC obesity rates by demographic groups
- [ ] **Cholesterol Levels:** Validate laboratory component analysis with weights
- [ ] **Dietary Intake:** Reproduce mean dietary intake statistics (tests dietary weights)

### Medium Priority (Q2 2025)
- [ ] **Blood Pressure Categories:** Reproduce hypertension prevalence rates
- [ ] **BMI Trends:** Multi-cycle trend analysis from published literature
- [ ] **Demographic Stratification:** Complex survey design with strata/PSU

### Aspirational (Future)
- [ ] **Published Paper Reproduction:** Select a peer-reviewed NHANES paper and reproduce key findings
- [ ] **Multi-Component Analysis:** Complex analyses requiring multiple data sources
- [ ] **Variance Estimation:** Reproduce confidence intervals using survey design variables

---

## How to Add a New Reproduction Study

1. **Select Target Statistic**
   - Find a published CDC Data Brief, tutorial example, or peer-reviewed paper
   - Identify a specific, clearly stated numerical result (mean, prevalence, etc.)
   - Ensure the data and methodology are well-documented

2. **Create Notebook**
   - Copy template structure from existing notebooks
   - Include full citation of source material
   - Document expected result upfront

3. **Structure the Notebook**
   ```
   1. Objective & Reference
   2. Data Acquisition (with validation)
   3. Data Preparation
   4. Analysis (showing weights, filters, calculations)
   5. Results Comparison
   6. Validation Assessment
   7. Conclusions & Implications
   ```

4. **Test & Document**
   - Run notebook top-to-bottom in clean environment
   - Document any discrepancies and investigation
   - Add to this README with status

---

## Technical Notes

### Survey Weights in NHANES

Different analyses require different weights:

| **Analysis Type** | **Weight Variable** | **Column Name** |
|-------------------|---------------------|-----------------|
| Interview/Questionnaire only | WTINT2YR | `interview_weight` |
| Examination/Lab data | WTMEC2YR | `exam_weight` |
| Dietary data (day 1) | WTDRD1 | `dietary_day1_weight` |

### Variance Estimation

For confidence intervals and hypothesis tests, you also need:
- **SDMVPSU** (`psu`) - Primary sampling unit
- **SDMVSTRA** (`strata`) - Sampling strata

These variables account for NHANES' complex survey design (stratification and clustering).

### Tools & Libraries

- **PopHealth Observatory:** Data acquisition and harmonization
- **NumPy/Pandas:** Weighted mean calculations
- **statsmodels:** Survey-weighted regression and variance estimation (future)
- **Jupyter:** Interactive analysis and documentation

---

## References

1. **NHANES Analytical Guidelines:** https://wwwn.cdc.gov/nchs/nhanes/analyticguidelines.aspx
2. **NHANES Tutorials:** https://wwwn.cdc.gov/nchs/nhanes/tutorials/default.aspx
3. **Survey Weighting Tutorial:** https://wwwn.cdc.gov/nchs/nhanes/tutorials/Weighting.aspx
4. **Module 3: Continuous Variables:** https://wwwn.cdc.gov/nchs/nhanes/tutorials/module3.aspx

---

## Contributing

We welcome community contributions of reproduction studies! Please:
1. Select a reputable published source
2. Follow the notebook structure template
3. Document all assumptions and data filters
4. Submit a PR with your notebook and update to this README

**Questions?** Open an issue on GitHub.
