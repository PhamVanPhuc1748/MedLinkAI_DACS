"""
Kiểm tra kết nối database và tự động kết nối nếu chưa có.

  python check_db.py                    # kiểm tra SQL Server mặc định (tên máy hiện tại)
  python check_db.py --host MYPC        # chỉ định tên máy SQL Server
  python check_db.py --url "mssql+..."  # chỉ định URL đầy đủ
  python check_db.py --retry 5          # thử lại tối đa 5 lần
"""
from __future__ import annotations

import argparse
import logging
import os
import socket
import sys
import time

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("check_db")

# ── Cấu hình mặc định ────────────────────────────────────────────────────────
_LOCAL_HOST       = socket.gethostname()
_DB_NAME          = "He_Thong_Du_Doan_Thuoc"
_SQLEXPRESS_URL   = (
    f"mssql+pyodbc://{_LOCAL_HOST}\\SQLEXPRESS/{_DB_NAME}"
    "?driver=ODBC+Driver+17+for+SQL+Server"
    "&trusted_connection=yes"
    "&TrustServerCertificate=yes"
)
_SQLITE_FALLBACK  = "sqlite:///./app_local.db"


# ── Helpers ──────────────────────────────────────────────────────────────────
def _build_engine(url: str):
    try:
        from sqlalchemy import create_engine
    except ImportError:
        log.error("SQLAlchemy chưa được cài đặt. Chạy: pip install sqlalchemy")
        sys.exit(1)

    if url.startswith("mssql"):
        return create_engine(
            url,
            fast_executemany=True,
            pool_pre_ping=True,
            pool_size=1,
            max_overflow=0,
        )
    return create_engine(url, connect_args={"check_same_thread": False})


def _ping(engine) -> tuple[bool, str]:
    """Trả về (ok, message)."""
    from sqlalchemy import text
    try:
        with engine.connect() as conn:
            if engine.dialect.name == "mssql":
                row = conn.execute(text("SELECT @@SERVERNAME, DB_NAME(), @@VERSION")).fetchone()
                server, db, ver = row
                short_ver = ver.splitlines()[0] if ver else "?"
                return True, f"server={server} | database={db} | {short_ver}"
            else:
                conn.execute(text("SELECT 1"))
                return True, f"SQLite OK ({engine.url})"
    except Exception as exc:  # noqa: BLE001
        return False, str(exc)


def check_and_connect(
    primary_url: str,
    fallback_url: str = _SQLITE_FALLBACK,
    max_retries: int = 3,
    retry_delay: float = 2.0,
) -> tuple[str, str]:
    """
    Thử kết nối primary_url (SQL Server).
    Nếu thất bại sau max_retries lần → chuyển sang fallback_url (SQLite).
    Trả về (url_đã_dùng, loại_db).
    """
    log.info("=" * 60)
    log.info("Máy chủ hiện tại : %s", _LOCAL_HOST)
    log.info("URL kết nối chính: %s", primary_url)
    log.info("=" * 60)

    # ── Thử kết nối SQL Server ───────────────────────────────────────
    for attempt in range(1, max_retries + 1):
        log.info("[%d/%d] Đang thử kết nối SQL Server…", attempt, max_retries)
        engine = _build_engine(primary_url)
        ok, msg = _ping(engine)
        if ok:
            log.info("✅ Kết nối SQL Server THÀNH CÔNG")
            log.info("   %s", msg)
            log.info("=" * 60)
            engine.dispose()
            return primary_url, "mssql"
        else:
            log.warning("❌ Lần %d thất bại: %s", attempt, msg)
            engine.dispose()
            if attempt < max_retries:
                log.info("   Thử lại sau %.1f giây…", retry_delay)
                time.sleep(retry_delay)

    # ── Fallback SQLite ──────────────────────────────────────────────
    log.warning("⚠️  SQL Server không khả dụng sau %d lần thử.", max_retries)
    log.info("→  Chuyển sang SQLite: %s", fallback_url)
    engine = _build_engine(fallback_url)
    ok, msg = _ping(engine)
    if ok:
        log.info("✅ Kết nối SQLite THÀNH CÔNG")
        log.info("   %s", msg)
    else:
        log.error("❌ Cả SQL Server lẫn SQLite đều thất bại: %s", msg)
        sys.exit(1)
    log.info("=" * 60)
    engine.dispose()
    return fallback_url, "sqlite"


# ── CLI ──────────────────────────────────────────────────────────────────────
def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Kiểm tra và tự động kết nối database")
    p.add_argument(
        "--host", default=_LOCAL_HOST,
        help=f"Tên máy SQL Server (mặc định: {_LOCAL_HOST})",
    )
    p.add_argument(
        "--db", default=_DB_NAME,
        help=f"Tên database (mặc định: {_DB_NAME})",
    )
    p.add_argument(
        "--url", default=None,
        help="Override URL kết nối hoàn chỉnh (bỏ qua --host và --db)",
    )
    p.add_argument(
        "--retry", type=int, default=3,
        help="Số lần thử lại SQL Server trước khi chuyển SQLite (mặc định: 3)",
    )
    p.add_argument(
        "--delay", type=float, default=2.0,
        help="Giây chờ giữa các lần thử (mặc định: 2.0)",
    )
    p.add_argument(
        "--no-fallback", action="store_true",
        help="Không dùng SQLite fallback — thoát luôn nếu SQL Server thất bại",
    )
    return p.parse_args()


if __name__ == "__main__":
    args = _parse_args()

    # Xây URL từ args nếu không override
    if args.url:
        primary = args.url
    else:
        primary = (
            f"mssql+pyodbc://{args.host}\\SQLEXPRESS/{args.db}"
            "?driver=ODBC+Driver+17+for+SQL+Server"
            "&trusted_connection=yes"
            "&TrustServerCertificate=yes"
        )

    fallback = _SQLITE_FALLBACK if not args.no_fallback else None

    if fallback:
        used_url, db_type = check_and_connect(primary, fallback, args.retry, args.delay)
    else:
        # Không fallback: chỉ thử SQL Server, thoát nếu thất bại
        used_url, db_type = check_and_connect(primary, primary, args.retry, args.delay)

    # Ghi kết quả ra biến môi trường (hữu ích khi gọi từ script khác)
    log.info("Kết quả: db_type=%s | url=%s", db_type, used_url)
    log.info("Gợi ý: set MODEL_GNN_DB_URL=%s", used_url)
