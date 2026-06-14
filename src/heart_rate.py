from pathlib import Path

import pandas as pd

from config import settings
from db import connect


HEART_RATE_GLOB = "samsunghealth_*/com.samsung.shealth.tracker.heart_rate.*.csv"
HEART_RATE_JSON_GLOB = "samsunghealth_*/jsons/com.samsung.shealth.tracker.heart_rate/**/*.json"


def _heart_rate_csv_glob(data_dir: Path = settings.data_dir) -> str:
    return str((data_dir / HEART_RATE_GLOB).resolve())


def _heart_rate_json_glob(data_dir: Path = settings.data_dir) -> str:
    return str((data_dir / HEART_RATE_JSON_GLOB).resolve())


def refresh_heart_rate_tables(data_dir: Path = settings.data_dir) -> None:
    heart_rate_csv_glob = _heart_rate_csv_glob(data_dir)

    with connect() as conn:
        conn.execute(
            """
            CREATE OR REPLACE TABLE heart_rate_raw_csv AS
            SELECT
                filename,
                "com.samsung.health.heart_rate.datauuid" AS datauuid,
                "com.samsung.health.heart_rate.deviceuuid" AS deviceuuid,
                "com.samsung.health.heart_rate.start_time" AS start_time_local,
                "com.samsung.health.heart_rate.end_time" AS end_time_local,
                CAST("com.samsung.health.heart_rate.start_time" AS DATE) AS day,
                "com.samsung.health.heart_rate.time_offset" AS time_offset,
                "com.samsung.health.heart_rate.heart_rate" AS heart_rate,
                "com.samsung.health.heart_rate.min" AS min_heart_rate,
                "com.samsung.health.heart_rate.max" AS max_heart_rate,
                "com.samsung.health.heart_rate.heart_beat_count" AS heart_beat_count,
                tag_id,
                source,
                "com.samsung.health.heart_rate.update_time" AS update_time,
                "com.samsung.health.heart_rate.create_time" AS create_time
            FROM read_csv(
                ?,
                skip = 1,
                header = true,
                filename = true,
                ignore_errors = true,
                union_by_name = true
            )
            WHERE
                "com.samsung.health.heart_rate.start_time" IS NOT NULL
                AND "com.samsung.health.heart_rate.heart_rate" IS NOT NULL;
            """,
            [heart_rate_csv_glob],
        )

        conn.execute(
            """
            CREATE OR REPLACE TABLE heart_rate_daily_summary AS
            SELECT
                day,
                ROUND(AVG(heart_rate), 2) AS avg_heart_rate,
                MIN(heart_rate) AS min_heart_rate,
                MAX(heart_rate) AS max_heart_rate,
                COUNT(*) AS readings,
                COUNT(DISTINCT deviceuuid) AS devices,
                MIN(start_time_local) AS first_reading_local,
                MAX(end_time_local) AS last_reading_local
            FROM heart_rate_raw_csv
            WHERE day IS NOT NULL
            GROUP BY day
            ORDER BY day;
            """
        )


def refresh_heart_rate_nightly_tables(data_dir: Path = settings.data_dir) -> None:
    heart_rate_json_glob = _heart_rate_json_glob(data_dir)

    with connect() as conn:
        conn.execute(
            """
            CREATE OR REPLACE TABLE heart_rate_clean_json AS
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
                heart_rate,
                heart_rate_min,
                heart_rate_max
            FROM read_json_auto(?, filename = true)
            WHERE
                start_time IS NOT NULL
                AND end_time IS NOT NULL
                AND heart_rate IS NOT NULL;
            """,
            [heart_rate_json_glob],
        )

        conn.execute(
            """
            CREATE OR REPLACE TABLE heart_rate_nightly_summary AS
            WITH heart_rate_with_night AS (
                SELECT
                    CASE
                        WHEN date_part('hour', start_time_local) < 12
                            THEN CAST(start_time_local AS DATE) - 1
                        ELSE CAST(start_time_local AS DATE)
                    END AS night_start_date,
                    heart_rate,
                    heart_rate_min,
                    heart_rate_max,
                    start_time_utc,
                    end_time_utc
                FROM heart_rate_clean_json
                WHERE
                    heart_rate IS NOT NULL
                    AND start_time_utc IS NOT NULL
                    AND end_time_utc IS NOT NULL
            )

            SELECT
                CAST(night_start_date AS VARCHAR)
                    || ' : '
                    || CAST(night_start_date + 1 AS VARCHAR) AS night,
                night_start_date,
                night_start_date + 1 AS night_end_date,
                ROUND(AVG(heart_rate), 2) AS avg_heart_rate,
                MIN(heart_rate_min) AS min_heart_rate,
                MAX(heart_rate_max) AS max_heart_rate,
                MIN(start_time_utc) AS first_reading_utc,
                MAX(end_time_utc) AS last_reading_utc,
                COUNT(*) AS readings
            FROM heart_rate_with_night
            GROUP BY night_start_date
            ORDER BY night_start_date;
            """
        )


def load_heart_rate_nightly_summary() -> pd.DataFrame:
    with connect() as conn:
        table_exists = conn.execute(
            """
            SELECT COUNT(*)
            FROM information_schema.tables
            WHERE table_name = 'heart_rate_nightly_summary';
            """
        ).fetchone()[0]

        if not table_exists:
            refresh_heart_rate_nightly_tables()

        return conn.execute(
            """
            SELECT
                night,
                night_start_date,
                night_end_date,
                avg_heart_rate,
                min_heart_rate,
                max_heart_rate,
                first_reading_utc,
                last_reading_utc,
                readings
            FROM heart_rate_nightly_summary
            ORDER BY night_start_date;
            """
        ).fetchdf()


def load_heart_rate_readings_for_night(night_start_date: str) -> pd.DataFrame:
    with connect() as conn:
        table_exists = conn.execute(
            """
            SELECT COUNT(*)
            FROM information_schema.tables
            WHERE table_name = 'heart_rate_clean_json';
            """
        ).fetchone()[0]

        if not table_exists:
            refresh_heart_rate_nightly_tables()

        return conn.execute(
            """
            WITH heart_rate_with_night AS (
                SELECT
                    CASE
                        WHEN date_part('hour', start_time_local) < 12
                            THEN CAST(start_time_local AS DATE) - 1
                        ELSE CAST(start_time_local AS DATE)
                    END AS night_start_date,
                    start_time_utc,
                    end_time_utc,
                    start_time_local,
                    end_time_local,
                    heart_rate,
                    heart_rate_min,
                    heart_rate_max,
                    datauuid,
                    filename
                FROM heart_rate_clean_json
                WHERE
                    heart_rate IS NOT NULL
                    AND start_time_local IS NOT NULL
                    AND end_time_local IS NOT NULL
            )
            SELECT
                night_start_date,
                start_time_utc,
                end_time_utc,
                start_time_local,
                end_time_local,
                heart_rate,
                heart_rate_min,
                heart_rate_max,
                datauuid,
                filename
            FROM heart_rate_with_night
            WHERE night_start_date = CAST(? AS DATE)
            ORDER BY start_time_local;
            """,
            [night_start_date],
        ).fetchdf()


def load_heart_rate_daily_summary() -> pd.DataFrame:
    with connect() as conn:
        table_exists = conn.execute(
            """
            SELECT COUNT(*)
            FROM information_schema.tables
            WHERE table_name = 'heart_rate_daily_summary';
            """
        ).fetchone()[0]

        if not table_exists:
            refresh_heart_rate_tables()

        return conn.execute(
            """
            SELECT
                day,
                avg_heart_rate,
                min_heart_rate,
                max_heart_rate,
                readings,
                devices,
                first_reading_local,
                last_reading_local
            FROM heart_rate_daily_summary
            ORDER BY day;
            """
        ).fetchdf()


def load_heart_rate_readings_for_day(day: str) -> pd.DataFrame:
    with connect() as conn:
        table_exists = conn.execute(
            """
            SELECT COUNT(*)
            FROM information_schema.tables
            WHERE table_name = 'heart_rate_raw_csv';
            """
        ).fetchone()[0]

        if not table_exists:
            refresh_heart_rate_tables()

        return conn.execute(
            """
            SELECT
                day,
                start_time_local,
                end_time_local,
                heart_rate,
                min_heart_rate,
                max_heart_rate,
                heart_beat_count,
                datauuid,
                deviceuuid,
                time_offset
            FROM heart_rate_raw_csv
            WHERE day = CAST(? AS DATE)
            ORDER BY start_time_local;
            """,
            [day],
        ).fetchdf()
