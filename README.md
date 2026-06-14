# Health Dashboard

Personal dashboard for Samsung Health exports using:

- `uv` for Python package management
- DuckDB for raw ingestion and ETL
- Streamlit for the frontend dashboard

## Setup

Install dependencies:

```bash
uv sync
```

Run the dashboard:

```bash
uv run streamlit run dashboard/Home.py
```

Refresh the HRV DuckDB tables:

```bash
uv run python -c "from hrv import refresh_hrv_tables; refresh_hrv_tables()"
```

The dashboard currently builds these DuckDB tables:

- `hrv_clean_json`: raw HRV readings from `data/samsunghealth_vikas.negi10_20260606141288/jsons/com.samsung.health.hrv/**/*.json`
- `hrv_nightly_summary`: nightly average SDNN/RMSSD grouped by local Amsterdam sleep night

## Project Layout

```text
dashboard/                 Streamlit app and pages
dashboard/pages/           Additional Streamlit pages
src/                       Reusable ingestion, ETL, and dashboard code
tests/                     Unit tests
data/                      Local Samsung Health export, ignored by git
warehouse/                 Generated DuckDB database, ignored by git
```
