from health_dashboard.ingest.discovery import summarize_export_files


def main() -> None:
    summary = summarize_export_files()
    print(summary.by_extension.to_string(index=False))


if __name__ == "__main__":
    main()
