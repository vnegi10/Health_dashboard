from pathlib import Path

import pandas as pd

from config import settings
from db import connect


STEPS_GLOB = "samsunghealth_*/com.samsung.shealth.tracker.pedometer_day_summary.*.csv"


def _steps_csv_glob(data_dir: Path = settings.data_dir) -> str:
    return str((data_dir / STEPS_GLOB).resolve())


def refresh_steps_tables(data_dir: Path = settings.data_dir) -> None:
    steps_csv_glob = _steps_csv_glob(data_dir)

    with connect() as conn:
        conn.execute(
            """
            CREATE OR REPLACE TABLE steps_raw_csv AS
            SELECT
                filename,
                datauuid,
                deviceuuid,
                to_timestamp(day_time / 1000) AS day_time_utc,
                timezone('Europe/Amsterdam', to_timestamp(day_time / 1000))::DATE AS day,
                step_count,
                walk_step_count,
                run_step_count,
                distance,
                calorie,
                active_time,
                update_time,
                create_time
            FROM read_csv(
                ?,
                skip = 1,
                header = true,
                filename = true,
                ignore_errors = true,
                union_by_name = true
            )
            WHERE day_time IS NOT NULL;
            """,
            [steps_csv_glob],
        )

        conn.execute(
            """
            CREATE OR REPLACE TABLE steps_daily_summary AS
            SELECT
                day,
                MAX(step_count)::BIGINT AS steps,
                MAX(distance) AS distance_meters,
                MAX(distance) / 1000 AS distance_km,
                MAX(calorie) AS calories,
                MAX(active_time) AS active_time_ms,
                COUNT(*) AS source_rows,
                COUNT(DISTINCT deviceuuid) AS devices
            FROM steps_raw_csv
            WHERE day IS NOT NULL
            GROUP BY day
            ORDER BY day;
            """
        )


def load_steps_daily_summary() -> pd.DataFrame:
    with connect() as conn:
        table_exists = conn.execute(
            """
            SELECT COUNT(*)
            FROM information_schema.tables
            WHERE table_name = 'steps_daily_summary';
            """
        ).fetchone()[0]

        if not table_exists:
            refresh_steps_tables()

        return conn.execute(
            """
            SELECT
                day,
                steps,
                distance_meters,
                distance_km,
                calories,
                active_time_ms,
                source_rows,
                devices
            FROM steps_daily_summary
            ORDER BY day;
            """
        ).fetchdf()
