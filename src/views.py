from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from config import settings
from discovery import summarize_export_files
from hrv import load_hrv_nightly_summary, load_hrv_readings_for_night, refresh_hrv_tables


@st.cache_data(show_spinner=False)
def get_hrv_summary():
    return load_hrv_nightly_summary()


@st.cache_data(show_spinner=False)
def get_hrv_readings_for_night(night_start_date: str):
    return load_hrv_readings_for_night(night_start_date)


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
        get_hrv_readings_for_night.clear()
        st.rerun()


def _selected_calendar_date(selection_event, fallback: str) -> str:
    if not selection_event:
        return fallback

    if hasattr(selection_event, "selection"):
        points = selection_event.selection.points
    else:
        points = selection_event.get("selection", {}).get("points", [])

    if not points:
        return fallback

    first_point = points[0]
    customdata = (
        first_point.get("customdata", [])
        if hasattr(first_point, "get")
        else getattr(first_point, "customdata", [])
    )
    return customdata[0] if customdata else fallback


def render_hrv_details_page() -> None:
    st.title("HRV Details")
    st.caption("Calendar view with per-night HRV variation")

    with st.spinner("Loading HRV calendar..."):
        hrv_summary = get_hrv_summary()

    if hrv_summary.empty:
        st.warning("No HRV readings were found in the Samsung Health export.")
        return

    calendar_data = hrv_summary.copy()
    calendar_data["night_start_date"] = pd.to_datetime(calendar_data["night_start_date"])
    calendar_data["date"] = calendar_data["night_start_date"].dt.strftime("%Y-%m-%d")
    calendar_data["week_start"] = calendar_data["night_start_date"] - pd.to_timedelta(
        calendar_data["night_start_date"].dt.weekday,
        unit="D",
    )
    calendar_data["weekday_index"] = calendar_data["night_start_date"].dt.weekday
    calendar_data["hover"] = (
        calendar_data["date"]
        + "<br>RMSSD "
        + calendar_data["avg_rmssd"].map("{:.2f} ms".format)
        + "<br>SDNN "
        + calendar_data["avg_sdnn"].map("{:.2f} ms".format)
        + "<br>Readings "
        + calendar_data["readings"].map("{:,}".format)
    )

    selected_default = st.session_state.get("selected_hrv_night", calendar_data.iloc[-1]["date"])

    fig = px.scatter(
        calendar_data,
        x="week_start",
        y="weekday_index",
        color="avg_rmssd",
        custom_data=["date"],
        hover_name="hover",
        color_continuous_scale="Teal",
        labels={
            "week_start": "Week",
            "weekday_index": "Day",
            "avg_rmssd": "Avg RMSSD",
        },
    )
    fig.update_traces(
        marker={
            "symbol": "square",
            "size": 28,
            "line": {"width": 1, "color": "rgba(255,255,255,0.85)"},
        },
        hovertemplate="%{hovertext}<extra></extra>",
    )
    fig.update_layout(
        height=300,
        margin={"l": 8, "r": 8, "t": 12, "b": 8},
        coloraxis_colorbar={"title": "RMSSD"},
    )
    fig.update_yaxes(
        tickmode="array",
        tickvals=[0, 1, 2, 3, 4, 5, 6],
        ticktext=["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
        autorange="reversed",
    )

    selection_event = st.plotly_chart(
        fig,
        key="hrv_calendar_heatmap",
        on_select="rerun",
        selection_mode="points",
        width="stretch",
    )
    selected_night = _selected_calendar_date(selection_event, selected_default)
    st.session_state.selected_hrv_night = selected_night

    selected_summary = calendar_data.loc[calendar_data["date"] == selected_night].iloc[0]

    with st.expander(f"Details for {selected_night}", expanded=True):
        readings = get_hrv_readings_for_night(selected_night)

        if readings.empty:
            st.warning("No detailed readings were found for this night.")
            return

        detail_data = readings.copy()
        detail_data["start_time_local"] = pd.to_datetime(detail_data["start_time_local"])
        detail_data["end_time_local"] = pd.to_datetime(detail_data["end_time_local"])

        detail_cols = st.columns(4)
        detail_cols[0].metric("Avg RMSSD", f"{selected_summary.avg_rmssd:.1f} ms")
        detail_cols[1].metric("Avg SDNN", f"{selected_summary.avg_sdnn:.1f} ms")
        detail_cols[2].metric("Readings", f"{int(selected_summary.readings):,}")
        detail_cols[3].metric(
            "Window",
            f"{detail_data.start_time_local.min():%H:%M} - {detail_data.end_time_local.max():%H:%M}",
        )

        chart_data = detail_data.melt(
            id_vars=["start_time_local"],
            value_vars=["rmssd", "sdnn"],
            var_name="metric",
            value_name="milliseconds",
        )
        chart_data["metric"] = chart_data["metric"].replace({"rmssd": "RMSSD", "sdnn": "SDNN"})

        detail_fig = px.line(
            chart_data,
            x="start_time_local",
            y="milliseconds",
            color="metric",
            labels={
                "start_time_local": "Local time",
                "milliseconds": "HRV (ms)",
                "metric": "Metric",
            },
            color_discrete_map={"RMSSD": "#0f766e", "SDNN": "#7c3aed"},
        )
        detail_fig.update_layout(height=420, margin={"l": 8, "r": 8, "t": 24, "b": 8})
        st.plotly_chart(detail_fig, width="stretch")

        st.dataframe(
            detail_data[
                [
                    "start_time_local",
                    "end_time_local",
                    "rmssd",
                    "sdnn",
                    "datauuid",
                ]
            ],
            width="stretch",
            hide_index=True,
            column_config={
                "rmssd": st.column_config.NumberColumn("RMSSD", format="%.2f ms"),
                "sdnn": st.column_config.NumberColumn("SDNN", format="%.2f ms"),
            },
        )
