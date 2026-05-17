from __future__ import annotations

import logging
import os
import socket
from typing import Generator

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import Session, sessionmaker

from .models import Base

logger = logging.getLogger(__name__)

# Import trạng thái nguồn dữ liệu (lazy để tránh circular)
def _get_data_source():
    try:
        import sys
        from pathlib import Path as _Path
        _src = _Path(__file__).resolve().parents[3]
        if str(_src) not in sys.path:
            sys.path.insert(0, str(_src))
        from data.data_source_status import data_source
        return data_source
    except Exception:
        return None

# ── SQL Server (Windows Auth) ────────────────────────────────────────────────
# Có thể override qua biến môi trường MODEL_GNN_DB_URL
_LOCAL_HOST = socket.gethostname()
_DEFAULT_URL = (
    f"mssql+pyodbc://{_LOCAL_HOST}\\SQLEXPRESS/He_Thong_Du_Doan_Thuoc"
    "?driver=ODBC+Driver+17+for+SQL+Server"
    "&trusted_connection=yes"
    "&TrustServerCertificate=yes"
)
_SQLITE_FALLBACK_URL = "sqlite:///./app_local.db"

SQLALCHEMY_DATABASE_URL: str = os.getenv("MODEL_GNN_DB_URL", _DEFAULT_URL)

_is_mssql = SQLALCHEMY_DATABASE_URL.startswith("mssql")


def _build_engine(url: str):
    if url.startswith("mssql"):
        return create_engine(
            url,
            fast_executemany=True,
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=10,
        )
    # SQLite
    return create_engine(url, connect_args={"check_same_thread": False})


def _try_connect(eng) -> bool:
    try:
        with eng.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


# Thử kết nối SQL Server; nếu thất bại tự chuyển sang chế độ JSON-only
engine = _build_engine(SQLALCHEMY_DATABASE_URL)
if not _try_connect(engine):
    if _is_mssql:
        logger.warning(
            "⚠️ Không thể kết nối SQL Server (%s), chuyển sang chế độ JSON-only",
            SQLALCHEMY_DATABASE_URL
        )
        print("[DB] ⚠️ SQL Server không khả dụng — chuyển sang chế độ JSON-only (File-based)")
        engine = None
        _is_mssql = False
        ds = _get_data_source()
        if ds:
            ds.set_db_connected(None)
else:
    ds = _get_data_source()
    if ds:
        ds.set_db_connected(SQLALCHEMY_DATABASE_URL)

if engine is not None:
    @event.listens_for(engine, "connect")
    def _on_connect(dbapi_conn, connection_record) -> None:
        try:
            cursor = dbapi_conn.cursor()
            cursor.execute("SELECT @@SERVERNAME, DB_NAME()")
            server, db = cursor.fetchone()
            cursor.close()
            logger.info("✅ Kết nối SQL Server thành công — server: %s | database: %s", server, db)
            print(f"[DB] ✅ Kết nối thành công — server: {server} | database: {db}")
            ds = _get_data_source()
            if ds:
                ds.set_db_connected(SQLALCHEMY_DATABASE_URL, server=str(server), db_name=str(db))
        except Exception:
            logger.info("✅ Kết nối database thành công")

    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
else:
    SessionLocal = None


def migrate_add_missing_columns() -> None:
    """Add any columns that are in the ORM model but not yet in the DB table."""
    if not _is_mssql or engine is None:
        return  # SQLite / JSON-only: skip SQL Server–specific DDL
    with engine.connect() as conn:
        # nguoi_dung.email — hỗ trợ cả tên cũ (users) và tên mới (nguoi_dung)
        for tbl in ("nguoi_dung", "users"):
            try:
                conn.execute(text(
                    f"IF EXISTS (SELECT 1 FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME='{tbl}')"
                    f" AND NOT EXISTS ("
                    f"   SELECT 1 FROM INFORMATION_SCHEMA.COLUMNS"
                    f"   WHERE TABLE_NAME='{tbl}' AND COLUMN_NAME='email'"
                    f") ALTER TABLE {tbl} ADD email NVARCHAR(255) NULL"
                ))
                conn.commit()
            except Exception as exc:  # noqa: BLE001
                logger.warning("migrate_add_missing_columns (%s): %s", tbl, exc)


def init_db() -> None:
    """Tạo toàn bộ bảng nếu chưa tồn tại, sau đó chạy migration cột mới."""
    if engine is not None:
        Base.metadata.create_all(bind=engine)
        migrate_add_missing_columns()
    # In log trạng thái nguồn dữ liệu trước khi sync
    ds = _get_data_source()
    if ds:
        ds.report()
    if engine is not None:
        _sync_json_store()


def _sync_json_store() -> None:
    """Xuất toàn bộ dữ liệu DB sang các file JSON trong src/data/ (chạy nền)."""
    import threading as _threading

    def _run() -> None:
        try:
            import importlib
            import sys
            from pathlib import Path as _Path

            # Đảm bảo src/ có trong sys.path
            _src = _Path(__file__).resolve().parents[3]   # …/src
            if str(_src) not in sys.path:
                sys.path.insert(0, str(_src))

            _export = importlib.import_module("data.export_to_json")
            _export.export_all()

            # Cập nhật số bản ghi vào data_source sau khi sync xong
            _ds = _get_data_source()
            if _ds:
                from data.json_store import store as _store
                _ds.update_json_counts(_store.summary())
                logger.info("[DataSource] Nguồn dữ liệu sau sync: %s", _ds._short_summary())
                print(_ds._short_summary())
        except Exception as _exc:   # noqa: BLE001
            logger.warning("⚠️ Không thể sync JSON store: %s", _exc)

    _threading.Thread(target=_run, daemon=True, name="json-sync").start()
    logger.info("[DB] JSON sync bắt đầu chạy nền…")


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
