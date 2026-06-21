import streamlit as st


def main() -> None:
    st.set_page_config(page_title="Health Dashboard", page_icon="heart", layout="wide")

    st.title("Health Dashboard")
    st.caption("Samsung Health analytics powered by DuckDB")

    st.subheader("Tech Stack")

    stack_cols = st.columns(3)
    stack_cols[0].metric("Package manager", "uv")
    stack_cols[1].metric("Analytics engine", "DuckDB")
    stack_cols[2].metric("Dashboard UI", "Streamlit")

    st.markdown(
        """
        - **Python** powers the ingestion, ETL, and dashboard logic.
        - **uv** manages the project environment, dependencies, and commands.
        - **DuckDB** stores raw Samsung Health exports and derived analytical tables.
        - **Streamlit** provides the interactive dashboard pages.
        - **Plotly** renders the time-series charts and calendar-style heatmaps.
        - **pandas** supports lightweight dataframe transformations for the UI layer.
        """
    )

    st.subheader("Data Flow")
    st.markdown(
        """
        Samsung Health CSV and JSON exports are kept locally in `data/`, transformed into
        DuckDB tables in `warehouse/health.duckdb`, and visualized through Streamlit pages.
        """
    )


if __name__ == "__main__":
    main()
