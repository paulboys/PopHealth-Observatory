"""Interactive NHANES exploration app using Streamlit.

SPDX-License-Identifier: MIT
"""

import streamlit as st

from pophealth_observatory.observatory import NHANESExplorer

st.set_page_config(page_title="PopHealth Observatory Explorer", layout="wide")


@st.cache_data(show_spinner="Loading NHANES data...")
def load_cycle(cycle: str):
    explorer = NHANESExplorer()
    merged = explorer.create_merged_dataset(cycle)
    return explorer, merged


st.title("PopHealth Observatory Explorer")
st.caption("Explore NHANES demographics, examination, laboratory, and questionnaire-derived metrics.")
st.markdown("---")

# Sidebar controls
with st.sidebar:
    st.header("Configuration")
    cycle = st.selectbox("Survey Cycle", ["2017-2018", "2015-2016", "2013-2014", "2011-2012", "2009-2010", "2021-2022"])
    metric_options = ["bmi", "avg_systolic", "avg_diastolic", "weight_kg", "height_cm", "waist_cm"]
    demographic_options = ["gender_label", "race_ethnicity_label", "education"]
    metric = st.selectbox("Metric", metric_options)
    demographic = st.selectbox("Demographic", demographic_options)
    agg_func = st.selectbox("Aggregation", ["mean", "median", "count"])
    show_raw = st.checkbox("Show Raw Data", value=False)

# Main content area - show immediate feedback
with st.spinner(f"Loading cycle {cycle}..."):
    explorer, df = load_cycle(cycle)

if df.empty:
    st.error(f"⚠️ Failed to load dataset for cycle **{cycle}**. This cycle may have limited file availability.")
    st.info("Try selecting **2017-2018** from the sidebar for complete data.")
    st.stop()

available_metrics = [m for m in [metric] if m in df.columns]
if not available_metrics:
    st.warning("Selected metric not present in dataset.")
else:
    st.subheader(f"{metric} by {demographic}")
    if demographic not in df.columns:
        st.warning("Demographic not found in dataset.")
    else:
        grp = df[[demographic, metric]].dropna()
        if grp.empty:
            st.info("No data after dropping NA values.")
        else:
            summary = grp.groupby(demographic)[metric].agg(["count", "mean", "median", "std"]).reset_index()
            if agg_func in ["mean", "median"]:
                plot_df = summary[[demographic, agg_func]]
                st.bar_chart(plot_df.set_index(demographic))
            elif agg_func == "count":
                plot_df = summary[[demographic, "count"]]
                st.bar_chart(plot_df.set_index(demographic))
            st.dataframe(summary, use_container_width=True)

# Laboratory & Questionnaire manifest insight (placeholder - feature coming soon)
st.subheader("Component File Inventory")
st.info(
    "📋 Detailed component manifest functionality is coming soon. "
    "See `notebooks/nhanes_demographics_link_finder.ipynb` for current prototype implementation."
)

if show_raw:
    st.subheader("Raw Merged Data (First 500 Rows)")
    st.dataframe(df.head(500), use_container_width=True)
