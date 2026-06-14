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

Run ingestion once implemented:

```bash
uv run python -m health_dashboard.ingest
```

## Project Layout

```text
dashboard/                 Streamlit app and pages
dashboard/pages/           Additional Streamlit pages
src/health_dashboard/      Reusable ingestion, ETL, and dashboard code
src/health_dashboard/db/   DuckDB connection and database helpers
src/health_dashboard/etl/  Transformations from raw tables to marts
src/health_dashboard/ingest/ Raw CSV/JSON discovery and loading
sql/raw/                   SQL for raw/staging tables
sql/marts/                 SQL for analytics marts
tests/                     Unit tests
data/                      Local Samsung Health export, ignored by git
warehouse/                 Generated DuckDB database, ignored by git
```
