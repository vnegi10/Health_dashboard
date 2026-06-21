from datetime import datetime
from pathlib import Path

import pandas as pd

from config import settings
from db import connect
from heart_rate import refresh_heart_rate_nightly_tables, refresh_heart_rate_tables
from hrv import refresh_hrv_tables
from steps import refresh_steps_tables


def refresh_all_tables(data_dir: Path = settings.data_dir) -> None:
    refresh_hrv_tables(data_dir)
    refresh_steps_tables(data_dir)
    refresh_heart_rate_tables(data_dir)
    refresh_heart_rate_nightly_tables(data_dir)


def _latest_raw_file_modified(data_dir: Path) -> datetime | None:
    if not data_dir.exists():
        return None

    modified_times = [path.stat().st_mtime for path in data_dir.rglob("*") if path.is_file()]
    return datetime.fromtimestamp(max(modified_times)) if modified_times else None


def _table_exists(table_name: str) -> bool:
    if not settings.duckdb_path.exists():
        return False

    with connect() as conn:
        return bool(
            conn.execute(
                """
                SELECT COUNT(*)
                FROM information_schema.tables
                WHERE table_name = ?;
                """,
                [table_name],
            ).fetchone()[0]
        )


def _table_freshness(dataset: str, table_name: str, timestamp_sql: str) -> dict:
    if not _table_exists(table_name):
        return {
            "dataset": dataset,
            "table": table_name,
            "latest_timestamp": pd.NaT,
            "rows": 0,
        }

    with connect() as conn:
        row = conn.execute(
            f"""
            SELECT
                {timestamp_sql} AS latest_timestamp,
                COUNT(*) AS rows
            FROM {table_name};
            """
        ).fetchone()

    return {
        "dataset": dataset,
        "table": table_name,
        "latest_timestamp": row[0],
        "rows": row[1],
    }


def load_data_freshness(data_dir: Path = settings.data_dir) -> pd.DataFrame:
    rows = [
        {
            "dataset": "Raw export files",
            "table": "(filesystem)",
            "latest_timestamp": _latest_raw_file_modified(data_dir),
            "rows": None,
        },
        _table_freshness("HRV nightly", "hrv_nightly_summary", "MAX(last_reading_utc)"),
        _table_freshness("Steps daily", "steps_daily_summary", "MAX(day)"),
        _table_freshness("HR daily", "heart_rate_daily_summary", "MAX(last_reading_local)"),
        _table_freshness("HR nightly", "heart_rate_nightly_summary", "MAX(last_reading_utc)"),
    ]

    freshness = pd.DataFrame(rows)
    freshness["latest_timestamp"] = pd.to_datetime(freshness["latest_timestamp"])
    return freshness
