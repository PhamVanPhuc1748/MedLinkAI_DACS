"""
setup_database.py
=================
Script tự động:
  1. Bật dịch vụ SQL Server (MSSQLSERVER hoặc MSSQL$SQLEXPRESS) nếu chưa chạy
  2. Kết nối vào SQL Server bằng Windows Authentication
  3. Tạo database 'He_Thong_Du_Doan_Thuoc' nếu chưa tồn tại
  4. Tạo toàn bộ bảng theo ORM models.py
  5. Tạo tài khoản admin và user mặc định

Chạy: python setup_database.py
Yêu cầu: SQL Server Express + ODBC Driver 17 for SQL Server
         Chạy với quyền Administrator để bật service
"""

from __future__ import annotations

import hashlib
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

# ── Fix encoding cho Windows console (tránh UnicodeEncodeError cp1252) ────────
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# ── Thêm src vào path ─────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent
SRC  = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

# ── Màu terminal ──────────────────────────────────────────────────────────────
class C:
    OK    = "\033[92m"  # xanh lá
    WARN  = "\033[93m"  # vàng
    ERR   = "\033[91m"  # đỏ
    INFO  = "\033[96m"  # cyan
    BOLD  = "\033[1m"
    RESET = "\033[0m"

def ok(msg):   print(f"{C.OK}  ✔  {msg}{C.RESET}")
def warn(msg): print(f"{C.WARN}  ⚠  {msg}{C.RESET}")
def err(msg):  print(f"{C.ERR}  ✘  {msg}{C.RESET}")
def info(msg): print(f"{C.INFO}  ➤  {msg}{C.RESET}")
def step(msg): print(f"\n{C.BOLD}{C.INFO}{'='*60}\n  {msg}\n{'='*60}{C.RESET}")

# =============================================================================
# BƯỚC 1: Bật dịch vụ SQL Server
# =============================================================================
_SQL_SERVICES = ["MSSQL$SQLEXPRESS", "MSSQLSERVER", "MSSQL$MSSQLSERVER"]

def _get_service_state(name: str) -> str | None:
    """Trả về 'Running', 'Stopped', hoặc None nếu service không tồn tại."""
    try:
        result = subprocess.run(
            ["sc", "query", name],
            capture_output=True, text=True, timeout=10
        )
        out = result.stdout
        if "RUNNING" in out:
            return "Running"
        if "STOPPED" in out:
            return "Stopped"
        return None
    except Exception:
        return None


def start_sql_service() -> str | None:
    """
    Tìm và bật dịch vụ SQL Server.
    Trả về tên service đã bật, hoặc None nếu thất bại.
    """
    step("BƯỚC 1: Bật dịch vụ SQL Server")

    found_service = None
    for svc in _SQL_SERVICES:
        state = _get_service_state(svc)
        if state == "Running":
            ok(f"Dịch vụ '{svc}' đang chạy.")
            return svc
        if state == "Stopped":
            found_service = svc
            break
        if state is not None:
            found_service = svc

    if found_service is None:
        # Thử dùng PowerShell để liệt kê tất cả SQL services
        info("Đang tìm dịch vụ SQL Server trên máy...")
        try:
            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 "Get-Service | Where-Object {$_.Name -like 'MSSQL*'} | Select-Object Name,Status | Format-Table -AutoSize"],
                capture_output=True, text=True, timeout=15
            )
            print(result.stdout.strip() or "(không tìm thấy dịch vụ MSSQL nào)")
        except Exception as e:
            warn(f"Không thể liệt kê services: {e}")
        err("Không tìm thấy dịch vụ SQL Server. Hãy cài SQL Server Express trước.")
        err("Tải tại: https://www.microsoft.com/sql-server/sql-server-downloads")
        return None

    info(f"Đang khởi động dịch vụ '{found_service}'...")
    try:
        result = subprocess.run(
            ["net", "start", found_service],
            capture_output=True, text=True, timeout=60
        )
        if result.returncode == 0:
            ok(f"Đã khởi động '{found_service}'.")
            time.sleep(3)  # Chờ service ổn định
            return found_service
        else:
            # Thử sc start
            result2 = subprocess.run(
                ["sc", "start", found_service],
                capture_output=True, text=True, timeout=60
            )
            if result2.returncode == 0:
                ok(f"Đã khởi động '{found_service}'.")
                time.sleep(3)
                return found_service
            else:
                err(f"Không thể khởi động '{found_service}'.")
                warn("Thử chạy script với quyền Administrator.")
                output_msg = result.stderr or result.stdout
                if output_msg:
                    print(f"  Chi tiết: {output_msg.strip()}")
                return None
    except subprocess.TimeoutExpired:
        warn("Timeout khi khởi động service. Tiếp tục thử kết nối...")
        return found_service
    except Exception as e:
        err(f"Lỗi khi bật service: {e}")
        return None


# =============================================================================
# BƯỚC 2: Kết nối SQL Server
# =============================================================================
def _detect_instance(service_name: str | None) -> str:
    """
    Xác định instance name từ service name.
    MSSQL$SQLEXPRESS -> hostname\\SQLEXPRESS
    MSSQLSERVER      -> hostname (default instance)
    """
    hostname = socket.gethostname()
    if service_name and "$" in service_name:
        instance = service_name.split("$", 1)[1]
        return f"{hostname}\\{instance}"
    return hostname  # default instance


def connect_sql_server(service_name: str | None) -> "pyodbc.Connection | None":
    """Kết nối SQL Server (master DB), trả về connection hoặc None."""
    step("BƯỚC 2: Kết nối SQL Server")

    try:
        import pyodbc
    except ImportError:
        err("pyodbc chưa được cài. Chạy: pip install pyodbc")
        return None

    # Lấy danh sách ODBC drivers
    available_drivers = [d for d in pyodbc.drivers() if "SQL Server" in d]
    if not available_drivers:
        err("Không tìm thấy ODBC Driver for SQL Server.")
        err("Tải tại: https://learn.microsoft.com/sql/connect/odbc/download-odbc-driver-for-sql-server")
        return None

    # Ưu tiên driver mới nhất
    preferred = ["ODBC Driver 18 for SQL Server",
                 "ODBC Driver 17 for SQL Server",
                 "ODBC Driver 13 for SQL Server",
                 "SQL Server"]
    driver = next((d for d in preferred if d in available_drivers), available_drivers[0])
    info(f"Dùng driver: {driver}")

    server = _detect_instance(service_name)
    info(f"Server: {server}")

    # Thử chuỗi kết nối với TrustServerCertificate
    conn_strings = [
        (f"DRIVER={{{driver}}};SERVER={server};DATABASE=master;"
         f"Trusted_Connection=yes;TrustServerCertificate=yes;"),
        (f"DRIVER={{{driver}}};SERVER={server};DATABASE=master;"
         f"Trusted_Connection=yes;"),
    ]

    for cs in conn_strings:
        try:
            conn = pyodbc.connect(cs, timeout=15)
            ok(f"Kết nối thành công → {server}")
            return conn
        except pyodbc.Error as e:
            pass

    # Thử các instance phổ biến nếu không kết nối được
    hostname = socket.gethostname()
    fallback_servers = [
        f"{hostname}\\SQLEXPRESS",
        f"{hostname}\\MSSQLSERVER",
        hostname,
        "localhost",
        "localhost\\SQLEXPRESS",
        "(local)",
        "(local)\\SQLEXPRESS",
    ]

    for srv in fallback_servers:
        if srv == server:
            continue
        cs = (f"DRIVER={{{driver}}};SERVER={srv};DATABASE=master;"
              f"Trusted_Connection=yes;TrustServerCertificate=yes;")
        try:
            conn = pyodbc.connect(cs, timeout=10)
            ok(f"Kết nối thành công → {srv}")
            return conn
        except pyodbc.Error:
            pass

    err("Không thể kết nối SQL Server. Kiểm tra:")
    err("  1. SQL Server Express đang chạy")
    err("  2. Windows Authentication được bật")
    err("  3. ODBC Driver 17+ được cài")
    return None


# =============================================================================
# BƯỚC 3: Tạo Database
# =============================================================================
DB_NAME = "He_Thong_Du_Doan_Thuoc"

def create_database(conn) -> bool:
    """Tạo database nếu chưa tồn tại."""
    step(f"BƯỚC 3: Tạo database '{DB_NAME}'")

    try:
        conn.autocommit = True
        cursor = conn.cursor()

        # Kiểm tra database đã tồn tại chưa
        cursor.execute(
            "SELECT database_id FROM sys.databases WHERE name = ?", DB_NAME
        )
        row = cursor.fetchone()

        if row:
            ok(f"Database '{DB_NAME}' đã tồn tại (ID={row[0]}). Bỏ qua tạo mới.")
        else:
            info(f"Đang tạo database '{DB_NAME}'...")
            # Dùng bracket để tránh lỗi tên có dấu gạch dưới
            cursor.execute(f"CREATE DATABASE [{DB_NAME}]")
            time.sleep(1)
            ok(f"Đã tạo database '{DB_NAME}'.")

        cursor.close()
        return True
    except Exception as e:
        err(f"Lỗi khi tạo database: {e}")
        return False


# =============================================================================
# BƯỚC 4: Tạo bảng bằng SQLAlchemy ORM
# =============================================================================
def create_tables() -> bool:
    """Tạo toàn bộ bảng từ ORM models.py."""
    step("BƯỚC 4: Tạo bảng ORM")

    try:
        from sqlalchemy import create_engine, text

        hostname = socket.gethostname()
        # Thử các kết nối
        urls_to_try = [
            f"mssql+pyodbc://{hostname}\\SQLEXPRESS/{DB_NAME}?driver=ODBC+Driver+17+for+SQL+Server&trusted_connection=yes&TrustServerCertificate=yes",
            f"mssql+pyodbc://{hostname}\\SQLEXPRESS/{DB_NAME}?driver=ODBC+Driver+18+for+SQL+Server&trusted_connection=yes&TrustServerCertificate=yes",
            f"mssql+pyodbc://{hostname}/{DB_NAME}?driver=ODBC+Driver+17+for+SQL+Server&trusted_connection=yes&TrustServerCertificate=yes",
            f"mssql+pyodbc://localhost\\SQLEXPRESS/{DB_NAME}?driver=ODBC+Driver+17+for+SQL+Server&trusted_connection=yes&TrustServerCertificate=yes",
        ]

        # Lấy URL từ biến môi trường nếu có
        env_url = os.getenv("MODEL_GNN_DB_URL")
        if env_url:
            urls_to_try.insert(0, env_url.replace("/master", f"/{DB_NAME}")
                               if "/master" in env_url else env_url)

        engine = None
        for url in urls_to_try:
            try:
                eng = create_engine(url, fast_executemany=True, pool_pre_ping=True)
                with eng.connect() as c:
                    c.execute(text("SELECT 1"))
                engine = eng
                info(f"SQLAlchemy kết nối: OK")
                break
            except Exception:
                pass

        if engine is None:
            err("SQLAlchemy không thể kết nối database.")
            return False

        # Import và tạo bảng
        from backend.app.models import Base
        info("Đang tạo bảng...")
        Base.metadata.create_all(bind=engine)
        tables = list(Base.metadata.tables.keys())
        ok(f"Đã tạo/xác nhận {len(tables)} bảng:")
        for t in sorted(tables):
            print(f"     📋 {t}")

        # Lưu URL vào biến môi trường để các bước sau dùng
        os.environ["MODEL_GNN_DB_URL"] = str(engine.url)
        return True

    except ImportError as e:
        err(f"Lỗi import: {e}")
        err("Đảm bảo đang dùng venv của project: .\\venv\\Scripts\\activate")
        return False
    except Exception as e:
        err(f"Lỗi khi tạo bảng: {e}")
        return False


# =============================================================================
# BƯỚC 5: Seed tài khoản mặc định
# =============================================================================
def _hash_password(password: str) -> str:
    """SHA-256 hash đơn giản (giống security.py)."""
    return hashlib.sha256(password.encode()).hexdigest()


def seed_default_accounts() -> None:
    """Tạo tài khoản admin và user mặc định nếu chưa có."""
    step("BƯỚC 5: Seed tài khoản mặc định")

    try:
        from sqlalchemy import create_engine, text
        from sqlalchemy.orm import Session

        db_url = os.environ.get("MODEL_GNN_DB_URL", "")
        if not db_url:
            warn("Không tìm thấy DATABASE_URL — bỏ qua seed tài khoản.")
            return

        engine = create_engine(db_url, fast_executemany=True, pool_pre_ping=True)
        from backend.app.models import User

        default_accounts = [
            {"username": "admin",  "password": "admin123",  "role": "admin",  "email": "admin@medlink.ai"},
            {"username": "user",   "password": "user123",   "role": "user",   "email": "user@medlink.ai"},
            {"username": "expert", "password": "expert123", "role": "expert", "email": "expert@medlink.ai"},
        ]

        with Session(engine) as session:
            for acc in default_accounts:
                existing = session.query(User).filter_by(username=acc["username"]).first()
                if existing:
                    ok(f"Tài khoản '{acc['username']}' đã tồn tại → bỏ qua.")
                else:
                    user = User(
                        username=acc["username"],
                        password_hash=_hash_password(acc["password"]),
                        role=acc["role"],
                        email=acc["email"],
                    )
                    session.add(user)
                    ok(f"Tạo tài khoản '{acc['username']}' (role={acc['role']}) ✔")
            session.commit()

    except Exception as e:
        warn(f"Không thể seed tài khoản: {e}")
        warn("Bạn có thể seed sau bằng: python seed_sqlserver.py")


# =============================================================================
# BƯỚC 6: In hướng dẫn tiếp theo
# =============================================================================
def print_next_steps() -> None:
    step("HOÀN TẤT — Hướng dẫn tiếp theo")
    print(f"""
  {C.OK}✔ Database '{DB_NAME}' đã sẵn sàng.{C.RESET}

  {C.BOLD}Bước tiếp theo:{C.RESET}

  1. Seed dữ liệu thuốc/bệnh/protein từ CSV:
     {C.INFO}python seed_sqlserver.py{C.RESET}

  2. Chạy ứng dụng:
     {C.INFO}.\\venv\\Scripts\\activate{C.RESET}
     {C.INFO}python main.py{C.RESET}

  3. Truy cập:
     • Giao diện: {C.INFO}http://localhost:8502{C.RESET}
     • API docs:  {C.INFO}http://127.0.0.1:8000/docs{C.RESET}

  {C.BOLD}Tài khoản mặc định:{C.RESET}
     • admin   / admin123   (quyền Admin)
     • user    / user123    (quyền User)
     • expert  / expert123  (quyền Expert)
""")


# =============================================================================
# MAIN
# =============================================================================
def main() -> int:
    print(f"""
{C.BOLD}{C.INFO}
╔══════════════════════════════════════════════════════════╗
║        MedLink AI — Database Setup Wizard                ║
║        Tự động cài đặt SQL Server Database               ║
╚══════════════════════════════════════════════════════════╝
{C.RESET}""")

    # Bước 1: Bật SQL Server
    service_name = start_sql_service()

    # Bước 2: Kết nối
    conn = connect_sql_server(service_name)
    if conn is None:
        err("\nKhông thể tiếp tục — không có kết nối SQL Server.")
        print(f"\n{C.WARN}Gợi ý khắc phục:{C.RESET}")
        print("  • Kiểm tra SQL Server Express đã cài chưa")
        print("  • Chạy script với quyền Administrator")
        print("  • Mở SQL Server Configuration Manager → bật TCP/IP")
        return 1

    # Bước 3: Tạo database
    if not create_database(conn):
        conn.close()
        return 1
    conn.close()

    # Bước 4: Tạo bảng
    if not create_tables():
        warn("Không tạo được bảng qua ORM — thử chạy lại hoặc tạo thủ công.")
        return 1

    # Bước 5: Seed tài khoản
    seed_default_accounts()

    # Bước 6: Hướng dẫn
    print_next_steps()
    return 0


if __name__ == "__main__":
    sys.exit(main())
