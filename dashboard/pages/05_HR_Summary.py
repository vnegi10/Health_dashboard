import sys
from pathlib import Path

import streamlit as st


sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from heart_rate_view import render_heart_rate_summary_page  # noqa: E402


st.set_page_config(page_title="HR Summary", page_icon="heart", layout="wide")
render_heart_rate_summary_page()
