# Methodology & Limitations

## Purpose & Scope

PopHealth Observatory is an **exploratory analytics platform** for Real-World Evidence (RWE) signal scanning using publicly available U.S. population health survey data. It is designed for:

- **Directional pattern identification** (not formal statistical inference)
- **Early hypothesis generation** (before rigorous validation)
- **Rapid trend visualization** (multi-cycle, geographic)
- **Internal dashboarding** (business intelligence, market sensing)

## What This Tool Is NOT

❌ **Not a clinical decision support system**
❌ **Not validated for regulatory submissions**
❌ **Not a replacement for formal epidemiologic analysis**
❌ **Not designed for patient-level intervention decisions**

## Current Analytical Approach

### Survey Weights (Simplified)
- **NHANES**: Uses exam weights (`WTMEC2YR` or equivalent) for weighted means
- **BRFSS**: Uses state-level aggregated prevalence (no individual weights applied)
- **Limitation**: Does not account for complex survey design effects (strata, PSU, finite population correction)
- **Impact**: Confidence intervals are approximate; point estimates directionally correct but variance underestimated

### Statistical Methods
- **Descriptive statistics**: Mean, median, standard deviation, count
- **Bivariate analysis**: Pearson correlation, OLS trendline (unadjusted)
- **Trend analysis**: Time-series plotting with 95% CI bands (based on standard error, not design-adjusted variance)
- **No adjustments for**: Multiple comparisons, confounding, selection bias, measurement error

### Data Quality
- **Source**: CDC NHANES (XPT files) and BRFSS (Socrata API)
- **Validation**: Programmatic integrity checks (row counts, URL availability)
- **Reproducibility**: Analytical validation notebooks in progress (see `reproducibility/` directory)
- **Missingness**: Handled via `dropna()` for specific analyses; no imputation

## Appropriate Use Cases

✅ **Exploratory dashboards** for internal stakeholders
✅ **Preliminary market sizing** or trend sensing
✅ **Hypothesis generation** before designing formal studies
✅ **Educational demonstrations** of population health patterns
✅ **Open-source prototyping** for method development

## Inappropriate Use Cases

🚫 Regulatory filings or submissions (FDA, EMA, etc.)
🚫 Clinical practice guidelines or treatment decisions
🚫 Legal evidence without expert epidemiologist review
🚫 Publication-grade inference without proper survey variance adjustment
🚫 High-stakes business decisions without validation layer

## Roadmap for Enhanced Rigor

**Version 0.7.0+**:
- Complex survey design variance (stratification, PSU, replicate weights)
- Survey package integration (R `survey` or Python `samplics`)
- Design effect documentation per indicator

**Version 1.0+**:
- Configurable rigor profiles (exploratory vs. validated modes)
- Expanded analytical validation (concordance with published CDC estimates)
- Propensity weighting for external validity adjustments

## Recommended Workflow

1. **Explore**: Use PopHealth Observatory for signal detection and trend visualization
2. **Validate**: Consult formal epidemiologic methods (complex survey packages, subject-matter experts)
3. **Document**: Record assumptions, limitations, and validation steps
4. **Decide**: Apply insights within appropriate decision context (internal planning, hypothesis refinement)

## Disclaimer

This tool is provided "as is" under the MIT License. Users are responsible for determining fitness for their specific use case. For publication-grade or regulatory-grade analysis, consult qualified biostatisticians and epidemiologists.

---

**Questions or feedback?**
Open an issue on [GitHub](https://github.com/paulboys/PopHealth-Observatory/issues) or contact the maintainers.
