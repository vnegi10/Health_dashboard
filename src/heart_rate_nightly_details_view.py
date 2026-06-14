import pandas as pd
import plotly.express as px
import streamlit as st

from heart_rate import load_heart_rate_nightly_summary, load_heart_rate_readings_for_night


HEATMAP_START_DATE = pd.Timestamp("2025-07-01")


@st.cache_data(show_spinner=False)
def get_heart_rate_nightly_summary():
    return load_heart_rate_nightly_summary()


@st.cache_data(show_spinner=False)
def get_heart_rate_readings_for_night(night_start_date: str):
    return load_heart_rate_readings_for_night(night_start_date)


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


def render_heart_rate_nightly_details_page() -> None:
    st.title("HR Nightly Details")
    st.caption("Calendar view with per-night heart rate variation")

    with st.spinner("Loading nightly heart rate calendar..."):
        nightly_summary = get_heart_rate_nightly_summary()

    if nightly_summary.empty:
        st.warning("No nightly heart rate rows were found in the Samsung Health JSON export.")
        return

    calendar_data = nightly_summary.copy()
    calendar_data["night_start_date"] = pd.to_datetime(calendar_data["night_start_date"])
    calendar_data = calendar_data[calendar_data["night_start_date"] >= HEATMAP_START_DATE]

    if calendar_data.empty:
        st.warning("No nightly heart rate rows were found from July 1, 2025 onward.")
        return

    calendar_data["date"] = calendar_data["night_start_date"].dt.strftime("%Y-%m-%d")
    calendar_data["week_start"] = calendar_data["night_start_date"] - pd.to_timedelta(
        calendar_data["night_start_date"].dt.weekday,
        unit="D",
    )
    calendar_data["weekday_index"] = calendar_data["night_start_date"].dt.weekday
    calendar_data["hover"] = (
        calendar_data["date"]
        + "<br>Avg HR "
        + calendar_data["avg_heart_rate"].map("{:.2f} bpm".format)
        + "<br>Range "
        + calendar_data["min_heart_rate"].map("{:.0f}".format)
        + "-"
        + calendar_data["max_heart_rate"].map("{:.0f} bpm".format)
        + "<br>Readings "
        + calendar_data["readings"].map("{:,}".format)
    )

    selected_default = st.session_state.get(
        "selected_hr_nightly_detail",
        calendar_data.iloc[-1]["date"],
    )
    if selected_default not in set(calendar_data["date"]):
        selected_default = calendar_data.iloc[-1]["date"]

    fig = px.scatter(
        calendar_data,
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
        coloraxis_colorbar={"title": "Avg HR"},
    )
    fig.update_yaxes(
        tickmode="array",
        tickvals=[0, 1, 2, 3, 4, 5, 6],
        ticktext=["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
        autorange="reversed",
    )

    selection_event = st.plotly_chart(
        fig,
        key="hr_nightly_calendar_heatmap",
        on_select="rerun",
        selection_mode="points",
        width="stretch",
    )
    selected_night = _selected_calendar_date(selection_event, selected_default)
    st.session_state.selected_hr_nightly_detail = selected_night

    selected_summary = calendar_data.loc[calendar_data["date"] == selected_night].iloc[0]

    with st.expander(f"Details for {selected_night}", expanded=True):
        readings = get_heart_rate_readings_for_night(selected_night)

        if readings.empty:
            st.warning("No detailed heart rate readings were found for this night.")
            return

        detail_data = readings.copy()
        detail_data["start_time_local"] = pd.to_datetime(detail_data["start_time_local"])
        detail_data["end_time_local"] = pd.to_datetime(detail_data["end_time_local"])

        detail_cols = st.columns(4)
        detail_cols[0].metric("Avg HR", f"{selected_summary.avg_heart_rate:.1f} bpm")
        detail_cols[1].metric(
            "Range",
            f"{selected_summary.min_heart_rate:.0f}-{selected_summary.max_heart_rate:.0f} bpm",
        )
        detail_cols[2].metric("Readings", f"{int(selected_summary.readings):,}")
        detail_cols[3].metric(
            "Window",
            f"{detail_data.start_time_local.min():%H:%M} - {detail_data.end_time_local.max():%H:%M}",
        )

        detail_fig = px.line(
            detail_data,
            x="start_time_local",
            y="heart_rate",
            labels={
                "start_time_local": "Local time",
                "heart_rate": "Heart rate (bpm)",
            },
            color_discrete_sequence=["#dc2626"],
        )
        detail_fig.update_layout(height=420, margin={"l": 8, "r": 8, "t": 24, "b": 8})
        st.plotly_chart(detail_fig, width="stretch")

        st.dataframe(
            detail_data[
                [
                    "start_time_local",
                    "end_time_local",
                    "heart_rate",
                    "heart_rate_min",
                    "heart_rate_max",
                    "datauuid",
                ]
            ],
            width="stretch",
            hide_index=True,
            column_config={
                "heart_rate": st.column_config.NumberColumn("Heart rate", format="%.1f bpm"),
                "heart_rate_min": st.column_config.NumberColumn("Min", format="%.1f bpm"),
                "heart_rate_max": st.column_config.NumberColumn("Max", format="%.1f bpm"),
            },
        )
