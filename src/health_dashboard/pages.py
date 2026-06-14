from pathlib import Path

import plotly.express as px
import streamlit as st

from health_dashboard.config import settings
from health_dashboard.etl import load_hrv_nightly_summary, refresh_hrv_tables
from health_dashboard.ingest.discovery import summarize_export_files


@st.cache_data(show_spinner=False)
def get_hrv_summary():
    return load_hrv_nightly_summary()


def render_raw_export_status_page() -> None:
    data_dir = Path(settings.data_dir)
    db_path = Path(settings.duckdb_path)

    st.title("Raw Export Status")
    st.caption("Samsung Health export inventory")

    if not data_dir.exists():
        st.warning(f"Data directory not found: {data_dir}")
        return

    summary = summarize_export_files(data_dir)
    status_cols = st.columns(3)
    status_cols[0].metric("CSV files", summary.csv_files)
    status_cols[1].metric("JSON files", summary.json_files)
    status_cols[2].metric("DuckDB path", str(db_path))

    st.dataframe(summary.by_extension, width="stretch", hide_index=True)


def render_hrv_summary_page() -> None:
    data_dir = Path(settings.data_dir)

    st.title("Nightly HRV")
    st.caption("Samsung Health nightly HRV analytics powered by DuckDB")

    if not data_dir.exists():
        st.warning(f"Data directory not found: {data_dir}")
        return

    with st.spinner("Loading HRV data from DuckDB..."):
        hrv_summary = get_hrv_summary()

    if hrv_summary.empty:
        st.warning("No HRV readings were found in the Samsung Health export.")
        return

    latest = hrv_summary.iloc[-1]
    previous = hrv_summary.iloc[-2] if len(hrv_summary) > 1 else None

    metric_cols = st.columns(4)
    metric_cols[0].metric("Nights", f"{len(hrv_summary):,}")
    metric_cols[1].metric(
        "Latest RMSSD",
        f"{latest.avg_rmssd:.1f} ms",
        None if previous is None else f"{latest.avg_rmssd - previous.avg_rmssd:.1f} ms",
    )
    metric_cols[2].metric(
        "Latest SDNN",
        f"{latest.avg_sdnn:.1f} ms",
        None if previous is None else f"{latest.avg_sdnn - previous.avg_sdnn:.1f} ms",
    )
    metric_cols[3].metric("Latest readings", f"{int(latest.readings):,}")

    controls = st.columns([1, 1, 2])
    days_to_show = controls[0].slider(
        "Window",
        min_value=14,
        max_value=max(30, len(hrv_summary)),
        value=min(90, len(hrv_summary)),
        step=7,
        format="%d nights",
    )
    show_points = controls[1].toggle("Show readings", value=True)

    filtered = hrv_summary.tail(days_to_show)
    chart_data = filtered.melt(
        id_vars=["night_start_date"],
        value_vars=["avg_rmssd", "avg_sdnn"],
        var_name="metric",
        value_name="milliseconds",
    )
    chart_data["metric"] = chart_data["metric"].replace(
        {"avg_rmssd": "RMSSD", "avg_sdnn": "SDNN"}
    )

    fig = px.line(
        chart_data,
        x="night_start_date",
        y="milliseconds",
        color="metric",
        markers=show_points,
        labels={
            "night_start_date": "Night starting",
            "milliseconds": "Average HRV (ms)",
            "metric": "Metric",
        },
        color_discrete_map={"RMSSD": "#0f766e", "SDNN": "#7c3aed"},
    )
    fig.update_layout(
        height=440,
        margin={"l": 8, "r": 8, "t": 24, "b": 8},
        legend_orientation="h",
        legend_yanchor="bottom",
        legend_y=1.02,
        legend_xanchor="right",
        legend_x=1,
    )
    st.plotly_chart(fig, width="stretch")

    st.subheader("Nightly Summary")
    st.dataframe(
        hrv_summary.sort_values("night_start_date", ascending=False),
        width="stretch",
        hide_index=True,
        column_config={
            "avg_sdnn": st.column_config.NumberColumn("Avg SDNN", format="%.2f ms"),
            "avg_rmssd": st.column_config.NumberColumn("Avg RMSSD", format="%.2f ms"),
            "readings": st.column_config.NumberColumn("Readings", format="%d"),
        },
    )

    if st.button("Refresh HRV tables"):
        refresh_hrv_tables(data_dir)
        get_hrv_summary.clear()
        st.rerun()
