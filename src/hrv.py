from pathlib import Path

import pandas as pd

from config import settings
from db import connect


HRV_GLOB = "samsunghealth_vikas.negi10_20260606141288/jsons/com.samsung.health.hrv/**/*.json"


def _hrv_json_glob(data_dir: Path = settings.data_dir) -> str:
    return str((data_dir / HRV_GLOB).resolve())


def refresh_hrv_tables(data_dir: Path = settings.data_dir) -> None:
    hrv_json_glob = _hrv_json_glob(data_dir)

    with connect() as conn:
        conn.execute(
            """
            CREATE OR REPLACE TABLE hrv_clean_json AS
            SELECT
                regexp_extract(
                    filename,
                    '([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})',
                    1
                ) AS datauuid,
                filename,
                timezone('UTC', to_timestamp(start_time / 1000)) AS start_time_utc,
                timezone('UTC', to_timestamp(end_time / 1000)) AS end_time_utc,
                timezone('Europe/Amsterdam', to_timestamp(start_time / 1000)) AS start_time_local,
                timezone('Europe/Amsterdam', to_timestamp(end_time / 1000)) AS end_time_local,
                sdnn,
                rmssd
            FROM read_json_auto(?, filename = true);
            """,
            [hrv_json_glob],
        )

        conn.execute(
            """
            CREATE OR REPLACE TABLE hrv_nightly_summary AS
            WITH hrv_with_night AS (
                SELECT
                    CASE
                        WHEN date_part('hour', start_time_local) < 12
                            THEN CAST(start_time_local AS DATE) - 1
                        ELSE CAST(start_time_local AS DATE)
                    END AS night_start_date,
                    sdnn,
                    rmssd,
                    start_time_utc,
                    end_time_utc
                FROM hrv_clean_json
                WHERE
                    sdnn IS NOT NULL
                    AND rmssd IS NOT NULL
                    AND start_time_utc IS NOT NULL
                    AND end_time_utc IS NOT NULL
            )

            SELECT
                CAST(night_start_date AS VARCHAR)
                    || ' : '
                    || CAST(night_start_date + 1 AS VARCHAR) AS night,
                night_start_date,
                night_start_date + 1 AS night_end_date,
                ROUND(AVG(sdnn), 2) AS avg_sdnn,
                ROUND(AVG(rmssd), 2) AS avg_rmssd,
                MIN(start_time_utc) AS first_reading_utc,
                MAX(end_time_utc) AS last_reading_utc,
                COUNT(*) AS readings
            FROM hrv_with_night
            GROUP BY night_start_date
            ORDER BY night_start_date;
            """
        )


def load_hrv_nightly_summary() -> pd.DataFrame:
    with connect() as conn:
        table_exists = conn.execute(
            """
            SELECT COUNT(*)
            FROM information_schema.tables
            WHERE table_name = 'hrv_nightly_summary';
            """
        ).fetchone()[0]

        if not table_exists:
            refresh_hrv_tables()

        return conn.execute(
            """
            SELECT
                night,
                night_start_date,
                night_end_date,
                avg_sdnn,
                avg_rmssd,
                first_reading_utc,
                last_reading_utc,
                readings
            FROM hrv_nightly_summary
            ORDER BY night_start_date;
            """
        ).fetchdf()
