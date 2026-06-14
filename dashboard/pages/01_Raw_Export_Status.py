import sys
from pathlib import Path

import streamlit as st


sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from health_dashboard.pages import render_raw_export_status_page  # noqa: E402


st.set_page_config(page_title="Raw Export Status", page_icon="heart", layout="wide")
render_raw_export_status_page()
