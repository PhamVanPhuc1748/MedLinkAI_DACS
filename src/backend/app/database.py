from __future__ import annotations

import json
import logging
import os
import socket
from pathlib import Path
from typing import Generator

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import Session, sessionmaker

from .models import Base

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[3]
MANUAL_DB_CONFIG_PATH = PROJECT_ROOT / "db_config.json"


def _get_data_source():
    """
    Hàm tiện ích lấy đối tượng `data_source` từ module `data_source_status`.
    Đối tượng này giúp hệ thống theo dõi trạng thái hiện tại đang kết nối với 
    SQL Server hay chỉ đang chạy tạm bằng file JSON (JSON-only mode).
    """
    try:
        import sys
        from pathlib import Path as _Path

        src_dir = _Path(__file__).resolve().parents[3]
        if str(src_dir) not in sys.path:
            sys.path.insert(0, str(src_dir))

        from data.data_source_status import data_source

        return data_source
    except Exception:
        return None


local_host = socket.gethostname()
_DEFAULT_URL = (
    f"mssql+pyodbc://{local_host}\\SQLEXPRESS/He_Thong_Du_Doan_Thuoc"
    "?driver=ODBC+Driver+17+for+SQL+Server"
    "&trusted_connection=yes"
    "&TrustServerCertificate=yes"
)
_SQLITE_FALLBACK_URL = "sqlite:///./app_local.db"


def _load_manual_db_url() -> str | None:
    """
    Đọc URL kết nối cơ sở dữ liệu từ file cấu hình thủ công `db_config.json` (nếu có).
    Cho phép người dùng thay đổi thông số kết nối (server, instance, database) 
    mà không cần sửa trực tiếp vào mã nguồn.
    """
    if not MANUAL_DB_CONFIG_PATH.exists():
        return None
    try:
        raw = json.loads(MANUAL_DB_CONFIG_PATH.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        logger.warning("Cannot parse manual DB config %s: %s", MANUAL_DB_CONFIG_PATH, exc)
        return None

    if not isinstance(raw, dict):
        return None

    db_url = str(raw.get("db_url") or "").strip()
    if db_url:
        return db_url

    db_type = str(raw.get("db_type") or "mssql").strip().lower()
    if db_type == "sqlite":
        sqlite_path = str(raw.get("sqlite_path") or "./app_local.db").strip()
        if sqlite_path.startswith("sqlite:///"):
            return sqlite_path
        return f"sqlite:///{sqlite_path}"

    server = str(raw.get("server") or local_host).strip()
    instance = str(raw.get("instance") or "SQLEXPRESS").strip()
    database = str(raw.get("database") or "He_Thong_Du_Doan_Thuoc").strip()
    driver = str(raw.get("driver") or "ODBC Driver 17 for SQL Server").strip().replace(" ", "+")
    trusted_connection = str(raw.get("trusted_connection", True)).lower()
    trust_server_certificate = str(raw.get("trust_server_certificate", True)).lower()

    server_part = f"{server}\\{instance}" if instance else server
    return (
        f"mssql+pyodbc://{server_part}/{database}"
        f"?driver={driver}"
        f"&trusted_connection={trusted_connection}"
        f"&TrustServerCertificate={trust_server_certificate}"
    )


SQLALCHEMY_DATABASE_URL: str = (
    os.getenv("MODEL_GNN_DB_URL")
    or _load_manual_db_url()
    or _DEFAULT_URL
)
_is_mssql = SQLALCHEMY_DATABASE_URL.startswith("mssql")


def _build_engine(url: str):
    """
    Khởi tạo SQLAlchemy Engine dựa trên chuỗi kết nối URL.
    - Nếu là mssql (SQL Server): tối ưu với `fast_executemany` và connection pooling.
    - Nếu là sqlite: thiết lập `check_same_thread=False` để tránh lỗi thread.
    """
    if url.startswith("mssql"):
        return create_engine(
            url,
            fast_executemany=True,
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=10,
        )
    return create_engine(url, connect_args={"check_same_thread": False})


def _try_connect(eng) -> bool:
    """
    Thử thực thi một câu lệnh đơn giản (`SELECT 1`) để kiểm tra xem 
    kết nối đến cơ sở dữ liệu có thực sự thành công hay không.
    Trả về True nếu kết nối tốt, False nếu thất bại.
    """
    try:
        with eng.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


engine = _build_engine(SQLALCHEMY_DATABASE_URL)
if not _try_connect(engine):
    if _is_mssql:
        logger.warning(
            "Cannot connect to SQL Server (%s), switching to JSON-only mode",
            SQLALCHEMY_DATABASE_URL,
        )
        print("[DB] SQL Server khong kha dung - chuyen sang che do JSON-only")
        engine = None
        _is_mssql = False
        data_source = _get_data_source()
        if data_source:
            data_source.set_db_connected(None)
else:
    data_source = _get_data_source()
    if data_source:
        data_source.set_db_connected(SQLALCHEMY_DATABASE_URL)

if engine is not None:

    @event.listens_for(engine, "connect")
    def _on_connect(dbapi_conn, connection_record) -> None:
        """
        Sự kiện (hook) tự động kích hoạt mỗi khi SQLAlchemy mở kết nối thành công.
        Hàm này sẽ query tên Server và Database hiện tại để ghi log 
        và cập nhật trạng thái kết nối lên UI.
        """
        try:
            cursor = dbapi_conn.cursor()
            cursor.execute("SELECT @@SERVERNAME, DB_NAME()")
            server, db_name = cursor.fetchone()
            cursor.close()
            logger.info("Connected to SQL Server - server: %s | database: %s", server, db_name)
            print(f"[DB] Ket noi thanh cong - server: {server} | database: {db_name}")
            data_source = _get_data_source()
            if data_source:
                data_source.set_db_connected(
                    SQLALCHEMY_DATABASE_URL,
                    server=str(server),
                    db_name=str(db_name),
                )
        except Exception:
            logger.info("Connected to database")

    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
else:
    SessionLocal = None


def migrate_add_missing_columns() -> None:
    """
    Hàm di trú (migrate) tự động: Kiểm tra nếu bảng `users` (hoặc `nguoi_dung`) 
    đã tồn tại nhưng thiếu cột `email`, thì sẽ tự động chạy lệnh ALTER TABLE để thêm cột đó.
    Giúp tránh lỗi khi cập nhật phiên bản code mới.
    """
    if not _is_mssql or engine is None:
        return
    with engine.connect() as conn:
        for table_name in ("nguoi_dung", "users"):
            try:
                conn.execute(
                    text(
                        f"IF EXISTS (SELECT 1 FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME='{table_name}')"
                        f" AND NOT EXISTS ("
                        f"   SELECT 1 FROM INFORMATION_SCHEMA.COLUMNS"
                        f"   WHERE TABLE_NAME='{table_name}' AND COLUMN_NAME='email'"
                        f") ALTER TABLE {table_name} ADD email NVARCHAR(255) NULL"
                    )
                )
                conn.commit()
            except Exception as exc:  # noqa: BLE001
                logger.warning("migrate_add_missing_columns (%s): %s", table_name, exc)


def init_db() -> None:
    """
    Hàm khởi tạo cơ sở dữ liệu chính:
    1. Tạo tất cả các bảng (nếu chưa có) dựa trên cấu trúc mô hình (models.py).
    2. Chạy migrate để sửa cấu trúc bảng nếu cần.
    3. Kích hoạt đồng bộ dữ liệu từ Database ra file JSON (backup).
    4. Bật chế độ lắng nghe thay đổi file JSON để đồng bộ ngược vào Database.
    """
    if engine is not None:
        Base.metadata.create_all(bind=engine)
        migrate_add_missing_columns()

    data_source = _get_data_source()
    if data_source:
        data_source.report()

    if engine is not None:
        _sync_json_store()
        _start_json_realtime_sync()


def _sync_json_store() -> None:
    """
    Chạy ngầm (background thread) quá trình đồng bộ toàn bộ dữ liệu 
    từ SQL Server lưu ra các file JSON tĩnh trong thư mục `src/data/`.
    Giúp ứng dụng luôn có một bản backup JSON mới nhất để fallback.
    """
    import threading as _threading

    def _run() -> None:
        try:
            import importlib
            import sys
            from pathlib import Path as _Path

            src_dir = _Path(__file__).resolve().parents[3]
            if str(src_dir) not in sys.path:
                sys.path.insert(0, str(src_dir))

            export_module = importlib.import_module("data.export_to_json")
            export_module.export_all()

            data_source = _get_data_source()
            if data_source:
                from data.json_store import store as json_store

                data_source.update_json_counts(json_store.summary())
                logger.info("[DataSource] %s", data_source._short_summary())
                print(data_source._short_summary())
        except Exception as exc:  # noqa: BLE001
            logger.warning("Cannot sync JSON store from DB: %s", exc)

    _threading.Thread(target=_run, daemon=True, name="json-sync").start()
    logger.info("[DB] Background DB -> JSON sync started")


def _start_json_realtime_sync() -> None:
    """
    Khởi động luồng giám sát (watch) các file JSON. 
    Nếu có bất kỳ thay đổi nào từ UI cập nhật thẳng vào JSON, 
    luồng này sẽ tự động parse và INSERT/UPDATE/DELETE tương ứng vào SQL Server.
    """
    try:
        import sys
        from pathlib import Path as _Path

        src_dir = _Path(__file__).resolve().parents[3]
        if str(src_dir) not in sys.path:
            sys.path.insert(0, str(src_dir))

        from data.json_store import store as json_store

        json_store.start_realtime_sync()
        logger.info("[DB] Realtime JSON -> DB sync enabled")
    except Exception as exc:  # noqa: BLE001
        logger.warning("Cannot enable realtime JSON -> DB sync: %s", exc)


def get_db() -> Generator[Session, None, None]:
    """
    Hàm Dependency Injection (tiêm phụ thuộc) dùng cho các endpoint FastAPI.
    Mỗi khi có 1 request gọi API, hàm này sẽ cấp 1 session CSDL (kết nối) mới.
    Sau khi request xử lý xong, session sẽ tự động được đóng lại (`db.close()`).
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
