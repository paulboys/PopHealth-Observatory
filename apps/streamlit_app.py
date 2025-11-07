"""Interactive NHANES & BRFSS exploration app using Streamlit.

Scientific visualization with tiered caching, survey weights, and trend analysis.

SPDX-License-Identifier: MIT
"""

import importlib.metadata as _md
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

try:
    from PIL import Image  # Pillow for logo processing
except ImportError:  # pragma: no cover - optional dependency during build
    Image = None

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st


def _ensure_package_import() -> tuple[object, object, str]:
    """Robust import for internal package classes.

    Attempts normal import of BRFSSExplorer & NHANESExplorer; if the package
    isn't installed (e.g. requirements.txt failed to install "."), inject the
    repository root onto ``sys.path`` and retry.

    Returns
    -------
    tuple
        (BRFSSExplorer, NHANESExplorer, mode) where mode is ``'installed'`` or
        ``'fallback'`` indicating whether a path injection was needed.

    Raises
    ------
    RuntimeError
        If import still fails after path injection.
    """
    try:
        from pophealth_observatory import BRFSSExplorer, NHANESExplorer  # type: ignore

        return BRFSSExplorer, NHANESExplorer, "installed"
    except ModuleNotFoundError:
        repo_root = Path(__file__).resolve().parents[1]
        if str(repo_root) not in sys.path:
            sys.path.insert(0, str(repo_root))
        try:
            from pophealth_observatory import BRFSSExplorer, NHANESExplorer  # type: ignore

            return BRFSSExplorer, NHANESExplorer, "fallback"
        except ModuleNotFoundError as e:
            raise RuntimeError(
                "Failed to import pophealth_observatory even after sys.path injection. "
                f"Working dir={os.getcwd()} sys.path snapshot length={len(sys.path)}"
            ) from e


BRFSSExplorer, NHANESExplorer, _IMPORT_MODE = _ensure_package_import()

try:  # Dynamic version from installed metadata (fallback to 'unknown')
    __version__ = _md.version("pophealth-observatory")
except Exception:  # pragma: no cover - very unlikely unless metadata missing
    __version__ = "unknown"

st.set_page_config(page_title="PopHealth Observatory Explorer", layout="wide")

if _IMPORT_MODE == "fallback":
    st.warning(
        "⚠️ Package wasn't installed normally. Using fallback sys.path injection. "
        "Ensure requirements.txt contains a single line '.' to install the project root."
    )

# ============================================================================
# LAYER 1: Raw Data Cache (Expensive - 20-60s load)
# ============================================================================


@st.cache_data(ttl=3600, show_spinner="Loading NHANES cycle data...")
def load_nhanes_cycle(cycle: str) -> tuple[NHANESExplorer, pd.DataFrame]:
    """Cache raw NHANES data for selected cycle."""
    explorer = NHANESExplorer()
    merged = explorer.create_merged_dataset(cycle)
    return explorer, merged


@st.cache_data(ttl=3600, show_spinner=False)
def get_brfss_raw_data() -> pd.DataFrame:
    """Cache raw BRFSS data from local file or API fallback."""
    from pathlib import Path

    # Try to load from local Parquet file first (fast)
    local_file = Path(__file__).parent.parent / "data" / "processed" / "brfss_indicators.parquet"

    if local_file.exists():
        try:
            df = pd.read_parquet(local_file)
            return df
        except Exception as e:
            st.warning(f"Could not load local BRFSS file: {e}. Falling back to API...")

    # Fallback to API if local file doesn't exist
    brfss = BRFSSExplorer()
    return brfss._get_raw(limit=brfss.config.default_limit)


@st.cache_data(ttl=3600, show_spinner=False)
def get_available_indicators() -> pd.DataFrame:
    """Cache list of available indicators."""
    brfss = BRFSSExplorer()
    return brfss.list_available_indicators()


@st.cache_data(ttl=1800, show_spinner=False)
def get_indicator_data(indicator_class: str, indicator_question: str) -> pd.DataFrame:
    """Cache filtered and normalized data for a specific indicator (all years)."""
    raw_data = get_brfss_raw_data()
    filtered_data = raw_data[
        (raw_data["class"] == indicator_class) & (raw_data["question"] == indicator_question)
    ].copy()

    if not filtered_data.empty:
        # Normalize column names to match expected format
        brfss_df = filtered_data.rename(
            columns={"yearstart": "year", "locationabbr": "state", "locationdesc": "state_name", "data_value": "value"}
        )

        # Convert types for proper visualization
        brfss_df["value"] = pd.to_numeric(brfss_df["value"], errors="coerce")
        brfss_df["year"] = pd.to_numeric(brfss_df["year"], errors="coerce").dropna().astype(int)

        # Remove rows with missing values
        brfss_df = brfss_df.dropna(subset=["value", "year", "state"])

        # Sort by year for proper animation sequence
        brfss_df = brfss_df.sort_values("year")

        return brfss_df
    else:
        return pd.DataFrame()


# ============================================================================
# LAYER 2: Filtered Data Cache (Medium - 1-5s)
# ============================================================================


@st.cache_data(ttl=1800, show_spinner=False)
def apply_nhanes_filters(
    df: pd.DataFrame, age_range: tuple[int, int], genders: list[str], races: list[str]
) -> pd.DataFrame:
    """Apply demographic filters to NHANES data."""
    filtered = df.copy()

    if "age_years" in df.columns:
        filtered = filtered[(filtered["age_years"] >= age_range[0]) & (filtered["age_years"] <= age_range[1])]

    if genders and "gender_label" in df.columns:
        filtered = filtered[filtered["gender_label"].isin(genders)]

    if races and "race_ethnicity_label" in df.columns:
        filtered = filtered[filtered["race_ethnicity_label"].isin(races)]

    return filtered


# ============================================================================
# LAYER 3: Aggregation Cache (Fast - <500ms)
# ============================================================================


@st.cache_data(ttl=600, show_spinner=False)
def compute_nhanes_summary(df: pd.DataFrame, metric: str, demographic: str, use_weights: bool = False) -> pd.DataFrame:
    """Compute summary statistics with optional survey weights."""
    if metric not in df.columns or demographic not in df.columns:
        return pd.DataFrame()

    subset = df[[demographic, metric]].dropna()
    if subset.empty:
        return pd.DataFrame()

    if use_weights and "exam_weight" in df.columns:
        # Weighted statistics (simplified; production would use proper variance estimation)
        def weighted_stats(group):
            if "exam_weight" not in group.columns:
                return pd.Series({"count": 0, "mean": np.nan, "median": np.nan, "std": np.nan})

            weights = group["exam_weight"].values
            values = group[metric].values

            if len(values) == 0 or weights.sum() == 0:
                return pd.Series({"count": 0, "mean": np.nan, "median": np.nan, "std": np.nan})

            wmean = np.average(values, weights=weights)
            wvar = np.average((values - wmean) ** 2, weights=weights)

            return pd.Series({"count": len(group), "mean": wmean, "median": wmean, "std": np.sqrt(wvar)})

        summary = df.groupby(demographic).apply(weighted_stats, include_groups=False).reset_index()
    else:
        summary = subset.groupby(demographic)[metric].agg(["count", "mean", "median", "std"]).reset_index()

    return summary


@st.cache_data(ttl=1800, show_spinner="Computing trends across cycles...")
def compute_trend_data(
    cycles: list[str],
    metric: str,
    demographic_groups: list[str],
    age_range: tuple[int, int],
    genders: list[str],
    races: list[str],
    use_weights: bool,
) -> pd.DataFrame:
    """Compute trend data across multiple cycles (parallelized)."""

    def process_cycle(cycle: str):
        try:
            _, df = load_nhanes_cycle(cycle)
            df_filtered = apply_nhanes_filters(df, age_range, genders, races)

            if df_filtered.empty or metric not in df_filtered.columns:
                return []

            results = []
            for group_col in ["gender_label", "race_ethnicity_label"]:
                if group_col in df_filtered.columns:
                    for group_val in demographic_groups:
                        group_df = df_filtered[df_filtered[group_col] == group_val]
                        if not group_df.empty and metric in group_df.columns:
                            values = group_df[metric].dropna()
                            if len(values) > 0:
                                if use_weights and "exam_weight" in group_df.columns:
                                    weights = group_df.loc[values.index, "exam_weight"].values
                                    mean_val = np.average(values, weights=weights)
                                    std_val = np.sqrt(np.average((values - mean_val) ** 2, weights=weights))
                                else:
                                    mean_val = values.mean()
                                    std_val = values.std()

                                # 95% CI approximation
                                ci_margin = 1.96 * std_val / np.sqrt(len(values))

                                results.append(
                                    {
                                        "cycle": cycle,
                                        "group": group_val,
                                        "mean": mean_val,
                                        "ci_lower": mean_val - ci_margin,
                                        "ci_upper": mean_val + ci_margin,
                                        "n": len(values),
                                    }
                                )
            return results
        except Exception as e:
            st.warning(f"Error processing cycle {cycle}: {e}")
            return []

    # Parallel processing for multiple cycles
    with ThreadPoolExecutor(max_workers=5) as executor:
        all_results = list(executor.map(process_cycle, cycles))

    # Flatten results
    flat_results = [item for sublist in all_results for item in sublist]
    return pd.DataFrame(flat_results)


# ============================================================================
# LAYER 4: Visualization Helpers (Instant - <100ms, not cached)
# ============================================================================


def create_box_plot(df: pd.DataFrame, metric: str, demographic: str, title: str) -> go.Figure:
    """Create interactive box plot with Plotly."""
    fig = px.box(
        df,
        x=demographic,
        y=metric,
        color=demographic,
        template="plotly_white",
        title=title,
        labels={metric: metric.replace("_", " ").title(), demographic: demographic.replace("_", " ").title()},
    )

    fig.update_traces(boxmean="sd")  # Show mean and std dev
    fig.update_layout(showlegend=False, height=500)

    return fig


def create_trend_plot(trend_df: pd.DataFrame, metric: str, title: str) -> go.Figure:
    """Create line plot with confidence intervals for trend analysis."""
    fig = go.Figure()

    for group in trend_df["group"].unique():
        group_data = trend_df[trend_df["group"] == group].sort_values("cycle")

        # Main line
        fig.add_trace(
            go.Scatter(
                x=group_data["cycle"],
                y=group_data["mean"],
                mode="lines+markers",
                name=group,
                line=dict(width=2),
                marker=dict(size=8),
            )
        )

        # Confidence interval shading
        fig.add_trace(
            go.Scatter(
                x=list(group_data["cycle"]) + list(group_data["cycle"][::-1]),
                y=list(group_data["ci_upper"]) + list(group_data["ci_lower"][::-1]),
                fill="toself",
                fillcolor=px.colors.qualitative.Plotly[len(fig.data) // 2 % 10],
                opacity=0.2,
                line=dict(width=0),
                showlegend=False,
                hoverinfo="skip",
            )
        )

    fig.update_layout(
        template="plotly_white",
        title=title,
        xaxis_title="Survey Cycle",
        yaxis_title=metric.replace("_", " ").title(),
        hovermode="x unified",
        height=500,
    )

    return fig


def create_choropleth_map(brfss_df: pd.DataFrame, value_col: str, title: str, animated: bool = False) -> go.Figure:
    """Create US state choropleth map for BRFSS data.

    Parameters
    ----------
    brfss_df : pd.DataFrame
        BRFSS data with state, value, and optionally year columns
    value_col : str
        Column name containing the value to visualize
    title : str
        Chart title
    animated : bool
        If True, creates animated choropleth with year as animation frame
    """
    if animated and "year" in brfss_df.columns:
        # Animated choropleth with timeline slider
        fig = px.choropleth(
            brfss_df,
            locations="state",
            locationmode="USA-states",
            color=value_col,
            scope="usa",
            title=title,
            color_continuous_scale="YlOrRd",
            labels={value_col: "Prevalence (%)"},
            animation_frame="year",
            hover_name="state_name",
            hover_data={"state": False, value_col: ":.1f", "year": True},
            range_color=[brfss_df[value_col].min(), brfss_df[value_col].max()],  # Fixed scale across years
        )

        # Customize animation settings
        fig.layout.updatemenus[0].buttons[0].args[1]["frame"]["duration"] = 800  # ms per frame
        fig.layout.updatemenus[0].buttons[0].args[1]["transition"]["duration"] = 300  # transition duration

    else:
        # Static single-year choropleth
        fig = px.choropleth(
            brfss_df,
            locations="state",
            locationmode="USA-states",
            color=value_col,
            scope="usa",
            title=title,
            color_continuous_scale="YlOrRd",
            labels={value_col: "Prevalence (%)"},
            hover_name="state_name",
            hover_data={"state": False, value_col: ":.1f"},
        )

    fig.update_layout(template="plotly_white", height=600)

    return fig


def get_asset_path(filename: str) -> Path:
    """Resolve an asset path relative to the repository.

    Checks common asset directories and returns the first match; otherwise
    returns the preferred docs/assets/images location even if missing.

    Parameters
    ----------
    filename : str
        Asset file name (e.g. 'data_analysis_flowchart.png').

    Returns
    -------
    Path
        Filesystem path where the asset should live.
    """
    candidates = [
        Path(__file__).parent.parent / "docs" / "assets" / "images" / filename,
        Path(__file__).parent.parent / "site" / "assets" / "images" / filename,
    ]
    for c in candidates:
        if c.exists():
            return c
    return candidates[0]


def ensure_dark_logo(original: Path) -> Path:
    """Create a dark/transparent variant of the logo next to the original.

    Processing steps:
    - Convert to RGBA
    - Any near-white pixel (all channels >= 235) -> fully transparent
    - Remaining pixels darkened (20% of original) for dark theme contrast

    If Pillow is not available or processing fails, returns the original path.

    Parameters
    ----------
    original : Path
        Path to original logo image.

    Returns
    -------
    Path
        Path to dark logo (existing or newly created) or original if skipped.
    """
    try:
        if Image is None or not original.exists():
            return original
        dark_path = original.with_name(original.stem + "_dark" + original.suffix)
        if dark_path.exists():
            return dark_path
        img = Image.open(original).convert("RGBA")
        pixels = img.getdata()
        new_pixels = []
        for r, g, b, a in pixels:
            if r >= 235 and g >= 235 and b >= 235:  # near-white -> transparent
                new_pixels.append((r, g, b, 0))
            else:
                new_pixels.append((int(r * 0.2), int(g * 0.2), int(b * 0.2), a))
        img.putdata(new_pixels)
        img.save(dark_path)
        return dark_path
    except Exception:
        return original


# ============================================================================
# MAIN APP
# ============================================================================

_logo_path = get_asset_path("data_analysis_flowchart.png")
_dark_logo_path = ensure_dark_logo(_logo_path)

logo_col, title_col = st.columns([1, 4])
with logo_col:
    if _dark_logo_path.exists():
        st.image(str(_dark_logo_path), use_column_width=True)
    elif _logo_path.exists():
        st.image(str(_logo_path), use_column_width=True)
    else:
        st.write("[logo missing]")

with title_col:
    st.title("PopHealth Observatory Explorer")
    st.caption("Exploratory analysis of U.S. population health data (NHANES & BRFSS)")

st.markdown("---")

# Sidebar: About & Info
with st.sidebar:
    st.header("ℹ️ About")

    st.markdown(
        """
    **PopHealth Observatory** delivers exploratory RWE population health insights — directional signal scanning.

    📊 **Data Sources:**
    - NHANES (CDC): National-level clinical measurements
    - BRFSS (CDC): State-level health indicators

    🧪 **Scope:**
    - Directional patterns & early hypothesis generation
    - Multi-cycle trends & geographic prevalence mapping
    - Optional survey weight summaries

    🚫 **Not:**
    - Formal statistical inference
    - Clinical decision support
    - Regulatory submission-grade analysis
    """
    )

    st.markdown("---")

    st.markdown(
        """
    **🔗 Links:**
    - [GitHub Repository](https://github.com/paulboys/PopHealth-Observatory)
    - [Documentation](https://paulboys.github.io/PopHealth-Observatory/)
    """
    )

    st.markdown("---")
    st.caption(f"v{__version__} | MIT License")

# Tabs for different analysis modes
tab1, tab2, tab3, tab4 = st.tabs(
    ["📊 Cross-Sectional Explorer", "📈 Trend Analysis", "🔗 Bivariate Analysis", "🗺️ Geographic View (BRFSS)"]
)

# ============================================================================
# TAB 1: Cross-Sectional Explorer
# ============================================================================

with tab1:
    st.header("Cross-Sectional Analysis")
    st.caption("Explore a single NHANES cycle with demographic stratification")

    # Cycle selector (local to this tab)
    nhanes_cycle_tab1 = st.selectbox(
        "NHANES Cycle",
        ["2017-2018", "2015-2016", "2013-2014", "2011-2012", "2009-2010", "2021-2022"],
        key="nhanes_cycle_tab1",
        help="Select survey cycle for cross-sectional analysis",
    )

    # Demographic filters (local to this tab)
    with st.expander("⚙️ Demographic Filters", expanded=True):
        col_f1, col_f2 = st.columns(2)

        with col_f1:
            age_range_tab1 = st.slider("Age Range", 0, 80, (20, 60), key="age_tab1", help="Filter participants by age")

            available_genders = ["Male", "Female"]
            selected_genders_tab1 = st.multiselect(
                "Gender", available_genders, default=available_genders, key="gender_tab1"
            )

        with col_f2:
            use_weights_tab1 = st.checkbox(
                "Apply Survey Weights ⚖️",
                value=False,
                key="weights_tab1",
                help="Use NHANES exam weights for population estimates",
            )

            available_races = [
                "Non-Hispanic White",
                "Non-Hispanic Black",
                "Mexican American",
                "Other Hispanic",
                "Non-Hispanic Asian",
                "Other Race",
            ]
            selected_races_tab1 = st.multiselect(
                "Race/Ethnicity", available_races, default=available_races, key="race_tab1"
            )

    col1, col2, col3 = st.columns(3)

    with col1:
        metric = st.selectbox(
            "Health Metric",
            ["bmi", "avg_systolic", "avg_diastolic", "weight_kg", "height_cm", "waist_cm"],
            help="Select outcome variable",
        )

    with col2:
        demographic = st.selectbox(
            "Stratify By", ["gender_label", "race_ethnicity_label", "education"], help="Group data by demographic"
        )

    with col3:
        viz_type = st.selectbox("Visualization", ["Box Plot", "Violin Plot", "Summary Table"], index=0)

    # Load and filter data
    with st.spinner(f"Loading {nhanes_cycle_tab1} data..."):
        explorer, df_raw = load_nhanes_cycle(nhanes_cycle_tab1)

    if df_raw.empty:
        st.error(f"⚠️ Failed to load dataset for cycle **{nhanes_cycle_tab1}**.")
        st.info("Try selecting **2017-2018** for complete data.")
        st.stop()

    df_filtered = apply_nhanes_filters(df_raw, age_range_tab1, selected_genders_tab1, selected_races_tab1)

    if df_filtered.empty:
        st.warning("No data matches the selected filters. Try broadening your criteria.")
    else:
        # Display summary metrics
        if metric in df_filtered.columns:
            col1, col2, col3, col4 = st.columns(4)
            values = df_filtered[metric].dropna()

            with col1:
                st.metric("Sample Size", f"{len(df_filtered):,}")
            with col2:
                st.metric("Mean", f"{values.mean():.2f}")
            with col3:
                st.metric("Median", f"{values.median():.2f}")
            with col4:
                st.metric("Std Dev", f"{values.std():.2f}")

            st.markdown("---")

            # Visualization
            if viz_type == "Box Plot":
                if demographic in df_filtered.columns:
                    title = f"{metric.replace('_', ' ').title()} by {demographic.replace('_', ' ').title()}"
                    if use_weights_tab1:
                        title += " (Weighted)"
                    fig = create_box_plot(df_filtered, metric, demographic, title)
                    st.plotly_chart(fig, use_container_width=True)
                    st.caption(
                        "📦 Box plot shows median (line), interquartile range (box), and outliers (points). "
                        "Mean and standard deviation are overlaid."
                    )
                else:
                    st.warning(f"Demographic '{demographic}' not found in dataset.")

            elif viz_type == "Violin Plot":
                if demographic in df_filtered.columns:
                    title = (
                        f"{metric.replace('_', ' ').title()} Distribution by {demographic.replace('_', ' ').title()}"
                    )
                    fig = px.violin(
                        df_filtered,
                        x=demographic,
                        y=metric,
                        color=demographic,
                        box=True,
                        template="plotly_white",
                        title=title,
                    )
                    fig.update_layout(showlegend=False, height=500)
                    st.plotly_chart(fig, use_container_width=True)
                    st.caption("🎻 Violin plot combines box plot with probability density (width = frequency).")
                else:
                    st.warning(f"Demographic '{demographic}' not found in dataset.")

            elif viz_type == "Summary Table":
                summary = compute_nhanes_summary(df_filtered, metric, demographic, use_weights_tab1)
                if not summary.empty:
                    st.dataframe(summary, use_container_width=True)
                    st.caption("📊 Summary statistics computed using pandas groupby aggregation.")
                else:
                    st.warning("Unable to compute summary statistics.")
        else:
            st.error(f"Metric '{metric}' not found in the dataset for this cycle.")

# ============================================================================
# TAB 2: Trend Analysis
# ============================================================================

with tab2:
    st.header("Trend Analysis Across Survey Cycles")
    st.caption("Visualize how health metrics change over time")

    # Demographic filters (local to this tab)
    with st.expander("⚙️ Demographic Filters", expanded=False):
        col_f1, col_f2 = st.columns(2)

        with col_f1:
            age_range_tab2 = st.slider("Age Range", 0, 80, (20, 60), key="age_tab2", help="Filter participants by age")

            available_genders = ["Male", "Female"]
            selected_genders_tab2 = st.multiselect(
                "Gender", available_genders, default=available_genders, key="gender_tab2"
            )

        with col_f2:
            use_weights_tab2 = st.checkbox(
                "Apply Survey Weights ⚖️",
                value=False,
                key="weights_tab2",
                help="Use NHANES exam weights for population estimates",
            )

            available_races = [
                "Non-Hispanic White",
                "Non-Hispanic Black",
                "Mexican American",
                "Other Hispanic",
                "Non-Hispanic Asian",
                "Other Race",
            ]
            selected_races_tab2 = st.multiselect(
                "Race/Ethnicity", available_races, default=available_races, key="race_tab2"
            )

    col1, col2 = st.columns(2)

    with col1:
        trend_metric = st.selectbox(
            "Metric to Track",
            ["bmi", "avg_systolic", "avg_diastolic", "weight_kg", "height_cm"],
            key="trend_metric",
            help="Select metric to track over time",
        )

    with col2:
        trend_cycles = st.multiselect(
            "Survey Cycles",
            ["2017-2018", "2015-2016", "2013-2014", "2011-2012", "2009-2010"],
            default=["2017-2018", "2015-2016", "2013-2014"],
            help="Select cycles to compare (more cycles = longer processing time)",
        )

    trend_groups = st.multiselect(
        "Compare Groups",
        available_genders + available_races,
        default=["Male", "Female"],
        help="Select demographic groups to compare",
    )

    if st.button("🔄 Compute Trends", type="primary"):
        if not trend_cycles:
            st.warning("Please select at least one survey cycle.")
        elif not trend_groups:
            st.warning("Please select at least one demographic group to compare.")
        else:
            trend_df = compute_trend_data(
                trend_cycles,
                trend_metric,
                trend_groups,
                age_range_tab2,
                selected_genders_tab2,
                selected_races_tab2,
                use_weights_tab2,
            )

            if trend_df.empty:
                st.error("No trend data could be computed. Check your filters and try again.")
            else:
                title = f"{trend_metric.replace('_', ' ').title()} Trends"
                if use_weights_tab2:
                    title += " (Weighted)"
                fig = create_trend_plot(trend_df, trend_metric, title)
                st.plotly_chart(fig, use_container_width=True)

                st.caption(
                    "📈 Line shows mean value; shaded area represents 95% confidence interval. "
                    "Hover for exact values and sample sizes."
                )

                with st.expander("📊 View Trend Data Table"):
                    st.dataframe(trend_df, use_container_width=True)
    else:
        st.info("👆 Click the button above to compute and visualize trends across selected cycles.")

# ============================================================================
# TAB 3: Bivariate Analysis
# ============================================================================

with tab3:
    st.header("Bivariate Analysis")
    st.caption("Explore relationships between two health metrics")

    # Cycle selector (local to this tab)
    nhanes_cycle_tab3 = st.selectbox(
        "NHANES Cycle",
        ["2017-2018", "2015-2016", "2013-2014", "2011-2012", "2009-2010", "2021-2022"],
        key="nhanes_cycle_tab3",
        help="Select survey cycle for bivariate analysis",
    )

    # Demographic filters (local to this tab)
    with st.expander("⚙️ Demographic Filters", expanded=False):
        col_f1, col_f2 = st.columns(2)

        with col_f1:
            age_range_tab3 = st.slider("Age Range", 0, 80, (20, 60), key="age_tab3", help="Filter participants by age")

            available_genders = ["Male", "Female"]
            selected_genders_tab3 = st.multiselect(
                "Gender", available_genders, default=available_genders, key="gender_tab3"
            )

        with col_f2:
            use_weights_tab3 = st.checkbox(
                "Apply Survey Weights ⚖️",
                value=False,
                key="weights_tab3",
                help="Use NHANES exam weights for population estimates",
            )

            available_races = [
                "Non-Hispanic White",
                "Non-Hispanic Black",
                "Mexican American",
                "Other Hispanic",
                "Non-Hispanic Asian",
                "Other Race",
            ]
            selected_races_tab3 = st.multiselect(
                "Race/Ethnicity", available_races, default=available_races, key="race_tab3"
            )

    col1, col2 = st.columns(2)

    with col1:
        x_metric = st.selectbox(
            "X-Axis Metric", ["bmi", "weight_kg", "height_cm", "waist_cm", "age_years"], key="x_metric"
        )

    with col2:
        y_metric = st.selectbox("Y-Axis Metric", ["avg_systolic", "avg_diastolic", "bmi", "weight_kg"], key="y_metric")

    color_by = st.selectbox("Color By", [None, "gender_label", "race_ethnicity_label"], index=0)

    # Load and filter data
    explorer, df_raw = load_nhanes_cycle(nhanes_cycle_tab3)
    df_filtered = apply_nhanes_filters(df_raw, age_range_tab3, selected_genders_tab3, selected_races_tab3)

    if df_filtered.empty:
        st.warning("No data matches the selected filters.")
    elif x_metric not in df_filtered.columns or y_metric not in df_filtered.columns:
        st.error("Selected metrics not available in this cycle.")
    else:
        scatter_df = df_filtered[[x_metric, y_metric] + ([color_by] if color_by else [])].dropna()

        if scatter_df.empty:
            st.warning("No data available after removing missing values.")
        else:
            title = f"{y_metric.replace('_', ' ').title()} vs {x_metric.replace('_', ' ').title()}"

            fig = px.scatter(
                scatter_df,
                x=x_metric,
                y=y_metric,
                color=color_by,
                trendline="ols",
                template="plotly_white",
                title=title,
                opacity=0.6,
                labels={
                    x_metric: x_metric.replace("_", " ").title(),
                    y_metric: y_metric.replace("_", " ").title(),
                },
            )

            fig.update_layout(height=600)
            st.plotly_chart(fig, use_container_width=True)

            st.caption("🔗 Scatter plot with OLS trendline. Each point represents one participant.")

            # Correlation coefficient
            corr = scatter_df[x_metric].corr(scatter_df[y_metric])
            st.metric("Pearson Correlation", f"{corr:.3f}")

# ============================================================================
# TAB 4: Geographic View (BRFSS)
# ============================================================================

with tab4:
    st.header("Geographic Analysis: State-Level Health Indicators")
    st.caption("Data from CDC Behavioral Risk Factor Surveillance System (BRFSS)")

    # Load available indicators (cached)
    try:
        available_indicators = get_available_indicators()

        if not available_indicators.empty:
            # Remove duplicates and create tuples of (class, question) for selectbox
            indicator_options = list(
                set([(row["class"], row["question"]) for _, row in available_indicators.iterrows()])
            )
            # Sort for consistent ordering
            indicator_options.sort(key=lambda x: (x[0], x[1]))

            # Add format function to show class + truncated question
            brfss_indicator = st.selectbox(
                "Select Indicator",
                indicator_options,
                format_func=lambda x: f"{x[0]}: {x[1][:80]}..." if len(x[1]) > 80 else f"{x[0]}: {x[1]}",
                help="Choose state-level health indicator",
            )

            indicator_class, indicator_question = brfss_indicator

            # Show full question text below selector
            st.caption(f"📋 **Question:** {indicator_question}")

            # Get available years for this indicator by checking cached raw data
            try:
                # Fetch raw data to see all available years (cached)
                raw_data = get_brfss_raw_data()
                if not raw_data.empty:
                    # Filter for this specific indicator
                    indicator_data = raw_data[
                        (raw_data["class"] == indicator_class) & (raw_data["question"] == indicator_question)
                    ]

                    if not indicator_data.empty and "yearstart" in indicator_data.columns:
                        # Convert yearstart to int and get unique years
                        available_years = sorted(
                            pd.to_numeric(indicator_data["yearstart"], errors="coerce").dropna().astype(int).unique(),
                            reverse=False,  # Chronological order for animation
                        )

                        # Display mode selector
                        view_mode = st.radio(
                            "View Mode",
                            ["Single Year", "Animated Time Series"],
                            horizontal=True,
                            help="Single Year: Select one year. Animated: Play through all years with animation.",
                        )

                        if view_mode == "Single Year":
                            year_options = ["Latest (most recent)"] + [str(y) for y in reversed(available_years)]

                            selected_year = st.selectbox(
                                "Year",
                                year_options,
                                help=f"Available years for this indicator: {', '.join(map(str, available_years))}",
                            )

                            year_filter = None if selected_year == "Latest (most recent)" else int(selected_year)
                            use_animation = False
                        else:
                            # Animated mode - load all years
                            year_filter = None
                            use_animation = True
                    else:
                        year_filter = None
                        use_animation = False
                else:
                    year_filter = None
                    use_animation = False
            except Exception as e:
                st.warning(f"Could not load available years: {e}")
                year_filter = None
                use_animation = False
        else:
            st.error("Unable to load available indicators from BRFSS API.")
            indicator_class = None
            indicator_question = None
            year_filter = None
    except Exception as e:
        st.error(f"Error loading indicators: {e}")
        indicator_class = None
        indicator_question = None
        year_filter = None

    if indicator_class and indicator_question:
        # Load pre-filtered and normalized indicator data (cached, instant after first load)
        brfss_df = get_indicator_data(indicator_class, indicator_question)

        if not brfss_df.empty:
            # Filter to single year if not in animation mode (simple pandas filter, very fast)
            if not use_animation and year_filter is not None:
                brfss_df = brfss_df[brfss_df["year"] == year_filter]
            elif not use_animation:
                # "Latest" option - get most recent year
                latest_year = brfss_df["year"].max()
                brfss_df = brfss_df[brfss_df["year"] == latest_year]
    else:
        brfss_df = pd.DataFrame()
        use_animation = False

    if brfss_df.empty:
        st.error("Unable to load BRFSS data. Try a different indicator or year.")
    else:
        if "value" in brfss_df.columns:
            # Only show summary stats for single year view (hide for animation)
            if not use_animation:
                col1, col2, col3, col4 = st.columns(4)

                values = brfss_df["value"].dropna()
                unique_states = brfss_df["state"].nunique() if "state" in brfss_df.columns else len(brfss_df)

                with col1:
                    st.metric("States", f"{unique_states}")
                with col2:
                    st.metric("Mean Prevalence", f"{values.mean():.1f}%")
                with col3:
                    st.metric("Range", f"{values.min():.1f}% - {values.max():.1f}%")
                with col4:
                    year_display = brfss_df["year"].iloc[0] if "year" in brfss_df.columns else "Unknown"
                    st.metric("Year", year_display)

                # Show note if limited state coverage
                if unique_states < 50:
                    state_list = ", ".join(sorted(brfss_df["state_name"].unique()))
                    st.info(f"ℹ️ **Note:** Data available for {unique_states} locations: {state_list}")

                st.markdown("---")

            # Choropleth map
            if "state" in brfss_df.columns:
                if use_animation:
                    # Animated title with year range
                    year_range = f"{brfss_df['year'].min()}-{brfss_df['year'].max()}"
                    title = f"{indicator_class} ({year_range})"
                    fig = create_choropleth_map(brfss_df, "value", title, animated=True)
                    st.plotly_chart(fig, use_container_width=True)
                    st.caption("🗺️ 🎬 Use play or slider to animate year-over-year change.")
                    st.caption("Darker colors indicate higher prevalence.")
                else:
                    # Single year title
                    year_display = brfss_df["year"].iloc[0] if "year" in brfss_df.columns else "Latest"
                    title = f"{indicator_class} ({year_display})"
                    fig = create_choropleth_map(brfss_df, "value", title, animated=False)
                    st.plotly_chart(fig, use_container_width=True)
                    st.caption("🗺️ Hover over states for exact prevalence values. Darker colors indicate higher rates.")

                with st.expander("📊 View State Rankings"):
                    ranking = brfss_df[["state", "state_name", "value"]].sort_values("value", ascending=False)
                    ranking.columns = ["State Code", "State Name", "Prevalence (%)"]
                    st.dataframe(ranking.reset_index(drop=True), use_container_width=True)
            else:
                st.warning("Location data not available for choropleth map.")
        else:
            st.error("Data format unexpected. Unable to visualize.")

# Footer
st.markdown("---")
st.caption(
    "🔬 **PopHealth Observatory** | Open-source population health analytics | "
    "[GitHub](https://github.com/paulboys/PopHealth-Observatory) | "
    "[Documentation](https://paulboys.github.io/PopHealth-Observatory/)"
)
