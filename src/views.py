from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from config import settings
from discovery import summarize_export_files
from hrv import load_hrv_nightly_summary, load_hrv_readings_for_night
from maintenance import load_data_freshness, refresh_all_tables
from steps import load_steps_daily_summary


@st.cache_data(show_spinner=False)
def get_hrv_summary():
    return load_hrv_nightly_summary()


@st.cache_data(show_spinner=False)
def get_hrv_readings_for_night(night_start_date: str):
    return load_hrv_readings_for_night(night_start_date)


@st.cache_data(show_spinner=False)
def get_steps_daily_summary():
    return load_steps_daily_summary()


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

    st.subheader("Data Freshness")
    freshness = load_data_freshness(data_dir)
    latest_timestamp = freshness["latest_timestamp"].dropna().max()
    freshness_cols = st.columns(2)
    freshness_cols[0].metric(
        "Latest data timestamp",
        "n/a" if pd.isna(latest_timestamp) else f"{latest_timestamp:%Y-%m-%d %H:%M}",
    )
    freshness_cols[1].metric(
        "Tracked datasets",
        f"{freshness['latest_timestamp'].notna().sum()} / {len(freshness)}",
    )
    st.dataframe(
        freshness,
        width="stretch",
        hide_index=True,
        column_config={
            "latest_timestamp": st.column_config.DatetimeColumn(
                "Latest timestamp",
                format="YYYY-MM-DD HH:mm",
            ),
            "rows": st.column_config.NumberColumn("Rows", format="%d"),
        },
    )

    if st.button("Refresh all", type="primary"):
        with st.spinner("Refreshing all DuckDB tables..."):
            refresh_all_tables(data_dir)
        from heart_rate_nightly_details_view import (
            get_heart_rate_nightly_summary as get_hr_detail_nightly_summary,
        )
        from heart_rate_nightly_details_view import get_heart_rate_readings_for_night
        from heart_rate_nightly_view import get_heart_rate_nightly_summary
        from heart_rate_view import (
            get_heart_rate_daily_summary,
            get_heart_rate_readings_for_day,
        )

        get_hrv_summary.clear()
        get_hrv_readings_for_night.clear()
        get_steps_daily_summary.clear()
        get_heart_rate_daily_summary.clear()
        get_heart_rate_readings_for_day.clear()
        get_heart_rate_nightly_summary.clear()
        get_hr_detail_nightly_summary.clear()
        get_heart_rate_readings_for_night.clear()
        st.rerun()


def render_hrv_summary_page() -> None:
    data_dir = Path(settings.data_dir)

    st.title("HRV Nightly Summary")
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


def _hrv_metric_baseline_plot(
    detail_data: pd.DataFrame,
    metric: str,
    label: str,
    baseline: float,
    color_above: str,
    color_below: str,
    unit: str = "ms",
) -> tuple[go.Figure, float, float]:
    above_baseline = detail_data[metric] > baseline
    below_baseline = detail_data[metric] < baseline
    above_pct = above_baseline.mean() * 100
    below_pct = below_baseline.mean() * 100

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=detail_data["start_time_local"],
            y=detail_data[metric],
            mode="lines",
            name=label,
            line={"color": "rgba(75, 85, 99, 0.45)", "width": 1.5},
            hovertemplate=f"%{{x|%H:%M}}<br>%{{y:.2f}} {unit}<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=detail_data.loc[above_baseline, "start_time_local"],
            y=detail_data.loc[above_baseline, metric],
            mode="markers",
            name=f"Above baseline ({above_pct:.1f}%)",
            marker={"color": color_above, "size": 6},
            hovertemplate=f"%{{x|%H:%M}}<br>%{{y:.2f}} {unit}<extra>Above baseline</extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=detail_data.loc[below_baseline, "start_time_local"],
            y=detail_data.loc[below_baseline, metric],
            mode="markers",
            name=f"Below baseline ({below_pct:.1f}%)",
            marker={"color": color_below, "size": 6},
            hovertemplate=f"%{{x|%H:%M}}<br>%{{y:.2f}} {unit}<extra>Below baseline</extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=[detail_data["start_time_local"].min(), detail_data["start_time_local"].max()],
            y=[baseline, baseline],
            mode="lines",
            name=f"7-night baseline: {baseline:.2f} {unit}",
            line={"color": "#facc15", "width": 3, "dash": "dot"},
            hovertemplate=f"7-night baseline: {baseline:.2f} {unit}<extra></extra>",
        )
    )
    fig.update_layout(
        height=360,
        margin={"l": 8, "r": 8, "t": 24, "b": 8},
        xaxis_title="Local time",
        yaxis_title=f"{label} ({unit})" if unit else label,
        legend_orientation="h",
        legend_yanchor="bottom",
        legend_y=1.02,
        legend_xanchor="right",
        legend_x=1,
    )

    return fig, above_pct, below_pct


def render_hrv_details_page() -> None:
    st.title("HRV Nightly Details")
    st.caption("Calendar view with per-night HRV variation")

    with st.spinner("Loading HRV calendar..."):
        hrv_summary = get_hrv_summary()

    if hrv_summary.empty:
        st.warning("No HRV readings were found in the Samsung Health export.")
        return

    calendar_data = hrv_summary.copy()
    calendar_data["night_start_date"] = pd.to_datetime(calendar_data["night_start_date"])
    calendar_data = calendar_data.sort_values("night_start_date")
    calendar_data["sdnn_7d_avg"] = calendar_data["avg_sdnn"].rolling(
        window=7,
        min_periods=1,
    ).mean()
    calendar_data["rmssd_7d_avg"] = calendar_data["avg_rmssd"].rolling(
        window=7,
        min_periods=1,
    ).mean()
    calendar_data["sdnn_rmssd_ratio"] = calendar_data["avg_sdnn"] / calendar_data["avg_rmssd"]
    calendar_data["sdnn_rmssd_ratio_7d_avg"] = calendar_data["sdnn_rmssd_ratio"].rolling(
        window=7,
        min_periods=1,
    ).mean()
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
        detail_data["sdnn_rmssd_ratio"] = detail_data["sdnn"] / detail_data["rmssd"]
        sdnn_baseline = float(selected_summary.sdnn_7d_avg)
        rmssd_baseline = float(selected_summary.rmssd_7d_avg)
        ratio_baseline = float(selected_summary.sdnn_rmssd_ratio_7d_avg)

        detail_cols = st.columns(4)
        detail_cols[0].metric("Avg RMSSD", f"{selected_summary.avg_rmssd:.1f} ms")
        detail_cols[1].metric("Avg SDNN", f"{selected_summary.avg_sdnn:.1f} ms")
        detail_cols[2].metric("Readings", f"{int(selected_summary.readings):,}")
        detail_cols[3].metric(
            "Window",
            f"{detail_data.start_time_local.min():%H:%M} - {detail_data.end_time_local.max():%H:%M}",
        )

        sdnn_fig, sdnn_above_pct, sdnn_below_pct = _hrv_metric_baseline_plot(
            detail_data=detail_data,
            metric="sdnn",
            label="SDNN",
            baseline=sdnn_baseline,
            color_above="#0f766e",
            color_below="#2563eb",
        )
        rmssd_fig, rmssd_above_pct, rmssd_below_pct = _hrv_metric_baseline_plot(
            detail_data=detail_data,
            metric="rmssd",
            label="RMSSD",
            baseline=rmssd_baseline,
            color_above="#0f766e",
            color_below="#2563eb",
        )
        ratio_fig, ratio_above_pct, ratio_below_pct = _hrv_metric_baseline_plot(
            detail_data=detail_data,
            metric="sdnn_rmssd_ratio",
            label="SDNN / RMSSD",
            baseline=ratio_baseline,
            color_above="#0f766e",
            color_below="#2563eb",
            unit="",
        )

        sdnn_cols = st.columns(3)
        sdnn_cols[0].metric("SDNN baseline", f"{sdnn_baseline:.2f} ms")
        sdnn_cols[1].metric("SDNN above", f"{sdnn_above_pct:.1f}%")
        sdnn_cols[2].metric("SDNN below", f"{sdnn_below_pct:.1f}%")
        st.plotly_chart(sdnn_fig, width="stretch")

        rmssd_cols = st.columns(3)
        rmssd_cols[0].metric("RMSSD baseline", f"{rmssd_baseline:.2f} ms")
        rmssd_cols[1].metric("RMSSD above", f"{rmssd_above_pct:.1f}%")
        rmssd_cols[2].metric("RMSSD below", f"{rmssd_below_pct:.1f}%")
        st.plotly_chart(rmssd_fig, width="stretch")

        ratio_cols = st.columns(3)
        ratio_cols[0].metric("Ratio baseline", f"{ratio_baseline:.2f}")
        ratio_cols[1].metric("Ratio above", f"{ratio_above_pct:.1f}%")
        ratio_cols[2].metric("Ratio below", f"{ratio_below_pct:.1f}%")
        st.plotly_chart(ratio_fig, width="stretch")

        with st.expander("Raw readings", expanded=False):
            st.dataframe(
                detail_data[
                    [
                        "start_time_local",
                        "end_time_local",
                        "rmssd",
                        "sdnn",
                        "sdnn_rmssd_ratio",
                        "datauuid",
                    ]
                ],
                width="stretch",
                hide_index=True,
                column_config={
                    "rmssd": st.column_config.NumberColumn("RMSSD", format="%.2f ms"),
                    "sdnn": st.column_config.NumberColumn("SDNN", format="%.2f ms"),
                    "sdnn_rmssd_ratio": st.column_config.NumberColumn(
                        "SDNN / RMSSD",
                        format="%.2f",
                    ),
                },
            )


def render_steps_summary_page() -> None:
    data_dir = Path(settings.data_dir)

    st.title("Steps Summary")
    st.caption("Daily Samsung Health step count and distance")

    if not data_dir.exists():
        st.warning(f"Data directory not found: {data_dir}")
        return

    with st.spinner("Loading steps data from DuckDB..."):
        steps_summary = get_steps_daily_summary()

    if steps_summary.empty:
        st.warning("No daily step count rows were found in the Samsung Health export.")
        return

    steps_summary = steps_summary.copy()
    steps_summary["day"] = pd.to_datetime(steps_summary["day"])

    latest = steps_summary.iloc[-1]
    metric_cols = st.columns(4)
    metric_cols[0].metric("Days", f"{len(steps_summary):,}")
    metric_cols[1].metric("Latest steps", f"{int(latest.steps):,}")
    metric_cols[2].metric("Latest distance", f"{latest.distance_km:.2f} km")
    metric_cols[3].metric("Total distance", f"{steps_summary.distance_km.sum():,.1f} km")

    min_day = steps_summary["day"].min().date()
    max_day = steps_summary["day"].max().date()
    default_start = max(min_day, max_day - pd.Timedelta(days=89))
    start_day, end_day = st.slider(
        "Date range",
        min_value=min_day,
        max_value=max_day,
        value=(default_start, max_day),
        format="YYYY-MM-DD",
    )

    range_data = steps_summary[
        (steps_summary["day"].dt.date >= start_day)
        & (steps_summary["day"].dt.date <= end_day)
    ]

    steps_fig = px.bar(
        range_data,
        x="day",
        y="steps",
        labels={"day": "Day", "steps": "Steps"},
        color_discrete_sequence=["#0f766e"],
    )
    steps_fig.update_layout(height=380, margin={"l": 8, "r": 8, "t": 24, "b": 8})
    st.plotly_chart(steps_fig, width="stretch")

    distance_fig = px.bar(
        range_data,
        x="day",
        y="distance_km",
        labels={"day": "Day", "distance_km": "Distance (km)"},
        color_discrete_sequence=["#2563eb"],
    )
    distance_fig.update_layout(height=340, margin={"l": 8, "r": 8, "t": 24, "b": 8})
    st.plotly_chart(distance_fig, width="stretch")

    st.subheader("Calendar Heatmap")
    month_options = steps_summary["day"].dt.to_period("M").astype(str).sort_values().unique()
    selected_month = st.selectbox("Month", month_options, index=len(month_options) - 1)

    month_start = pd.Period(selected_month, freq="M").to_timestamp()
    month_end = month_start + pd.offsets.MonthEnd(0)
    month_days = pd.DataFrame({"day": pd.date_range(month_start, month_end, freq="D")})
    heatmap_data = month_days.merge(steps_summary[["day", "steps"]], on="day", how="left")
    heatmap_data["steps"] = heatmap_data["steps"].fillna(0)
    heatmap_data["week_start"] = heatmap_data["day"] - pd.to_timedelta(
        heatmap_data["day"].dt.weekday,
        unit="D",
    )
    heatmap_data["weekday_index"] = heatmap_data["day"].dt.weekday
    heatmap_data["date"] = heatmap_data["day"].dt.strftime("%Y-%m-%d")
    heatmap_data["hover"] = (
        heatmap_data["date"] + "<br>Steps " + heatmap_data["steps"].map("{:,.0f}".format)
    )

    heatmap_fig = px.scatter(
        heatmap_data,
        x="week_start",
        y="weekday_index",
        color="steps",
        custom_data=["date"],
        hover_name="hover",
        color_continuous_scale="Greens",
        labels={"week_start": "Week", "weekday_index": "Day", "steps": "Steps"},
    )
    heatmap_fig.update_traces(
        marker={
            "symbol": "square",
            "size": 34,
            "line": {"width": 1, "color": "rgba(255,255,255,0.9)"},
        },
        hovertemplate="%{hovertext}<extra></extra>",
    )
    heatmap_fig.update_layout(
        height=300,
        margin={"l": 8, "r": 8, "t": 12, "b": 8},
        coloraxis_colorbar={"title": "Steps"},
    )
    heatmap_fig.update_yaxes(
        tickmode="array",
        tickvals=[0, 1, 2, 3, 4, 5, 6],
        ticktext=["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
        autorange="reversed",
    )
    st.plotly_chart(heatmap_fig, width="stretch")
