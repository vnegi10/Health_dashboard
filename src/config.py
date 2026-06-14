from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class Settings:
    data_dir: Path = PROJECT_ROOT / "data"
    duckdb_path: Path = PROJECT_ROOT / "warehouse" / "health.duckdb"


settings = Settings()
