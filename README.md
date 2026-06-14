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

## DuckDB Tables

The dashboard currently builds the following tables in `warehouse/health.duckdb`.

### `hrv_clean_json`

Raw HRV readings ingested from:

```text
data/samsunghealth_*/jsons/com.samsung.health.hrv/**/*.json
```

This table preserves each Samsung Health HRV reading and adds normalized timestamps.

| Column | Type | Description |
| --- | --- | --- |
| `datauuid` | `VARCHAR` | UUID extracted from the source JSON filename. |
| `filename` | `VARCHAR` | Full source JSON file path. |
| `start_time_utc` | `TIMESTAMP` | Reading start time normalized to UTC. |
| `end_time_utc` | `TIMESTAMP` | Reading end time normalized to UTC. |
| `start_time_local` | `TIMESTAMP` | Reading start time converted to `Europe/Amsterdam`. |
| `end_time_local` | `TIMESTAMP` | Reading end time converted to `Europe/Amsterdam`. |
| `sdnn` | `DOUBLE` | SDNN HRV value in milliseconds. |
| `rmssd` | `DOUBLE` | RMSSD HRV value in milliseconds. |

### `hrv_nightly_summary`

Night-level HRV aggregate used by the HRV summary and details pages. Nights are grouped by local Amsterdam time: readings before noon are assigned to the previous night.

| Column | Type | Description |
| --- | --- | --- |
| `night` | `VARCHAR` | Display label for the sleep night, such as `2026-06-05 : 2026-06-06`. |
| `night_start_date` | `DATE` | Local date on which the sleep night started. |
| `night_end_date` | `DATE` | Local date after `night_start_date`. |
| `avg_sdnn` | `DOUBLE` | Average SDNN for the night, rounded to two decimals. |
| `avg_rmssd` | `DOUBLE` | Average RMSSD for the night, rounded to two decimals. |
| `first_reading_utc` | `TIMESTAMP` | Earliest HRV reading timestamp for the night in UTC. |
| `last_reading_utc` | `TIMESTAMP` | Latest HRV reading timestamp for the night in UTC. |
| `readings` | `BIGINT` | Number of HRV readings included in the nightly aggregate. |

## Project Layout

```text
dashboard/                 Streamlit app and pages
dashboard/pages/           Additional Streamlit pages
src/                       Reusable ingestion, ETL, and dashboard code
tests/                     Unit tests
data/                      Local Samsung Health export, ignored by git
warehouse/                 Generated DuckDB database, ignored by git
```
