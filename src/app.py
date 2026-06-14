import streamlit as st


def main() -> None:
    st.set_page_config(page_title="Health Dashboard", page_icon="heart", layout="wide")

    st.title("Health Dashboard")
    st.caption("Samsung Health analytics powered by DuckDB")

    st.page_link("pages/01_Raw_Export_Status.py", label="Raw Export Status")
    st.page_link("pages/02_HRV_Summary.py", label="HRV Summary")
    st.page_link("pages/03_HRV_Details.py", label="HRV Details")
    st.page_link("pages/04_Steps_Summary.py", label="Steps Summary")


if __name__ == "__main__":
    main()
