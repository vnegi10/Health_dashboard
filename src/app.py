import streamlit as st


def main() -> None:
    st.set_page_config(page_title="Health Dashboard", page_icon="heart", layout="wide")

    st.title("Health Dashboard")
    st.caption("Samsung Health analytics powered by DuckDB")

    st.page_link("pages/01_Raw_Export_Status.py", label="Raw Export Status")
    st.page_link("pages/02_HRV_Nightly_Summary.py", label="HRV Nightly Summary")
    st.page_link("pages/03_HRV_Nightly_Details.py", label="HRV Nightly Details")
    st.page_link("pages/04_Steps_Summary.py", label="Steps Summary")
    st.page_link("pages/05_HR_Summary.py", label="HR Summary")
    st.page_link("pages/06_HR_Nightly_Summary.py", label="HR Nightly Summary")
    st.page_link("pages/07_HR_Nightly_Details.py", label="HR Nightly Details")


if __name__ == "__main__":
    main()
