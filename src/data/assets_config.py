"""
assets_config.py — Cấu hình hình ảnh và tài nguyên trực quan cho giao diện web.
================================================================================

╔══════════════════════════════════════════════════════════════════╗
║  CÁCH ĐỔI ẢNH NỀN TRANG CHỦ (WALLPAPER)                        ║
║                                                                  ║
║  1. Mở thư mục:  src/data/wallpaper/                            ║
║  2. Đặt ảnh vào đó (jpg, jpeg, png, webp, gif)                  ║
║  3. Chỉ cần 1 ảnh — hệ thống tự nhận, không cần sửa code       ║
║  4. Reload trang web là xong                                     ║
║                                                                  ║
║  Gợi ý kích thước: 1920×1080 px trở lên để nét trên màn hình   ║
║  Nếu có nhiều ảnh: dùng tên file bắt đầu bằng số để ưu tiên    ║
║  (vd: 01_bg.jpg sẽ được dùng trước 02_bg.jpg)                   ║
╚══════════════════════════════════════════════════════════════════╝

Nếu thư mục wallpaper/ trống:
  Fallback 1 → src/data/assets/bg_landing.jpg  (nếu có)
  Fallback 2 → ảnh y tế từ Unsplash (online, luôn có sẵn)
"""
from __future__ import annotations

import base64
from pathlib import Path

# ─── Thư mục assets ────────────────────────────────────────────────────────
ASSETS_DIR = Path(__file__).resolve().parent / "assets"
ASSETS_DIR.mkdir(parents=True, exist_ok=True)

# ─── Thư mục wallpaper — chỉ cần thả ảnh vào đây ──────────────────────────
WALLPAPER_DIR = Path(__file__).resolve().parent / "wallpaper"
WALLPAPER_DIR.mkdir(parents=True, exist_ok=True)

_SUPPORTED_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}

# ─── Ảnh nền fallback (nếu wallpaper/ trống) ───────────────────────────────
_BG_LOCAL = ASSETS_DIR / "bg_landing.jpg"
BG_IMAGE_FALLBACK_URL = (
    "https://images.unsplash.com/photo-1532187863486-abf9dbad1b69"
    "?auto=format&fit=crop&w=1920&q=80"
)

# ─── Định dạng MIME cho base64 ─────────────────────────────────────────────
_EXT_MIME: dict[str, str] = {
    ".jpg":  "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png":  "image/png",
    ".webp": "image/webp",
    ".gif":  "image/gif",
}


def _encode_image(path: Path) -> str:
    """Đọc file ảnh → chuỗi CSS url('data:...')."""
    mime = _EXT_MIME.get(path.suffix.lower(), "image/jpeg")
    b64 = base64.b64encode(path.read_bytes()).decode()
    return f"url('data:{mime};base64,{b64}')"


def get_bg_css() -> str:
    """Trả về CSS background-image cho landing page.

    Thứ tự ưu tiên:
      1. Ảnh đầu tiên (theo thứ tự tên) trong src/data/wallpaper/
      2. src/data/assets/bg_landing.jpg
      3. URL fallback Unsplash (ảnh phòng lab/y tế, miễn phí)
    """
    # 1. Quét wallpaper/
    wallpapers = sorted(
        p for p in WALLPAPER_DIR.iterdir()
        if p.is_file() and p.suffix.lower() in _SUPPORTED_EXTS
    )
    if wallpapers:
        try:
            return _encode_image(wallpapers[0])
        except Exception:
            pass

    # 2. Fallback: assets/bg_landing.jpg
    if _BG_LOCAL.exists():
        try:
            return _encode_image(_BG_LOCAL)
        except Exception:
            pass

    # 3. URL online
    return f"url('{BG_IMAGE_FALLBACK_URL}')"


# ─── Màu sắc gradient nền overlay ─────────────────────────────────────────
LANDING_OVERLAY = (
    "linear-gradient(135deg, rgba(13,148,136,0.82) 0%, rgba(30,64,175,0.78) 100%)"
)

# ─── Thông tin hiển thị trên các section trang chủ ────────────────────────
SYSTEM_STATS = {
    "drugs":     "1,400+",
    "diseases":  "400+",
    "proteins":  "900+",
    "links":     "5,000+",
}

FEATURES = [
    {
        "icon": "🔬",
        "title": "Dự đoán AI chính xác",
        "desc": "Mô hình FuzzyGCN học trên đồ thị thuốc-bệnh-protein, cho AUC > 0.95.",
    },
    {
        "icon": "⚡",
        "title": "Tra cứu tức thì",
        "desc": "Nhập tên thuốc hoặc bệnh, nhận kết quả dự đoán trong vài giây.",
    },
    {
        "icon": "📊",
        "title": "Dữ liệu minh bạch",
        "desc": "Phân biệt rõ liên kết đã biết (xác nhận thực nghiệm) và AI dự đoán mới.",
    },
    {
        "icon": "🛡️",
        "title": "Bảo mật & phân quyền",
        "desc": "Hệ thống phân quyền admin/user, bảo vệ dữ liệu người dùng.",
    },
]

HOW_TO_USE = [
    {"step": "1", "title": "Đăng nhập", "desc": "Tạo tài khoản hoặc đăng nhập với tài khoản có sẵn."},
    {"step": "2", "title": "Chọn chức năng", "desc": "Dùng menu bên trái để chọn tra cứu thuốc, bệnh hoặc protein."},
    {"step": "3", "title": "Nhập từ khoá", "desc": "Nhập tên thuốc, bệnh hoặc ID cần tra cứu vào ô tìm kiếm."},
    {"step": "4", "title": "Xem kết quả", "desc": "AI trả về danh sách liên kết kèm xác suất và nguồn gốc dữ liệu."},
]
