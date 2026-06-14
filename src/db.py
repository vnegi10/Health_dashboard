from pathlib import Path

import duckdb

from config import settings


def connect(database: Path | str = settings.duckdb_path) -> duckdb.DuckDBPyConnection:
    db_path = Path(database)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return duckdb.connect(str(db_path))
