import sys
from pathlib import Path

import streamlit as st


sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from heart_rate_nightly_details_view import render_heart_rate_nightly_details_page  # noqa: E402


st.set_page_config(page_title="HR Nightly Details", page_icon="heart", layout="wide")
render_heart_rate_nightly_details_page()
