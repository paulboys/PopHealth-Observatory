"""Interactive NHANES exploration app using Streamlit.

SPDX-License-Identifier: MIT
"""
import streamlit as st

from pophealth_observatory.observatory import NHANESExplorer

st.set_page_config(page_title="PopHealth Observatory Explorer", layout="wide")

@st.cache_data(show_spinner=False)
def load_cycle(cycle: str):
    explorer = NHANESExplorer()
    merged = explorer.create_merged_dataset(cycle)
    return explorer, merged

st.title("PopHealth Observatory Explorer")
st.caption(
    "Explore NHANES demographics, examination, laboratory, and "
    "questionnaire-derived metrics."
)

# Sidebar controls
with st.sidebar:
    st.header("Configuration")
    cycle = st.selectbox("Survey Cycle", ['2021-2022','2017-2018','2015-2016','2013-2014','2011-2012','2009-2010'])
    metric_options = ['bmi','avg_systolic','avg_diastolic','weight_kg','height_cm','waist_cm']
    demographic_options = ['gender_label','race_ethnicity_label','education']
    metric = st.selectbox("Metric", metric_options)
    demographic = st.selectbox("Demographic", demographic_options)
    agg_func = st.selectbox("Aggregation", ['mean','median','count'])
    show_raw = st.checkbox("Show Raw Data", value=False)

explorer, df = load_cycle(cycle)
if df.empty:
    st.error("Failed to load dataset for selected cycle.")
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
            summary = grp.groupby(demographic)[metric].agg(['count','mean','median','std']).reset_index()
            if agg_func in ['mean','median']:
                plot_df = summary[[demographic, agg_func]]
                st.bar_chart(plot_df.set_index(demographic))
            elif agg_func == 'count':
                plot_df = summary[[demographic,'count']]
                st.bar_chart(plot_df.set_index(demographic))
            st.dataframe(summary, use_container_width=True)

# Laboratory & Questionnaire manifest insight
st.subheader("Component File Inventory (Quick Manifest)")
manifest = explorer.get_detailed_component_manifest(
    components=['Laboratory', 'Questionnaire'],
    file_types=['XPT'],
    year_range=('1999', '2022'),
    as_dataframe=True,
)
summary = manifest['summary_counts']
st.json(summary)

if 'dataframe' in manifest:
    lab_subset = manifest['dataframe'][manifest['dataframe']['component']=='Laboratory'].copy()
    keep_cols = ['year_normalized','data_file_name','data_file_type','data_file_size','derived_local_filename']
    lab_subset = lab_subset[keep_cols].drop_duplicates()[:50]
    st.write("Laboratory Files (sample)")
    st.dataframe(lab_subset, use_container_width=True)

if show_raw:
    st.subheader("Raw Merged Data (First 500 Rows)")
    st.dataframe(df.head(500), use_container_width=True)

st.caption(f"Schema Version: {manifest.get('schema_version')} • Generated: {manifest.get('generated_at')}")
