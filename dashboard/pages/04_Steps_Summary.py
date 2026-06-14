import sys
from pathlib import Path

import streamlit as st


sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from views import render_steps_summary_page  # noqa: E402


st.set_page_config(page_title="Steps Summary", page_icon="heart", layout="wide")
render_steps_summary_page()
