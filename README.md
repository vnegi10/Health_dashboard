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

Refresh the steps DuckDB tables:

```bash
uv run python -c "from steps import refresh_steps_tables; refresh_steps_tables()"
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

### `steps_raw_csv`

Raw daily pedometer summary rows ingested from:

```text
data/samsunghealth_*/com.samsung.shealth.tracker.pedometer_day_summary.*.csv
```

This table preserves the source rows and normalizes the daily timestamp into a local date. Samsung Health exports can contain multiple source/device rows for the same day.

| Column | Type | Description |
| --- | --- | --- |
| `filename` | `VARCHAR` | Full source CSV file path. |
| `datauuid` | `VARCHAR` | Samsung Health row UUID. |
| `deviceuuid` | `VARCHAR` | Device/source identifier from the export. |
| `day_time_utc` | `TIMESTAMP WITH TIME ZONE` | Source day timestamp from Samsung Health. |
| `day` | `DATE` | Local `Europe/Amsterdam` date for the daily summary. |
| `step_count` | `BIGINT` | Step count reported by the source row. |
| `walk_step_count` | `BIGINT` | Walking step count reported by the source row. |
| `run_step_count` | `BIGINT` | Running step count reported by the source row. |
| `distance` | `DOUBLE` | Distance reported by the source row in meters. |
| `calorie` | `DOUBLE` | Calories reported by the source row. |
| `active_time` | `BIGINT` | Active time reported by Samsung Health in milliseconds. |
| `update_time` | `TIMESTAMP` | Source row update timestamp. |
| `create_time` | `TIMESTAMP` | Source row creation timestamp. |

### `steps_daily_summary`

Day-level steps aggregate used by the Steps Summary page. It groups duplicate source/device rows by day and uses the maximum step and distance values for each day to avoid double-counting multiple device rows.

| Column | Type | Description |
| --- | --- | --- |
| `day` | `DATE` | Local date. |
| `steps` | `BIGINT` | Daily step count. |
| `distance_meters` | `DOUBLE` | Daily distance in meters. |
| `distance_km` | `DOUBLE` | Daily distance in kilometers. |
| `calories` | `DOUBLE` | Daily calories. |
| `active_time_ms` | `BIGINT` | Daily active time in milliseconds. |
| `source_rows` | `BIGINT` | Number of raw source rows for the day. |
| `devices` | `BIGINT` | Number of distinct devices/source IDs for the day. |

## Project Layout

```text
dashboard/                 Streamlit app and pages
dashboard/pages/           Additional Streamlit pages
src/                       Reusable ingestion, ETL, and dashboard code
tests/                     Unit tests
data/                      Local Samsung Health export, ignored by git
warehouse/                 Generated DuckDB database, ignored by git
```
