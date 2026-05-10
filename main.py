"""
Khởi động toàn bộ ứng dụng MedLink AI từ 1 file duy nhất.

  python main.py                   # backend (8000) + Modern UI app_modern.py  ← MẶC ĐỊNH
  python main.py --modern-only     # CHỈ Modern UI, không cần backend (demo nhanh)
  python main.py --classic         # backend (8000) + giao diện cũ streamlit_app.py
  python main.py --ui-only         # chỉ chạy Modern UI (không backend)
  python main.py --api-only        # chỉ chạy FastAPI backend
  python main.py --api-port 8080 --ui-port 8503

Cổng mặc định có thể đổi tại đây:
"""
from __future__ import annotations

import argparse
import importlib.util
import logging
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path

import uvicorn

# ═══════════════════════════════════════════════════════
#   ĐỔI CỔNG TẠI ĐÂY (nếu bị xung đột)
# ═══════════════════════════════════════════════════════
DEFAULT_API_HOST = "127.0.0.1"
DEFAULT_API_PORT = 8000          # ← đổi cổng FastAPI tại đây
DEFAULT_UI_HOST  = "localhost"
DEFAULT_UI_PORT  = 8502          # ← đổi cổng Streamlit tại đây
# ═══════════════════════════════════════════════════════

# ── Cấu hình đường dẫn ──────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent
BACKEND_DIR = ROOT / "src" / "backend"
FRONTEND_ENTRY         = ROOT / "src" / "frontend" / "app_modern.py"    # ← giao diện mặc định
FRONTEND_CLASSIC_ENTRY = ROOT / "src" / "frontend" / "streamlit_app.py"  # ← UI cũ (--classic)

# Đảm bảo backend có thể import được
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

# ── Logger chung ─────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  →  %(message)s",
    datefmt="%H:%M:%S",
)
_log = logging.getLogger("medlink")


# ── Kiểm tra & tìm cổng trống ────────────────────────────────────────────────
def _is_port_free(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET6 if ":" in host else socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            s.bind((host, port))
            return True
        except OSError:
            return False


def _find_free_port(host: str, start: int, max_tries: int = 20) -> int:
    """Tìm cổng trống bắt đầu từ start."""
    for port in range(start, start + max_tries):
        if _is_port_free(host, port):
            return port
    raise RuntimeError(f"Không tìm được cổng trống trong khoảng {start}–{start + max_tries}")


def _kill_port(port: int) -> None:
    """Dùng netstat + taskkill để giải phóng cổng trên Windows."""
    try:
        import subprocess as _sp
        result = _sp.run(
            ["netstat", "-ano"],
            capture_output=True, text=True, timeout=5
        )
        for line in result.stdout.splitlines():
            if f":{port} " in line and "LISTENING" in line:
                parts = line.split()
                pid = parts[-1]
                _sp.run(["taskkill", "/F", "/PID", pid], capture_output=True, timeout=5)
                print(f"  [PORT] Đã giải phóng cổng {port} (PID {pid})")
                time.sleep(0.5)
                return
    except Exception:  # noqa: BLE001
        pass


def _ensure_port_free(host: str, port: int, label: str) -> int:
    """Kiểm tra cổng; nếu bận thì cố giải phóng hoặc tìm cổng mới."""
    if _is_port_free(host, port):
        return port
    print(f"  ⚠️  Cổng {port} ({label}) đang bận — đang thử giải phóng…")
    _kill_port(port)
    time.sleep(1)
    if _is_port_free(host, port):
        print(f"  ✅ Đã giải phóng cổng {port}")
        return port
    # Vẫn bận → tìm cổng kế tiếp
    new_port = _find_free_port(host, port + 1)
    print(f"  ℹ️  Dùng cổng thay thế: {new_port} thay cho {port}")
    return new_port


# ── Setup Database (chạy trong thread nền, không block UI) ─────────────────
def _run_db_setup() -> None:
    """Chạy setup_database.main() trong thread nền và pipe log ra console."""
    setup_path = ROOT / "setup_database.py"
    if not setup_path.exists():
        _log.warning("[DB-SETUP] Không tìm thấy setup_database.py — bỏ qua.")
        return

    _log.info("[DB-SETUP] Bắt đầu kiểm tra / khởi tạo database...")
    try:
        spec = importlib.util.spec_from_file_location("setup_database", setup_path)
        mod  = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        # Redirect print() của setup_database thành log
        import builtins, io, contextlib

        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            exit_code = mod.main()

        for line in buf.getvalue().splitlines():
            clean = line.strip()
            if not clean:
                continue
            # Phân loại mức log theo ký hiệu
            if any(x in clean for x in ("✔", "OK", "sẵn sàng")):
                _log.info("[DB-SETUP] " + clean)
            elif any(x in clean for x in ("✘", "Lỗi", "FAILED")):
                _log.error("[DB-SETUP] " + clean)
            elif any(x in clean for x in ("⚠", "Timeout", "bỏ qua")):
                _log.warning("[DB-SETUP] " + clean)
            elif clean.startswith(("═", "╔", "╚", "║", "│", "─", "═")):
                continue  # bỏ đường viền ASCII
            else:
                _log.info("[DB-SETUP] " + clean)

        if exit_code == 0:
            _log.info("[DB-SETUP] ✔ Hoàn tất — database sẵn sàng.")
        else:
            _log.warning("[DB-SETUP] Kết thúc với lỗi (code=%s) — xem log bên trên.", exit_code)

    except Exception as exc:
        _log.exception("[DB-SETUP] Lỗi không mong đợi: %s", exc)


def start_db_setup() -> threading.Thread:
    """Khởi chạy setup_database trong thread daemon — không block luồng chính."""
    t = threading.Thread(target=_run_db_setup, name="db-setup", daemon=True)
    t.start()
    _log.info("[DB-SETUP] Thread khởi động (chạy song song với API & UI).")
    return t


# ── Khởi động FastAPI (chạy trong thread nền) ────────────────────────────────
def _run_api(host: str, port: int, reload: bool) -> None:
    uvicorn.run(
        "app:app",
        host=host,
        port=port,
        reload=reload,
        app_dir=str(BACKEND_DIR),
        log_level="info",
    )


def start_api(host: str = DEFAULT_API_HOST, port: int = DEFAULT_API_PORT, reload: bool = False) -> threading.Thread:
    t = threading.Thread(target=_run_api, args=(host, port, reload), daemon=True, name="fastapi")
    t.start()
    return t


# ── Khởi động Streamlit ──────────────────────────────────────────────────────
def start_streamlit(
    host: str = DEFAULT_UI_HOST,
    port: int = DEFAULT_UI_PORT,
    classic: bool = False,
) -> None:
    """Khởi động Streamlit. Mặc định dùng app_modern.py; truyền classic=True để dùng UI cũ."""
    entry = FRONTEND_CLASSIC_ENTRY if classic else FRONTEND_ENTRY
    if not entry.exists():
        print(f"  ❌ Không tìm thấy {entry}")
        sys.exit(1)
    cmd = [
        sys.executable, "-m", "streamlit", "run",
        str(entry),
        "--server.address", host,
        "--server.port", str(port),
        "--server.headless", "true",
    ]
    label = "streamlit_app.py (Classic UI)" if classic else "app_modern.py (Modern UI)"
    print(f"  [UI]   Đang chạy: {label}")
    subprocess.run(cmd, check=False)


# ── Parse args ───────────────────────────────────────────────────────────────
def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="MedLink AI — khởi động toàn bộ ứng dụng",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="  Mặc định: python main.py  →  backend + Modern UI (app_modern.py)",
    )
    p.add_argument("--api-host",    default=DEFAULT_API_HOST, help=f"Host FastAPI (mặc định: {DEFAULT_API_HOST})")
    p.add_argument("--api-port",    type=int, default=DEFAULT_API_PORT, help=f"Port FastAPI (mặc định: {DEFAULT_API_PORT})")
    p.add_argument("--ui-host",     default=DEFAULT_UI_HOST,  help=f"Host Streamlit (mặc định: {DEFAULT_UI_HOST})")
    p.add_argument("--ui-port",     type=int, default=DEFAULT_UI_PORT, help=f"Port Streamlit (mặc định: {DEFAULT_UI_PORT})")
    p.add_argument("--reload",      action="store_true",  help="Bật auto-reload cho FastAPI (dev)")
    p.add_argument("--api-only",    action="store_true",  help="Chỉ chạy FastAPI backend")
    p.add_argument("--ui-only",     action="store_true",  help="Chỉ chạy Modern UI (app_modern.py), không backend")
    p.add_argument("--modern-only", action="store_true",  help="Alias của --ui-only")
    p.add_argument("--classic",     action="store_true",  help="Dùng giao diện cũ (streamlit_app.py) thay Modern UI")
    p.add_argument("--modern",      action="store_true",  help="[Không cần thiết] Modern UI là mặc định rồi")
    p.add_argument("--no-kill",     action="store_true",  help="Không tự động giải phóng cổng bận")
    return p.parse_args()


# ── Main ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    args = parse_args()

    # Kiểm tra & xử lý cổng bận (trừ khi --no-kill)
    if not args.no_kill:
        args.api_port = _ensure_port_free(args.api_host, args.api_port, "FastAPI")
        args.ui_port  = _ensure_port_free(args.ui_host,  args.ui_port,  "Streamlit")

    # ── Xác định chế độ giao diện ─────────────────────────────────────────────
    # Modern UI là mặc định; --classic để dùng UI cũ
    use_classic = args.classic
    # --ui-only hoặc --modern-only: chỉ chạy UI, không backend
    ui_only = args.ui_only or args.modern_only

    # ── Chạy DB setup song song (luôn luôn, trừ --ui-only / --modern-only) ──────
    if not ui_only:
        start_db_setup()

    if args.api_only:
        print(f"[API]  http://{args.api_host}:{args.api_port}")
        _run_api(args.api_host, args.api_port, args.reload)

    elif ui_only:
        # ── Chỉ chạy Modern UI standalone (không cần backend) ────────────────
        print("=" * 60)
        print("  MedLink AI — Modern UI (standalone, không cần backend)")
        print("=" * 60)
        print(f"  [UI]   http://{args.ui_host}:{args.ui_port}")
        print("  Giao diện: app_modern.py (FuzzyGCN + RBAC + Pyvis)")
        print("=" * 60)
        start_streamlit(args.ui_host, args.ui_port, classic=False)

    else:
        ui_label = "streamlit_app.py (Classic UI)" if use_classic else "app_modern.py (Modern UI)"
        print("=" * 60)
        print("  MedLink AI — Khởi động ứng dụng")
        print(f"  Giao diện: {ui_label}")
        print("=" * 60)
        print(f"  [API]  http://{args.api_host}:{args.api_port}")
        print(f"  [UI]   http://{args.ui_host}:{args.ui_port}")
        print("=" * 60)

        api_thread = start_api(args.api_host, args.api_port, args.reload)

        print("  Đang chờ API khởi động", end="", flush=True)
        _api_ready = False
        for _ in range(60):            # tối đa 30 giây
            time.sleep(0.5)
            if not api_thread.is_alive():
                print(" FAILED (thread died)")
                sys.exit(1)
            try:
                import urllib.request as _ur
                _ur.urlopen(
                    f"http://{args.api_host}:{args.api_port}/api/health",
                    timeout=1,
                )
                _api_ready = True
                break
            except Exception:
                print(".", end="", flush=True)
        if _api_ready:
            print(" OK")
        else:
            print(" timeout — API vẫn chưa phản hồi, tiếp tục…")

        start_streamlit(args.ui_host, args.ui_port, classic=use_classic)
