"""
src/data/data_source_status.py
──────────────────────────────────────────────────────────────────────────────
Theo dõi và in log nguồn dữ liệu hệ thống đang sử dụng:
  - SQL Server (mssql)
  - SQLite (sqlite)
  - JSON files (fallback khi không có DB)

Import và dùng ở bất kỳ đâu:
  from src.data.data_source_status import data_source
  data_source.report()          # in log trạng thái
  data_source.is_db_connected() # True nếu đang dùng DB
  data_source.current_source()  # "mssql" | "sqlite" | "json"
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Literal

log = logging.getLogger("data_source")

SourceType = Literal["mssql", "sqlite", "json"]

_DATA_DIR = Path(__file__).resolve().parent


class DataSourceStatus:
    """Singleton theo dõi nguồn dữ liệu đang hoạt động."""

    def __init__(self) -> None:
        self._source: SourceType = "json"        # mặc định ban đầu
        self._db_url: str = ""
        self._json_dir: Path = _DATA_DIR
        self._json_counts: dict[str, int] = {}
        self._db_server: str = ""
        self._db_name: str = ""

    # ── Setter gọi từ database.py ──────────────────────────────────────────
    def set_db_connected(self, db_url: str, server: str = "", db_name: str = "") -> None:
        """Gọi khi DB đã kết nối thành công."""
        self._db_url = db_url
        self._db_server = server
        self._db_name = db_name
        if db_url.startswith("mssql"):
            self._source = "mssql"
        else:
            self._source = "sqlite"

    def set_json_only(self, counts: dict[str, int] | None = None) -> None:
        """Gọi khi không có DB, chỉ dùng JSON."""
        self._source = "json"
        if counts:
            self._json_counts = counts

    def update_json_counts(self, counts: dict[str, int]) -> None:
        """Cập nhật số bản ghi trong từng file JSON (sau khi sync)."""
        self._json_counts = counts

    # ── Query ──────────────────────────────────────────────────────────────
    def current_source(self) -> SourceType:
        return self._source

    def is_db_connected(self) -> bool:
        return self._source in ("mssql", "sqlite")

    def is_json_synced(self) -> bool:
        return bool(self._json_counts)

    # ── Báo cáo log ────────────────────────────────────────────────────────
    def report(self) -> None:
        """In log đầy đủ trạng thái nguồn dữ liệu."""
        sep = "=" * 62
        log.info(sep)
        log.info("  TRẠNG THÁI NGUỒN DỮ LIỆU HỆ THỐNG")
        log.info(sep)

        if self._source == "mssql":
            log.info("  Nguồn chính  : ✅ SQL Server (đang kết nối)")
            log.info("  Server       : %s", self._db_server or "(không rõ)")
            log.info("  Database     : %s", self._db_name or "(không rõ)")
            log.info("  URL          : %s", self._db_url)
        elif self._source == "sqlite":
            log.info("  Nguồn chính  : ⚠️  SQLite (SQL Server không khả dụng)")
            log.info("  File DB      : %s", self._db_url)
        else:
            log.info("  Nguồn chính  : ❌ Không có DB — chỉ đọc từ JSON")

        # Trạng thái JSON
        if self._json_counts:
            total = sum(self._json_counts.values())
            log.info("  JSON files   : ✅ Đã sync — %d bản ghi / %d bảng",
                     total, len(self._json_counts))
            log.info("  Thư mục JSON : %s", self._json_dir)
            # In chi tiết bảng có dữ liệu
            non_empty = {k: v for k, v in self._json_counts.items() if v > 0}
            if non_empty:
                log.info("  ── Chi tiết bảng JSON ──────────────────────────────")
                for name, cnt in sorted(non_empty.items()):
                    log.info("     %-30s %d bản ghi", name, cnt)
        else:
            log.info("  JSON files   : 🔄 Chưa sync (sẽ sync sau khi DB sẵn sàng)")

        log.info(sep)
        print(self._short_summary())

    def _short_summary(self) -> str:
        """Tóm tắt 1 dòng in ra console."""
        if self._source == "mssql":
            db_part = f"SQL Server ({self._db_server}/{self._db_name})"
        elif self._source == "sqlite":
            db_part = f"SQLite ({self._db_url})"
        else:
            db_part = "Không có DB"

        json_part = (
            f"JSON sync ✅ ({sum(self._json_counts.values())} bản ghi)"
            if self._json_counts
            else "JSON chưa sync"
        )
        return f"[DataSource] DB={db_part} | {json_part}"


# ── Singleton toàn cục ────────────────────────────────────────────────────────
data_source = DataSourceStatus()
