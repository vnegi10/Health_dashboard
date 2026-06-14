import pandas as pd
import plotly.express as px
import streamlit as st

from heart_rate import (
    load_heart_rate_daily_summary,
    load_heart_rate_readings_for_day,
    refresh_heart_rate_tables,
)


@st.cache_data(show_spinner=False)
def get_heart_rate_daily_summary():
    return load_heart_rate_daily_summary()


@st.cache_data(show_spinner=False)
def get_heart_rate_readings_for_day(day: str):
    return load_heart_rate_readings_for_day(day)


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


def render_heart_rate_summary_page() -> None:
    st.title("HR Summary")
    st.caption("Daily average heart rate and selected-day variation")

    with st.spinner("Loading heart rate data from DuckDB..."):
        daily_summary = get_heart_rate_daily_summary()

    if daily_summary.empty:
        st.warning("No heart rate rows were found in the Samsung Health export.")
        return

    daily_summary = daily_summary.copy()
    daily_summary["day"] = pd.to_datetime(daily_summary["day"])

    latest = daily_summary.iloc[-1]
    metric_cols = st.columns(4)
    metric_cols[0].metric("Days", f"{len(daily_summary):,}")
    metric_cols[1].metric("Latest avg", f"{latest.avg_heart_rate:.1f} bpm")
    metric_cols[2].metric("Latest range", f"{latest.min_heart_rate:.0f}-{latest.max_heart_rate:.0f} bpm")
    metric_cols[3].metric("Latest readings", f"{int(latest.readings):,}")

    min_day = daily_summary["day"].min().date()
    max_day = daily_summary["day"].max().date()
    default_start = max(min_day, max_day - pd.Timedelta(days=89))
    start_day, end_day = st.slider(
        "Date range",
        min_value=min_day,
        max_value=max_day,
        value=(default_start, max_day),
        format="YYYY-MM-DD",
    )

    range_data = daily_summary[
        (daily_summary["day"].dt.date >= start_day)
        & (daily_summary["day"].dt.date <= end_day)
    ]

    summary_fig = px.line(
        range_data,
        x="day",
        y="avg_heart_rate",
        markers=True,
        labels={"day": "Day", "avg_heart_rate": "Average heart rate (bpm)"},
        color_discrete_sequence=["#dc2626"],
    )
    summary_fig.update_layout(height=380, margin={"l": 8, "r": 8, "t": 24, "b": 8})
    st.plotly_chart(summary_fig, width="stretch")

    st.subheader("Calendar Heatmap")
    month_options = daily_summary["day"].dt.to_period("M").astype(str).sort_values().unique()
    selected_month = st.selectbox("Month", month_options, index=len(month_options) - 1)

    month_start = pd.Period(selected_month, freq="M").to_timestamp()
    month_end = month_start + pd.offsets.MonthEnd(0)
    month_days = pd.DataFrame({"day": pd.date_range(month_start, month_end, freq="D")})
    heatmap_data = month_days.merge(
        daily_summary[["day", "avg_heart_rate", "readings"]],
        on="day",
        how="left",
    )
    heatmap_data["week_start"] = heatmap_data["day"] - pd.to_timedelta(
        heatmap_data["day"].dt.weekday,
        unit="D",
    )
    heatmap_data["weekday_index"] = heatmap_data["day"].dt.weekday
    heatmap_data["date"] = heatmap_data["day"].dt.strftime("%Y-%m-%d")
    heatmap_data["hover"] = (
        heatmap_data["date"]
        + "<br>Avg HR "
        + heatmap_data["avg_heart_rate"].map(lambda value: "n/a" if pd.isna(value) else f"{value:.1f} bpm")
        + "<br>Readings "
        + heatmap_data["readings"].fillna(0).map("{:,.0f}".format)
    )

    heatmap_fig = px.scatter(
        heatmap_data,
        x="week_start",
        y="weekday_index",
        color="avg_heart_rate",
        custom_data=["date"],
        hover_name="hover",
        color_continuous_scale="Reds",
        labels={
            "week_start": "Week",
            "weekday_index": "Day",
            "avg_heart_rate": "Avg HR",
        },
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
        coloraxis_colorbar={"title": "Avg HR"},
    )
    heatmap_fig.update_yaxes(
        tickmode="array",
        tickvals=[0, 1, 2, 3, 4, 5, 6],
        ticktext=["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
        autorange="reversed",
    )

    selected_default = st.session_state.get("selected_heart_rate_day", daily_summary.iloc[-1]["day"].strftime("%Y-%m-%d"))
    selection_event = st.plotly_chart(
        heatmap_fig,
        key="heart_rate_calendar_heatmap",
        on_select="rerun",
        selection_mode="points",
        width="stretch",
    )
    selected_day = _selected_calendar_date(selection_event, selected_default)
    st.session_state.selected_heart_rate_day = selected_day

    with st.expander(f"Heart rate variation for {selected_day}", expanded=True):
        readings = get_heart_rate_readings_for_day(selected_day)

        if readings.empty:
            st.warning("No detailed heart rate readings were found for this day.")
            return

        readings = readings.copy()
        readings["start_time_local"] = pd.to_datetime(readings["start_time_local"])
        readings["end_time_local"] = pd.to_datetime(readings["end_time_local"])

        day_cols = st.columns(4)
        day_cols[0].metric("Avg HR", f"{readings.heart_rate.mean():.1f} bpm")
        day_cols[1].metric("Min HR", f"{readings.heart_rate.min():.0f} bpm")
        day_cols[2].metric("Max HR", f"{readings.heart_rate.max():.0f} bpm")
        day_cols[3].metric("Readings", f"{len(readings):,}")

        variation_fig = px.line(
            readings,
            x="start_time_local",
            y="heart_rate",
            labels={
                "start_time_local": "Local time",
                "heart_rate": "Heart rate (bpm)",
            },
            color_discrete_sequence=["#dc2626"],
        )
        variation_fig.update_layout(height=420, margin={"l": 8, "r": 8, "t": 24, "b": 8})
        st.plotly_chart(variation_fig, width="stretch")

        st.dataframe(
            readings[
                [
                    "start_time_local",
                    "end_time_local",
                    "heart_rate",
                    "min_heart_rate",
                    "max_heart_rate",
                    "datauuid",
                    "deviceuuid",
                ]
            ],
            width="stretch",
            hide_index=True,
            column_config={
                "heart_rate": st.column_config.NumberColumn("Heart rate", format="%.1f bpm"),
                "min_heart_rate": st.column_config.NumberColumn("Min", format="%.1f bpm"),
                "max_heart_rate": st.column_config.NumberColumn("Max", format="%.1f bpm"),
            },
        )

    if st.button("Refresh heart rate tables"):
        refresh_heart_rate_tables()
        get_heart_rate_daily_summary.clear()
        get_heart_rate_readings_for_day.clear()
        st.rerun()
