"""
Track and report the active data source used by the system.

Possible sources:
  - SQL Server (mssql)
  - SQLite (sqlite)
  - JSON files (fallback when no DB is available)
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Literal

log = logging.getLogger("data_source")

SourceType = Literal["mssql", "sqlite", "json"]

_DATA_DIR = Path(__file__).resolve().parent


class DataSourceStatus:
    """Singleton tracking the active data source."""

    def __init__(self) -> None:
        self._source: SourceType = "json"
        self._db_url: str = ""
        self._json_dir: Path = _DATA_DIR
        self._json_counts: dict[str, int] = {}
        self._db_server: str = ""
        self._db_name: str = ""

    def set_db_connected(self, db_url: str | None, server: str = "", db_name: str = "") -> None:
        """Set the current source to a connected database or reset to JSON."""
        if not db_url:
            self._db_url = ""
            self._db_server = ""
            self._db_name = ""
            self._source = "json"
            return

        self._db_url = db_url
        self._db_server = server
        self._db_name = db_name
        if db_url.startswith("mssql"):
            self._source = "mssql"
        else:
            self._source = "sqlite"

    def set_json_only(self, counts: dict[str, int] | None = None) -> None:
        """Set the current source to JSON-only mode."""
        self._source = "json"
        self._db_url = ""
        self._db_server = ""
        self._db_name = ""
        if counts:
            self._json_counts = counts

    def update_json_counts(self, counts: dict[str, int]) -> None:
        """Update JSON record counts after synchronization."""
        self._json_counts = counts

    def current_source(self) -> SourceType:
        return self._source

    def is_db_connected(self) -> bool:
        return self._source in ("mssql", "sqlite")

    def is_json_synced(self) -> bool:
        return bool(self._json_counts)

    def report(self) -> None:
        """Log the full data-source status."""
        sep = "=" * 62
        log.info(sep)
        log.info("  TRANG THAI NGUON DU LIEU HE THONG")
        log.info(sep)

        if self._source == "mssql":
            log.info("  Nguon chinh  : SQL Server")
            log.info("  Server       : %s", self._db_server or "(khong ro)")
            log.info("  Database     : %s", self._db_name or "(khong ro)")
            log.info("  URL          : %s", self._db_url)
        elif self._source == "sqlite":
            log.info("  Nguon chinh  : SQLite")
            log.info("  File DB      : %s", self._db_url)
        else:
            log.info("  Nguon chinh  : JSON only")

        if self._json_counts:
            total = sum(self._json_counts.values())
            log.info("  JSON files   : synced - %d records / %d tables", total, len(self._json_counts))
            log.info("  Thu muc JSON : %s", self._json_dir)
            non_empty = {k: v for k, v in self._json_counts.items() if v > 0}
            if non_empty:
                log.info("  Chi tiet bang JSON")
                for name, cnt in sorted(non_empty.items()):
                    log.info("     %-30s %d records", name, cnt)
        else:
            log.info("  JSON files   : chua sync")

        log.info(sep)
        print(self._short_summary())

    def _short_summary(self) -> str:
        if self._source == "mssql":
            db_part = f"SQL Server ({self._db_server}/{self._db_name})"
        elif self._source == "sqlite":
            db_part = f"SQLite ({self._db_url})"
        else:
            db_part = "Khong co DB"

        json_part = (
            f"JSON sync ({sum(self._json_counts.values())} records)"
            if self._json_counts
            else "JSON chua sync"
        )
        return f"[DataSource] DB={db_part} | {json_part}"


data_source = DataSourceStatus()
