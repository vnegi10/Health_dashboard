import plotly.express as px
import streamlit as st
import pandas as pd

from heart_rate import load_heart_rate_nightly_summary


@st.cache_data(show_spinner=False)
def get_heart_rate_nightly_summary():
    return load_heart_rate_nightly_summary()


def render_heart_rate_nightly_page() -> None:
    st.title("HR Nightly Summary")
    st.caption("Nightly average heart rate from Samsung Health JSON readings")

    with st.spinner("Loading nightly heart rate data from DuckDB..."):
        nightly_summary = get_heart_rate_nightly_summary()

    if nightly_summary.empty:
        st.warning("No nightly heart rate rows were found in the Samsung Health JSON export.")
        return

    nightly_summary = nightly_summary.copy()
    nightly_summary["night_start_date"] = pd.to_datetime(nightly_summary["night_start_date"])

    latest = nightly_summary.iloc[-1]
    previous = nightly_summary.iloc[-2] if len(nightly_summary) > 1 else None

    metric_cols = st.columns(4)
    metric_cols[0].metric("Nights", f"{len(nightly_summary):,}")
    metric_cols[1].metric(
        "Latest avg HR",
        f"{latest.avg_heart_rate:.1f} bpm",
        None if previous is None else f"{latest.avg_heart_rate - previous.avg_heart_rate:.1f} bpm",
    )
    metric_cols[2].metric(
        "Latest range",
        f"{latest.min_heart_rate:.0f}-{latest.max_heart_rate:.0f} bpm",
    )
    metric_cols[3].metric("Latest readings", f"{int(latest.readings):,}")

    controls = st.columns([1, 2])
    nights_to_show = controls[0].slider(
        "Window",
        min_value=14,
        max_value=max(30, len(nightly_summary)),
        value=min(90, len(nightly_summary)),
        step=7,
        format="%d nights",
    )

    filtered = nightly_summary.tail(nights_to_show)
    fig = px.line(
        filtered,
        x="night_start_date",
        y="avg_heart_rate",
        markers=True,
        labels={
            "night_start_date": "Night starting",
            "avg_heart_rate": "Average heart rate (bpm)",
        },
        color_discrete_sequence=["#dc2626"],
    )
    fig.update_layout(height=420, margin={"l": 8, "r": 8, "t": 24, "b": 8})
    st.plotly_chart(fig, width="stretch")

    st.subheader("Nightly Summary")
    st.dataframe(
        nightly_summary.sort_values("night_start_date", ascending=False),
        width="stretch",
        hide_index=True,
        column_config={
            "avg_heart_rate": st.column_config.NumberColumn("Avg HR", format="%.2f bpm"),
            "min_heart_rate": st.column_config.NumberColumn("Min HR", format="%.1f bpm"),
            "max_heart_rate": st.column_config.NumberColumn("Max HR", format="%.1f bpm"),
            "readings": st.column_config.NumberColumn("Readings", format="%d"),
        },
    )
