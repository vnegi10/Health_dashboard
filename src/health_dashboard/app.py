from pathlib import Path

import streamlit as st

from health_dashboard.config import settings
from health_dashboard.ingest.discovery import summarize_export_files


def main() -> None:
    st.set_page_config(page_title="Health Dashboard", page_icon="heart", layout="wide")

    st.title("Health Dashboard")
    st.caption("Samsung Health export analytics powered by DuckDB")

    data_dir = Path(settings.data_dir)
    db_path = Path(settings.duckdb_path)

    metric_cols = st.columns(3)
    summary = summarize_export_files(data_dir)

    metric_cols[0].metric("CSV files", summary.csv_files)
    metric_cols[1].metric("JSON files", summary.json_files)
    metric_cols[2].metric("DuckDB path", str(db_path))

    st.subheader("Raw export status")
    if not data_dir.exists():
        st.warning(f"Data directory not found: {data_dir}")
        return

    st.write(f"Using raw data from `{data_dir}`.")
    st.dataframe(summary.by_extension, use_container_width=True, hide_index=True)


if __name__ == "__main__":
    main()
