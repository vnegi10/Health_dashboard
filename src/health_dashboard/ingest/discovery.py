from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from health_dashboard.config import settings


@dataclass(frozen=True)
class ExportSummary:
    csv_files: int
    json_files: int
    by_extension: pd.DataFrame


def summarize_export_files(data_dir: Path = settings.data_dir) -> ExportSummary:
    files = [path for path in data_dir.rglob("*") if path.is_file()] if data_dir.exists() else []
    rows = [
        {"extension": path.suffix.lower() or "(none)", "files": 1, "bytes": path.stat().st_size}
        for path in files
    ]

    if rows:
        by_extension = (
            pd.DataFrame(rows)
            .groupby("extension", as_index=False)
            .agg(files=("files", "sum"), bytes=("bytes", "sum"))
            .sort_values(["files", "extension"], ascending=[False, True])
        )
    else:
        by_extension = pd.DataFrame(columns=["extension", "files", "bytes"])

    counts = dict(zip(by_extension["extension"], by_extension["files"], strict=False))
    return ExportSummary(
        csv_files=int(counts.get(".csv", 0)),
        json_files=int(counts.get(".json", 0)),
        by_extension=by_extension,
    )
