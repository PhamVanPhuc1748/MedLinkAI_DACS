"""
app_modern.py — Giao diện hiện đại cho hệ thống FuzzyGCN (MedLink AI)
======================================================================
Chức năng:
  - Glassmorphism + Neon UI với streamlit-option-menu
  - Phân quyền RBAC: Guest / User / Expert / Admin
  - Trang Landing / Đăng nhập (giữ nguyên đồ họa cũ)
  - Tab Trạm Dự Đoán   → User, Expert, Admin
  - Tab Lưới Sinh Học   → pyvis 15 nodes tương tác
  - Tab Duyệt Liên Kết  → Expert, Admin
  - Tab Cấu Hình        → Admin

Chạy: streamlit run src/frontend/app_modern.py
Yêu cầu: pip install streamlit streamlit-option-menu pyvis
"""
from __future__ import annotations

import json
import os
import random
import re
import sys
import tempfile
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
import base64 as _b64


def _html_iframe(html_str: str, height: int, scrolling: bool = False) -> None:
    """Render HTML string bằng st.iframe thông qua file tạm (Streamlit 1.57+).
    
    st.iframe mới chỉ nhận đường dẫn file hoặc URL, không nhận HTML string trực tiếp.
    Hàm này ghi HTML ra file tạm, trỏ iframe đến file đó, rồi dọn dẹp.
    """
    import tempfile
    import os as _os
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".html", delete=False, encoding="utf-8"
    ) as _f:
        _f.write(html_str)
        _tmp = _f.name
    try:
        st.iframe(_tmp, height=height)
    finally:
        try:
            _os.unlink(_tmp)
        except OSError:
            pass

# ── Đảm bảo sys.path đúng để import nội bộ ───────────────────────────────────
ROOT = Path(__file__).resolve().parents[1]          # src/
PROJECT_ROOT = Path(__file__).resolve().parents[2]  # project root
for _p in (str(ROOT), str(PROJECT_ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

# ── Import pyvis (optional — cảnh báo nếu chưa cài) ──────────────────────────
try:
    from pyvis.network import Network as PyvisNetwork
    _PYVIS_OK = True
except ImportError:
    _PYVIS_OK = False

# ── Import streamlit-option-menu ──────────────────────────────────────────────
try:
    from streamlit_option_menu import option_menu
    _MENU_OK = True
except ImportError:
    _MENU_OK = False

# ── Import backend API client (tùy chọn) ──────────────────────────────────────
try:
    from frontend.app.services.api_client import ApiClient  # type: ignore
    from frontend.app.config import API_DEFAULT              # type: ignore
    _API_OK = True
except Exception:
    _API_OK = False
    API_DEFAULT = "http://localhost:8000"

try:
    from backend.app.security import hash_password as auth_hash_password  # type: ignore
except Exception:
    import hashlib

    def auth_hash_password(password: str) -> str:
        return hashlib.sha256(password.encode("utf-8")).hexdigest()


# =============================================================================
# CẤU HÌNH TRANG (phải gọi đầu tiên)
# =============================================================================
st.set_page_config(
    page_title="MedLink AI — FuzzyGCN",
    page_icon="💊",
    layout="wide",
    initial_sidebar_state="expanded",
)


# =============================================================================
# CSS TOÀN CỤC — Glassmorphism + Neon + Ẩn menu mặc định Streamlit
# =============================================================================
GLOBAL_CSS = """
<style>
/* ── Ẩn hamburger menu và footer mặc định của Streamlit ── */
#MainMenu { visibility: hidden !important; }
footer    { visibility: hidden !important; }
/* Ẩn header nhưng giữ lại các phần tử cần thiết */
header    { visibility: hidden !important; }
/* Ẩn nút toggle sidebar (cả expand lẫn collapse) — sidebar sẽ luôn cố định */
[data-testid="collapsedControl"]         { display: none !important; }
[data-testid="stSidebarCollapseButton"]  { display: none !important; }
button[kind="header"]                    { display: none !important; }

/* ── Biến màu Dark-neon ── */
:root {
  --bg:           #0a0f1e;
  --surface:      rgba(255,255,255,0.06);
  --surface-2:    rgba(255,255,255,0.10);
  --border:       rgba(255,255,255,0.12);
  --text:         #e2e8f0;
  --muted:        #94a3b8;
  --neon-cyan:    #00f5d4;
  --neon-blue:    #00b4d8;
  --neon-purple:  #7c3aed;
  --neon-pink:    #f72585;
  --danger:       #f87171;
  --success:      #4ade80;
  --warn:         #fbbf24;
  --radius:       14px;
  --radius-lg:    20px;
  --glow-cyan:    0 0 20px rgba(0,245,212,0.35), 0 0 60px rgba(0,245,212,0.12);
  --glow-blue:    0 0 20px rgba(0,180,216,0.35), 0 0 60px rgba(0,180,216,0.12);
  --glow-purple:  0 0 20px rgba(124,58,237,0.45);
  --shadow:       0 4px 24px rgba(0,0,0,0.5);
  --shadow-lg:    0 8px 48px rgba(0,0,0,0.7);
}

/* ── Nền chính gradient tối ── */
.stApp {
  background: linear-gradient(135deg, #0a0f1e 0%, #0d1b2a 50%, #0a1628 100%) !important;
  background-attachment: fixed !important;
}

/* ── Sidebar nền kính mờ ── */
section[data-testid="stSidebar"] {
  background: linear-gradient(180deg, rgba(10,15,30,0.97) 0%, rgba(13,27,42,0.97) 100%) !important;
  border-right: 1px solid var(--border) !important;
  backdrop-filter: blur(20px) !important;
}

/* ── Thẻ Glassmorphism cơ bản ── */
.glass-card {
  background: rgba(255,255,255,0.05);
  border: 1px solid rgba(255,255,255,0.12);
  border-radius: var(--radius-lg);
  padding: 1.6rem 1.8rem;
  backdrop-filter: blur(16px);
  box-shadow: var(--shadow);
  margin-bottom: 1.2rem;
  transition: border-color 0.3s ease, box-shadow 0.3s ease;
}
.glass-card:hover {
  border-color: rgba(0,245,212,0.3);
  box-shadow: var(--shadow), 0 0 30px rgba(0,245,212,0.08);
}

/* ── Thẻ Metric neon ── */
.metric-card {
  background: rgba(255,255,255,0.04);
  border: 1px solid rgba(0,245,212,0.25);
  border-radius: var(--radius-lg);
  padding: 1.4rem 1.6rem;
  text-align: center;
  backdrop-filter: blur(12px);
  box-shadow: var(--shadow), 0 0 20px rgba(0,245,212,0.08);
  transition: all 0.3s ease;
  position: relative;
  overflow: hidden;
}
.metric-card::before {
  content: '';
  position: absolute;
  top: 0; left: 0; right: 0;
  height: 2px;
  background: linear-gradient(90deg, transparent, var(--neon-cyan), transparent);
  animation: shimmer-top 2.5s ease-in-out infinite;
}
@keyframes shimmer-top {
  0%,100% { opacity: 0.4; }
  50%      { opacity: 1; }
}
.metric-card:hover {
  border-color: rgba(0,245,212,0.5);
  box-shadow: var(--glow-cyan), var(--shadow-lg);
  transform: translateY(-3px);
}
.metric-value {
  font-size: 2.4rem;
  font-weight: 900;
  color: var(--neon-cyan);
  line-height: 1;
  text-shadow: var(--glow-cyan);
  letter-spacing: -0.03em;
}
.metric-label {
  font-size: 0.78rem;
  color: var(--muted);
  margin-top: 0.4rem;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  font-weight: 600;
}
.metric-delta {
  font-size: 0.82rem;
  margin-top: 0.5rem;
  font-weight: 700;
}

/* ── Nút Neon ── */
.stButton > button {
  background: linear-gradient(135deg, rgba(0,245,212,0.15), rgba(0,180,216,0.15)) !important;
  border: 1.5px solid var(--neon-cyan) !important;
  color: var(--neon-cyan) !important;
  border-radius: var(--radius) !important;
  font-weight: 700 !important;
  font-size: 0.88rem !important;
  transition: all 0.25s ease !important;
  text-shadow: 0 0 10px rgba(0,245,212,0.5) !important;
}
.stButton > button:hover {
  background: rgba(0,245,212,0.25) !important;
  box-shadow: var(--glow-cyan) !important;
  transform: translateY(-2px) !important;
}

/* ── Nút Primary neon mạnh hơn ── */
.stButton > button[kind="primary"],
.stButton > button[data-testid="baseButton-primary"] {
  background: linear-gradient(135deg, #00f5d4 0%, #00b4d8 100%) !important;
  border: none !important;
  color: #0a0f1e !important;
  text-shadow: none !important;
  font-weight: 800 !important;
  box-shadow: var(--glow-cyan) !important;
}
.stButton > button[kind="primary"]:hover {
  box-shadow: 0 0 40px rgba(0,245,212,0.6), 0 0 80px rgba(0,245,212,0.2) !important;
  transform: translateY(-3px) !important;
}

/* ── Input fields ── */
.stTextInput > div > div > input,
.stSelectbox > div > div,
.stNumberInput input,
.stTextArea textarea {
  background: rgba(255,255,255,0.04) !important;
  border: 1.5px solid rgba(255,255,255,0.15) !important;
  border-radius: var(--radius) !important;
  color: var(--text) !important;
  font-size: 0.9rem !important;
  transition: border-color 0.2s ease, box-shadow 0.2s ease !important;
}
.stTextInput > div > div > input:focus,
.stTextArea textarea:focus {
  border-color: var(--neon-cyan) !important;
  box-shadow: 0 0 0 3px rgba(0,245,212,0.15) !important;
}
.stSelectbox > div > div > div,
[data-baseweb="select"] { background: rgba(10,15,30,0.9) !important; }
div[data-baseweb="popover"] ul { background: #0d1b2a !important; }
div[data-baseweb="option"]:hover { background: rgba(0,245,212,0.1) !important; }

/* ── Slider ── */
.stSlider [data-baseweb="slider"] div[role="slider"] {
  background: var(--neon-cyan) !important;
  box-shadow: var(--glow-cyan) !important;
}
.stSlider [data-baseweb="slider"] div[data-testid="stThumb"] {
  background: var(--neon-cyan) !important;
}

/* ── Tiêu đề trang ── */
.page-title {
  font-size: clamp(1.5rem, 3vw, 2.2rem);
  font-weight: 900;
  background: linear-gradient(90deg, var(--neon-cyan), var(--neon-blue));
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  letter-spacing: -0.03em;
  margin-bottom: 0.3rem;
}
.page-subtitle {
  font-size: 0.9rem;
  color: var(--muted);
  margin-bottom: 1.8rem;
}

/* ── Badge vai trò ── */
.role-badge {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  padding: 0.28rem 0.8rem;
  border-radius: 999px;
  font-size: 0.76rem;
  font-weight: 700;
  letter-spacing: 0.05em;
  text-transform: uppercase;
}
.role-guest   { background: rgba(148,163,184,0.15); border:1px solid #64748b; color:#94a3b8; }
.role-user    { background: rgba(0,180,216,0.15);   border:1px solid var(--neon-blue);   color:var(--neon-blue); }
.role-expert  { background: rgba(124,58,237,0.15);  border:1px solid var(--neon-purple); color:#a78bfa; }
.role-admin   { background: rgba(247,37,133,0.15);  border:1px solid var(--neon-pink);   color:var(--neon-pink); }

/* ── Logo sidebar ── */
.sidebar-logo {
  padding: 0.6rem 0 1rem;
  text-align: left;
}
.sidebar-logo-title {
  font-size: 1.35rem;
  font-weight: 900;
  color: var(--neon-cyan);
  letter-spacing: -0.03em;
  text-shadow: 0 0 20px rgba(0,245,212,0.4);
}
.sidebar-logo-sub {
  font-size: 0.7rem;
  color: var(--muted);
  margin-top: 0.1rem;
  letter-spacing: 0.05em;
  text-transform: uppercase;
}

/* ── Separator ── */
.neon-hr {
  border: none;
  height: 1px;
  background: linear-gradient(90deg, transparent, var(--neon-cyan), transparent);
  margin: 0.9rem 0;
  opacity: 0.35;
}

/* ── Cảnh báo phân quyền ── */
.access-denied {
  background: rgba(247,37,133,0.08);
  border: 1px solid rgba(247,37,133,0.35);
  border-radius: var(--radius-lg);
  padding: 2rem;
  text-align: center;
  color: var(--neon-pink);
}

/* ── Bảng kết quả dự đoán ── */
.result-table-wrap {
  background: rgba(255,255,255,0.03);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: 1.2rem;
  backdrop-filter: blur(10px);
}

/* ── Score bar ── */
.score-bar-bg {
  background: rgba(255,255,255,0.08);
  border-radius: 999px;
  height: 6px;
  width: 100%;
  overflow: hidden;
}
.score-bar-fill {
  height: 100%;
  border-radius: 999px;
  background: linear-gradient(90deg, var(--neon-cyan), var(--neon-blue));
  box-shadow: 0 0 8px rgba(0,245,212,0.6);
  transition: width 0.6s ease;
}

/* ── Label đã biết / dự đoán ── */
.badge-known {
  background: rgba(74,222,128,0.15);
  border: 1px solid rgba(74,222,128,0.4);
  color: #4ade80;
  padding: 0.18rem 0.6rem;
  border-radius: 999px;
  font-size: 0.72rem;
  font-weight: 700;
}
.badge-pred {
  background: rgba(0,180,216,0.15);
  border: 1px solid rgba(0,180,216,0.4);
  color: var(--neon-blue);
  padding: 0.18rem 0.6rem;
  border-radius: 999px;
  font-size: 0.72rem;
  font-weight: 700;
}

/* ── Animation fade-in ── */
@keyframes fadeInUp {
  from { opacity: 0; transform: translateY(20px); }
  to   { opacity: 1; transform: translateY(0); }
}
.fade-in { animation: fadeInUp 0.5s ease both; }

/* ── Scrollbar tuỳ chỉnh ── */
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: rgba(0,245,212,0.3); border-radius: 999px; }

/* ── Streamlit dataframe ── */
.stDataFrame { border-radius: var(--radius) !important; overflow: hidden; }
iframe { border-radius: var(--radius-lg) !important; }

/* ── Icon trang trí nền ── */
.bg-deco {
  position: fixed;
  top: 0; left: 0; right: 0; bottom: 0;
  pointer-events: none;
  z-index: 0;
  overflow: hidden;
}
.bg-deco span {
  position: absolute;
  font-size: 7.5rem;
  opacity: 0.07;
  user-select: none;
  filter: blur(0px) drop-shadow(0 0 12px rgba(0,245,212,0.18));
  animation: deco-float 12s ease-in-out infinite alternate;
}
@keyframes deco-float {
  0%   { transform: translateY(0px) rotate(0deg) scale(1); }
  100% { transform: translateY(-22px) rotate(10deg) scale(1.06); }
}
</style>
"""

_BG_DECO_HTML = """
<div class="bg-deco">
  <span style="top:4%;left:6%;animation-delay:0s;">💊</span>
  <span style="top:10%;right:9%;animation-delay:1.5s;">🧬</span>
  <span style="top:27%;left:2%;animation-delay:3s;">🦠</span>
  <span style="top:42%;right:4%;animation-delay:0.8s;">⚗️</span>
  <span style="top:60%;left:12%;animation-delay:2.2s;">🔬</span>
  <span style="top:74%;right:16%;animation-delay:4s;">💉</span>
  <span style="top:86%;left:4%;animation-delay:1s;">🧪</span>
  <span style="top:18%;left:48%;animation-delay:2.8s;">🫀</span>
  <span style="top:52%;right:42%;animation-delay:0.4s;">🧫</span>
  <span style="top:80%;left:52%;animation-delay:3.5s;">🩺</span>
  <span style="top:35%;left:28%;animation-delay:5s;">🧲</span>
  <span style="top:68%;right:28%;animation-delay:1.8s;">⚕️</span>
</div>
"""


# =============================================================================
# DỮ LIỆU MẪU (dùng khi không kết nối được API)
# =============================================================================
SAMPLE_DRUGS = [
    "Aspirin", "Metformin", "Lisinopril", "Atorvastatin", "Omeprazole",
    "Amlodipine", "Metoprolol", "Losartan", "Albuterol", "Gabapentin",
    "Sertraline", "Levothyroxine", "Hydrochlorothiazide", "Simvastatin", "Warfarin",
]

SAMPLE_DISEASES = [
    "Tiểu đường type 2", "Tăng huyết áp", "Bệnh tim mạch vành", "Viêm khớp dạng thấp",
    "Hen phế quản", "Trầm cảm", "Parkinson", "Alzheimer", "Ung thư phổi",
    "Đột quỵ", "Suy tim", "Viêm phổi", "Nhiễm HIV", "Vẩy nến", "Lupus ban đỏ",
]

SAMPLE_PROTEINS = [
    "ACE", "EGFR", "TNF-α", "IL-6", "COX-2",
    "HER2", "VEGF", "p53", "BRCA1", "mTOR",
    "AKT1", "NF-κB", "JAK2", "STAT3", "BCL-2",
]

# Dữ liệu lịch sử dự đoán mẫu (toàn cục — trong session thực tế sẽ lưu DB)
HISTORY_RECORDS: list[dict] = []

# Dữ liệu duyệt liên kết mẫu cho Expert/Admin
PENDING_LINKS = [
    {"id": 1, "drug": "Metformin",    "disease": "Alzheimer",       "score": 0.87, "status": "Chờ duyệt"},
    {"id": 2, "drug": "Atorvastatin", "disease": "Lupus ban đỏ",    "score": 0.79, "status": "Chờ duyệt"},
    {"id": 3, "drug": "Aspirin",      "disease": "Parkinson",       "score": 0.74, "status": "Chờ duyệt"},
    {"id": 4, "drug": "Sertraline",   "disease": "Bệnh tim mạch vành", "score": 0.68, "status": "Chờ duyệt"},
    {"id": 5, "drug": "Lisinopril",   "disease": "Vẩy nến",         "score": 0.63, "status": "Chờ duyệt"},
    {"id": 6, "drug": "Gabapentin",   "disease": "Viêm khớp dạng thấp", "score": 0.61, "status": "Chờ duyệt"},
    {"id": 7, "drug": "Albuterol",    "disease": "Trầm cảm",        "score": 0.55, "status": "Chờ duyệt"},
]


# =============================================================================
# HELPER — PHÂN QUYỀN (RBAC)
# =============================================================================
# Thứ tự quyền từ thấp đến cao
ROLE_LEVELS = {"guest": 0, "user": 1, "expert": 2, "admin": 3}
ROLE_LABELS  = {"guest": "Khách",       "user": "Bác sĩ",
                "expert": "Chuyên gia", "admin": "Quản trị"}
ROLE_ICONS   = {"guest": "👤",  "user": "🩺", "expert": "🔬", "admin": "👑"}
ROLE_CLASSES = {"guest": "role-guest", "user": "role-user",
                "expert": "role-expert", "admin": "role-admin"}


def _restore_session_from_url() -> None:
    """
    Khôi phục session từ URL query params sau khi F5.
    Token được lưu vào URL: ?token=xxx
    Khi reload, hàm này đọc token từ URL và xác thực với Backend để phục hồi role/username.
    """
    # Nếu đã có session rồi (chưa F5), bỏ qua
    if st.session_state.get("demo_role", "guest") != "guest":
        return
    if st.session_state.get("api_token"):
        return

    # Đọc token từ URL query params
    try:
        params = st.query_params
        token = params.get("token", "")
        page  = params.get("page", "")
        if not token:
            return

        # Xác thực token với Backend bằng cách gọi /api/stats (endpoint cần auth)
        import requests as _req
        resp = _req.get(
            f"{API_DEFAULT}/stats",
            headers={"Authorization": f"Bearer {token}"},
            timeout=5,
        )
        if resp.status_code == 200:
            # Token hợp lệ — nhưng /stats không trả về role/username
            # Nên ta lưu token và để hệ thống tự xác định qua /admin/users
            # Thử gọi /admin/users để lấy role (chỉ admin gọi được)
            resp_role = _req.get(
                f"{API_DEFAULT}/admin/users?limit=1",
                headers={"Authorization": f"Bearer {token}"},
                timeout=5,
            )
            if resp_role.status_code == 200:
                role = "admin"
            else:
                # Thử gọi expert-only endpoint
                resp_exp = _req.get(
                    f"{API_DEFAULT}/model/metrics",
                    headers={"Authorization": f"Bearer {token}"},
                    timeout=5,
                )
                role = "expert" if resp_exp.status_code == 200 else "user"

            # Lấy username từ token store phía backend (không có endpoint riêng)
            # Dùng username đã lưu trong query params nếu có
            username = params.get("user", role)

            st.session_state["api_token"] = token
            st.session_state["demo_role"] = role
            st.session_state["username"]  = username
            if page:
                st.session_state["_restore_page"] = page
        # Nếu token hết hạn hoặc sai, xóa khỏi URL
        else:
            st.query_params.clear()
    except Exception:
        pass  # Bỏ qua mọi lỗi mạng khi restore


def _role() -> str:
    """Lấy vai trò hiện tại từ session_state."""
    return st.session_state.get("demo_role", "guest")


def _can(min_role: str) -> bool:
    """Kiểm tra người dùng có đủ quyền tối thiểu không."""
    return ROLE_LEVELS.get(_role(), 0) >= ROLE_LEVELS.get(min_role, 999)


def _is_logged_in() -> bool:
    """Giả lập trạng thái đăng nhập: guest = chưa đăng nhập."""
    return _role() != "guest"


def _history_cache_key() -> str:
    username = st.session_state.get("username", "guest")
    return f"prediction_history_cache::{username}"


def _clear_prediction_history_cache() -> None:
    st.session_state.pop(_history_cache_key(), None)


def _history_client() -> ApiClient | None:
    if not _API_OK or not st.session_state.get("api_token"):
        return None
    client = ApiClient(API_DEFAULT)
    client.token = st.session_state["api_token"]
    return client


def _load_prediction_history(force: bool = False) -> list[dict]:
    cache_key = _history_cache_key()
    if not force and cache_key in st.session_state:
        return st.session_state.get(cache_key, [])

    client = _history_client()
    if client is None:
        st.session_state[cache_key] = []
        return []

    rows = client.history()
    st.session_state[cache_key] = rows
    return rows


def _format_history_rows(rows: list[dict]) -> pd.DataFrame:
    formatted_rows: list[dict] = []
    direction_map = {
        "drug_to_disease": "Thuốc → Bệnh",
        "disease_to_drug": "Bệnh → Thuốc",
    }
    for item in rows:
        ts_raw = item.get("timestamp")
        try:
            ts_text = datetime.fromisoformat(str(ts_raw)).strftime("%d/%m/%Y %H:%M:%S")
        except (TypeError, ValueError):
            ts_text = str(ts_raw or "")

        score_raw = item.get("score", 0)
        try:
            score_val = round(float(score_raw), 4)
        except (TypeError, ValueError):
            score_val = 0.0

        formatted_rows.append({
            "Thời gian": ts_text,
            "Truy vấn": item.get("input_name", ""),
            "Chiều": direction_map.get(item.get("direction", ""), item.get("direction", "")),
            "Kết quả": item.get("target_name", ""),
            "Điểm": score_val,
            "Nguồn": "Đã biết" if item.get("known") else "AI dự đoán",
        })
    return pd.DataFrame(formatted_rows)


# =============================================================================
# COMPONENT — TRANG LANDING / ĐĂNG NHẬP (giữ nguyên đồ họa)
# =============================================================================
@st.dialog("Đăng nhập Hệ Thống")
def render_login_dialog() -> None:
    st.markdown("""
      <div style="text-align:center;margin-bottom:1rem;">
        <div style="font-size:1.8rem;line-height:1;">💊 <span style="font-size:1.2rem;font-weight:900;color:#00f5d4;">MedLink AI</span></div>
      </div>
    """, unsafe_allow_html=True)

    # Tab chọn đăng nhập / đăng ký (giao diện giả lập)
    tab_login, tab_register, tab_forgot = st.tabs([
        "🔑 Đăng nhập", "📝 Đăng ký", "🔓 Quên mật khẩu"
    ])

    with tab_login:
        username_in = st.text_input("Tên đăng nhập", placeholder="Nhập tên đăng nhập...")
        password_in = st.text_input("Mật khẩu", type="password", placeholder="Nhập mật khẩu...")

        if st.button("🚀 Đăng nhập", use_container_width=True, type="primary",
                     key="btn_demo_login"):
            if username_in.strip() and password_in:
                if _API_OK:
                    import logging
                    
                    # Khởi tạo logger để in ra terminal
                    logger = logging.getLogger("MedLink_Frontend")
                    if not logger.handlers:
                        handler = logging.StreamHandler()
                        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
                        handler.setFormatter(formatter)
                        logger.addHandler(handler)
                    logger.setLevel(logging.INFO)
                    
                    client = ApiClient(API_DEFAULT)
                    try:
                        logger.info(f">>> [WEB] Đang gọi API Login tới: {API_DEFAULT}/auth/login với username: '{username_in.strip()}'")
                        res = client.login(username_in.strip(), password_in)
                        logger.info(f"<<< [API] Trả về thành công: {res}")
                        
                        st.session_state["demo_role"] = res.get("role", "user")
                        st.session_state["username"]  = res.get("username", username_in.strip())
                        st.session_state["api_token"] = res.get("token", "")
                        _clear_prediction_history_cache()
                        HISTORY_RECORDS.clear()
                        # Lưu token vào URL để khôi phục sau F5
                        st.query_params["token"] = res.get("token", "")
                        st.query_params["user"]  = res.get("username", username_in.strip())
                        st.success("Đăng nhập thành công!")
                        st.rerun()
                    except Exception as e:
                        logger.error(f"!!! [API] Lỗi khi đăng nhập: {e}")
                        st.error(f"Sai tên đăng nhập hoặc mật khẩu! (Chi tiết: {e})")
                else:
                    st.error("Lỗi: Không thể kết nối đến Backend API. Kiểm tra xem server FastAPI đã chạy chưa.")
            else:
                st.warning("Vui lòng nhập đầy đủ tên đăng nhập và mật khẩu.")

    with tab_register:
        reg_user_  = st.text_input("Tên đăng nhập", placeholder="Tối thiểu 3 ký tự", key="lp_reg_user")
        reg_email_ = st.text_input("Email", placeholder="email@hospital.vn", key="lp_reg_email")
        reg_pass_  = st.text_input("Mật khẩu", type="password", placeholder="Tối thiểu 6 ký tự", key="lp_reg_pass")
        reg_conf_  = st.text_input("Xác nhận mật khẩu", type="password", placeholder="Nhập lại mật khẩu", key="lp_reg_conf")
        if st.button("📝 Tạo tài khoản", use_container_width=True, key="btn_lp_register"):
            if not reg_user_ or not reg_email_ or not reg_pass_ or not reg_conf_:
                st.warning("⚠️ Vui lòng điền đầy đủ tất cả các trường.")
            elif len(reg_user_.strip()) < 3:
                st.warning("⚠️ Tên đăng nhập phải có ít nhất 3 ký tự.")
            elif "@" not in reg_email_ or "." not in reg_email_.split("@")[-1]:
                st.warning("⚠️ Địa chỉ email không hợp lệ.")
            elif len(reg_pass_) < 6:
                st.warning("⚠️ Mật khẩu phải có ít nhất 6 ký tự.")
            elif reg_pass_ != reg_conf_:
                st.warning("⚠️ Mật khẩu xác nhận không khớp.")
            elif _API_OK:
                try:
                    client = ApiClient(API_DEFAULT)
                    client.register(
                        username=reg_user_.strip(),
                        email=reg_email_.strip().lower(),
                        password=reg_pass_,
                    )
                    st.success("✅ Đăng ký thành công! Bạn có thể đăng nhập ngay.")
                except Exception as exc:
                    st.error(f"❌ Đăng ký thất bại: {exc}")
            else:
                st.error("Không thể kết nối Backend API.")

    # ── TAB QUÊN MẬT KHẨU ─────────────────────────────────────────
    with tab_forgot:
        otp_sent = st.session_state.get("lp_otp_sent", False)

        if not otp_sent:
            st.markdown("""
            <div style="background:rgba(59,130,246,0.08);border:1px solid rgba(59,130,246,0.3);
                        border-radius:10px;padding:0.8rem 1rem;font-size:0.83rem;color:#93c5fd;
                        margin-bottom:1rem;">
              📬 Nhập tên đăng nhập và email đã đăng ký. Hệ thống sẽ gửi mã OTP 6 chữ số.
              Mã có hiệu lực <strong>10 phút</strong>.
            </div>
            """, unsafe_allow_html=True)
            fp_user_  = st.text_input("👤 Tên đăng nhập", placeholder="Tên đăng nhập của bạn", key="lp_fp_user")
            fp_email_ = st.text_input("📧 Email đã đăng ký", placeholder="email@hospital.vn", key="lp_fp_email")
            if st.button("📨 Gửi mã OTP", use_container_width=True, key="btn_lp_send_otp"):
                if not fp_user_ or not fp_email_:
                    st.warning("⚠️ Vui lòng nhập đủ tên đăng nhập và email.")
                elif _API_OK:
                    try:
                        client = ApiClient(API_DEFAULT)
                        result = client.forgot_password(
                            username=fp_user_.strip(),
                            email=fp_email_.strip().lower(),
                        )
                        st.session_state["lp_otp_sent"]    = True
                        st.session_state["lp_fp_username"] = fp_user_.strip()
                        st.success(f"✅ {result.get('message', 'Đã gửi OTP!')}")
                        st.rerun()
                    except Exception as exc:
                        st.error(f"❌ {exc}")
                else:
                    st.error("Không thể kết nối Backend API.")
        else:
            fp_username_disp = st.session_state.get("lp_fp_username", "")
            st.markdown(f"""
            <div style="background:rgba(16,185,129,0.08);border:1px solid rgba(16,185,129,0.3);
                        border-radius:10px;padding:0.8rem 1rem;font-size:0.83rem;color:#6ee7b7;
                        margin-bottom:1rem;">
              ✅ Mã OTP đã được gửi tới email của tài khoản <strong>{fp_username_disp}</strong>.
              Vui lòng kiểm tra hộp thư (kể cả spam).
            </div>
            """, unsafe_allow_html=True)
            fp_otp_   = st.text_input("🔢 Mã OTP (6 chữ số)", placeholder="123456", max_chars=6, key="lp_fp_otp")
            fp_newpw_ = st.text_input("🔒 Mật khẩu mới", type="password", placeholder="Tối thiểu 6 ký tự", key="lp_fp_newpw")
            fp_conf_  = st.text_input("🔒 Xác nhận mật khẩu mới", type="password", placeholder="Nhập lại", key="lp_fp_conf")

            col_reset, col_resend = st.columns(2)
            with col_reset:
                if st.button("🔓 Đặt lại mật khẩu", use_container_width=True, key="btn_lp_reset_pw"):
                    if not fp_otp_ or not fp_newpw_ or not fp_conf_:
                        st.warning("⚠️ Vui lòng điền đầy đủ tất cả các trường.")
                    elif len(fp_otp_.strip()) != 6 or not fp_otp_.strip().isdigit():
                        st.warning("⚠️ Mã OTP phải gồm đúng 6 chữ số.")
                    elif len(fp_newpw_) < 6:
                        st.warning("⚠️ Mật khẩu mới phải có ít nhất 6 ký tự.")
                    elif fp_newpw_ != fp_conf_:
                        st.warning("⚠️ Mật khẩu xác nhận không khớp.")
                    elif _API_OK:
                        try:
                            client = ApiClient(API_DEFAULT)
                            result = client.reset_password(
                                username=fp_username_disp,
                                otp=fp_otp_.strip(),
                                new_password=fp_newpw_,
                            )
                            st.success(f"✅ {result.get('message', 'Đặt lại mật khẩu thành công!')}")
                            st.session_state.pop("lp_otp_sent", None)
                            st.session_state.pop("lp_fp_username", None)
                            st.rerun()
                        except Exception as exc:
                            st.error(f"❌ {exc}")
                    else:
                        st.error("Không thể kết nối Backend API.")
            with col_resend:
                if st.button("← Gửi lại OTP", use_container_width=True, key="btn_lp_resend_otp"):
                    st.session_state.pop("lp_otp_sent", None)
                    st.rerun()

# =============================================================================
# COMPONENT — SIDEBAR ĐIỀU HƯỚNG
# =============================================================================
def render_sidebar() -> str:
    """
    Vẽ sidebar với option_menu (streamlit-option-menu).
    Trả về tên menu hiện tại đang được chọn.
    """
    role = _role()

    with st.sidebar:
        # ── Logo ──────────────────────────────────────────────────────────────
        st.markdown(f"""
        <div class="sidebar-logo">
          <div class="sidebar-logo-title">💊 MedLink AI</div>
          <div class="sidebar-logo-sub">FuzzyGCN · Drug–Disease AI</div>
        </div>
        <div class="neon-hr"></div>
        """, unsafe_allow_html=True)

        # ── Thông পুরা tin người dùng ───────────────────────────────────────────────
        if role != "guest":
            username  = st.session_state.get("username", "Demo User")
            role_icon = ROLE_ICONS[role]
            role_lbl  = ROLE_LABELS[role]
            role_cls  = ROLE_CLASSES[role]
            st.markdown(f"""
            <div style="display:flex;align-items:center;gap:0.7rem;padding:0.6rem 0;">
              <div style="width:36px;height:36px;border-radius:50%;
                          background:linear-gradient(135deg,#00f5d4,#00b4d8);
                          display:flex;align-items:center;justify-content:center;
                          font-size:1rem;box-shadow:0 0 12px rgba(0,245,212,0.4);">
                {role_icon}
              </div>
              <div>
                <div style="font-size:0.88rem;font-weight:700;color:#e2e8f0;">{username}</div>
                <span class="role-badge {role_cls}">{role_lbl}</span>
              </div>
            </div>
            <div class="neon-hr"></div>
            """, unsafe_allow_html=True)

        # ── Xây dựng danh sách menu theo quyền ────────────────────────────────
        # Tất cả các role đều thấy: Tổng quan, Tra cứu
        menu_items   = ["🏠 Tổng quan", "📚 Tra cứu"]
        menu_icons   = ["house-fill", "search"]

        if _can("user"):     # User, Expert, Admin
            menu_items  += ["⚗️ Trạm Dự Đoán"]
            menu_icons  += ["activity"]
        menu_items      += ["🌐 Lưới Sinh Học"]
        menu_icons      += ["diagram-3-fill"]

        if _can("expert"):   # Expert, Admin
            menu_items  += ["📊 So Sánh Model"]
            menu_icons  += ["bar-chart-line-fill"]

        if _can("expert"):   # Expert, Admin
            menu_items  += ["✅ Duyệt Liên Kết"]
            menu_icons  += ["check2-circle"]

        if _can("admin"):    # Admin only
            menu_items  += ["⚙️ Cấu Hình & Metrics", "👥 Quản Lý Tài Khoản"]
            menu_icons  += ["sliders", "people-fill"]

        # ── option_menu (streamlit-option-menu) ───────────────────────────────
        if _MENU_OK:
            selected = option_menu(
                menu_title=None,
                options=menu_items,
                icons=menu_icons,
                default_index=0,
                key="sidebar_menu",
                styles={
                    "container": {
                        "padding": "0", "background": "transparent",
                    },
                    "icon": {
                        "color": "#00f5d4", "font-size": "0.9rem",
                    },
                    "nav-link": {
                        "font-size": "0.86rem", "font-weight": "600",
                        "color": "#94a3b8",
                        "padding": "0.55rem 0.8rem",
                        "border-radius": "10px",
                        "--hover-color": "rgba(0,245,212,0.1)",
                    },
                    "nav-link-selected": {
                        "background": "rgba(0,245,212,0.15)",
                        "color": "#00f5d4",
                        "box-shadow": "0 0 15px rgba(0,245,212,0.2)",
                        "border": "1px solid rgba(0,245,212,0.3)",
                    },
                },
            )
        else:
            # Fallback nếu streamlit-option-menu chưa cài
            st.markdown("""
            <style>
            div[data-testid="stRadio"] label > div:first-child,
            div[data-testid="stRadio"] div[role="radio"],
            div[data-testid="stRadio"] span[data-baseweb="radio"] > div {
                border-radius: 4px !important;
            }
            div[data-testid="stRadio"] label {
                padding: 0.3rem 0;
            }
            </style>
            """, unsafe_allow_html=True)
            selected = st.radio(
                "Menu",
                menu_items,
                key="sidebar_menu_fallback",
                label_visibility="collapsed",
            )

        st.markdown("<div class='neon-hr'></div>", unsafe_allow_html=True)

        # ── Nút đăng xuất ─────────────────────────────────────────────────────
        if role == "guest":
            if st.button("🔑 Đăng nhập / Đăng ký", use_container_width=True, key="btn_login_sidebar"):
                render_login_dialog()
        else:
            if st.button("🚪 Đăng xuất", use_container_width=True, key="btn_signout"):
                for k in ["demo_role", "username", "sidebar_menu", "sidebar_menu_fallback",
                          "guest_workspace", "pred_results", "pred_query_label", "api_token",
                          "review_statuses", "saved_config"]:
                    st.session_state.pop(k, None)
                _clear_prediction_history_cache()
                HISTORY_RECORDS.clear()
                # Xóa token khỏi URL
                st.query_params.clear()
                st.rerun()



        # ── Footer sidebar ─────────────────────────────────────────────────────
        st.markdown("""
        <div style="font-size:0.68rem;color:#1e293b;text-align:center;
                    margin-top:1.2rem;padding-top:0.6rem;
                    border-top:1px solid rgba(255,255,255,0.05);">
          MedLink AI v2.0 · FuzzyGCN<br>
          <span style="color:#0f172a;">Drug–Disease Intelligence</span>
        </div>
        """, unsafe_allow_html=True)

    return str(selected)


# =============================================================================
# TRANG: TỔNG QUAN (tất cả role xem được)
# =============================================================================
def render_intro_page() -> None:
    """Trang tổng quan về hệ thống FuzzyGCN."""
    st.markdown('<div class="page-title fade-in">🏠 Tổng quan hệ thống</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-subtitle">MedLink AI — Nền tảng dự đoán liên kết Thuốc–Bệnh bằng FuzzyGCN</div>',
                unsafe_allow_html=True)

    # Thẻ tổng quan
    cols = st.columns(4)
    metrics = [
        ("1,373", "Thuốc", "+12 mới", "#00f5d4"),
        ("5,603", "Bệnh",  "+8 mới",  "#00b4d8"),
        ("13,384","Protein","—",      "#a78bfa"),
        ("96.3%", "AUC ROC","↑ 2.1%", "#f72585"),
    ]
    for i, (val, lbl, delta, color) in enumerate(metrics):
        with cols[i]:
            delta_color = "#4ade80" if "+" in delta or "↑" in delta else "#94a3b8"
            st.markdown(f"""
            <div class="metric-card fade-in" style="border-color:rgba({
              '0,245,212' if color=='#00f5d4' else
              '0,180,216' if color=='#00b4d8' else
              '124,58,237' if color=='#a78bfa' else
              '247,37,133'
            },0.3);">
              <div class="metric-value" style="color:{color};
                text-shadow:0 0 20px {color}66;">{val}</div>
              <div class="metric-label">{lbl}</div>
              <div class="metric-delta" style="color:{delta_color};">{delta}</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("<div style='height:2rem'></div>", unsafe_allow_html=True)

    # 1. Bảng 1: Dataset Summary
    st.markdown("""
    <div style="font-size:1.3rem;font-weight:800;color:#00f5d4;margin-bottom:1rem;text-shadow:0 0 10px rgba(0,245,212,0.3);">
      📊 1. Thông số các tập dữ liệu (Dataset Summary)
    </div>
    """, unsafe_allow_html=True)
    
    df_dataset = pd.DataFrame({
        "Dataset": ["B-dataset", "C-dataset", "F-dataset"],
        "Drugs": [269, 663, 593],
        "Diseases": [598, 409, 313],
        "Proteins": [1021, 993, 2741],
        "Drug-disease associations": [18416, 2532, 1933],
        "Drug-protein associations": [3110, 3773, 3243],
        "Disease-protein associations": [5898, 10734, 54265],
        "Sparsity": [0.1144, 0.0093, 0.0104]
    })
    st.dataframe(df_dataset, use_container_width=True, hide_index=True)
    
    st.markdown("<div style='font-size:0.95rem; color:#94a3b8; margin-top:1.5rem; margin-bottom:0.8rem; font-weight:600;'>📉 Biểu đồ so sánh số lượng Thuốc, Bệnh và Protein:</div>", unsafe_allow_html=True)
    df_dataset_chart = df_dataset[["Dataset", "Drugs", "Diseases", "Proteins"]].set_index("Dataset")
    st.bar_chart(df_dataset_chart, use_container_width=True, height=350)


    st.markdown("<div style='height:2.5rem'></div>", unsafe_allow_html=True)

    # 2. Bảng 2: Model Metrics
    st.markdown("""
    <div style="font-size:1.3rem;font-weight:800;color:#00b4d8;margin-bottom:1rem;text-shadow:0 0 10px rgba(0,180,216,0.3);">
      📈 2. Hiệu suất mô hình (10-Fold CV Metrics)
    </div>
    """, unsafe_allow_html=True)

    df_metrics = pd.DataFrame({
        "Dataset": ["B-dataset", "C-dataset", "F-dataset"],
        "Folds": [10, 10, 10],
        "AUC": ["0.9114 ± 0.0055", "0.9798 ± 0.0063", "0.9742 ± 0.0061"],
        "AUPR": ["0.9037 ± 0.0072", "0.9696 ± 0.0078", "0.9565 ± 0.0130"],
        "Accuracy": ["0.8207 ± 0.0053", "0.8796 ± 0.0136", "0.8897 ± 0.0114"],
        "Precision": ["0.7723 ± 0.0061", "0.7755 ± 0.0190", "0.7947 ± 0.0180"],
        "Recall": ["0.9098 ± 0.0066", "0.9846 ± 0.0086", "0.9775 ± 0.0079"],
        "F1": ["0.8354 ± 0.0046", "0.8675 ± 0.0136", "0.8765 ± 0.0115"],
        "MCC": ["0.6519 ± 0.0103", "0.7784 ± 0.0237", "0.7927 ± 0.0195"]
    })
    st.dataframe(df_metrics, use_container_width=True, hide_index=True)

    st.markdown("<div style='font-size:0.95rem; color:#94a3b8; margin-top:1.5rem; margin-bottom:0.8rem; font-weight:600;'>📉 Biểu đồ so sánh AUC, Accuracy và F1 Score:</div>", unsafe_allow_html=True)
    df_metrics_chart = pd.DataFrame({
        "Dataset": ["B-dataset", "C-dataset", "F-dataset"],
        "AUC": [0.9114, 0.9798, 0.9742],
        "Accuracy": [0.8207, 0.8796, 0.8897],
        "F1": [0.8354, 0.8675, 0.8765]
    }).set_index("Dataset")
    st.bar_chart(df_metrics_chart, use_container_width=True, height=350)

    st.markdown("<div style='height:2.5rem'></div>", unsafe_allow_html=True)

    # Thẻ mô tả (FuzzyGCN + Phân quyền)
    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("""
        <div class="glass-card fade-in">
          <div style="font-size:1.1rem;font-weight:800;color:#a78bfa;margin-bottom:0.8rem;">
            🧠 Về FuzzyGCN
          </div>
          <p style="color:#94a3b8;font-size:0.88rem;line-height:1.75;margin:0;">
            FuzzyGCN là mô hình kết hợp <strong style="color:#e2e8f0;">Graph Convolutional Network</strong>
            và <strong style="color:#e2e8f0;">Fuzzy Logic</strong> để mô hình hóa tính không chắc chắn
            trong dữ liệu sinh học. Mô hình học được biểu diễn đặc trưng
            từ đồ thị 3 loại nút: Thuốc, Bệnh và Protein.
          </p>
          <ul style="color:#64748b;font-size:0.85rem;line-height:2;margin-top:0.8rem;padding-left:1.2rem;">
            <li>Dataset B, C, F (Gottlieb, HDVD, FDataset)</li>
            <li>GIP Kernel similarity, ESM protein embeddings</li>
            <li>Mol2Vec molecular fingerprints</li>
          </ul>
        </div>
        """, unsafe_allow_html=True)

    with col_b:
        st.markdown("""
        <div class="glass-card fade-in">
          <div style="font-size:1.1rem;font-weight:800;color:#f72585;margin-bottom:0.8rem;">
            🔐 Phân quyền hệ thống
          </div>
          <div style="display:flex;flex-direction:column;gap:0.6rem;">
            <div style="display:flex;align-items:center;gap:0.7rem;padding:0.5rem 0.7rem;
                        background:rgba(148,163,184,0.06);border-radius:8px;">
              <span class="role-badge role-guest">👤 Khách</span>
              <span style="color:#64748b;font-size:0.82rem;">Xem Tổng quan & Tra cứu danh mục</span>
            </div>
            <div style="display:flex;align-items:center;gap:0.7rem;padding:0.5rem 0.7rem;
                        background:rgba(0,180,216,0.06);border-radius:8px;">
              <span class="role-badge role-user">🩺 Bác sĩ</span>
              <span style="color:#64748b;font-size:0.82rem;">+ AI Dự đoán & Lịch sử cá nhân</span>
            </div>
            <div style="display:flex;align-items:center;gap:0.7rem;padding:0.5rem 0.7rem;
                        background:rgba(124,58,237,0.06);border-radius:8px;">
              <span class="role-badge role-expert">🔬 Chuyên gia</span>
              <span style="color:#64748b;font-size:0.82rem;">+ Duyệt & xác nhận liên kết mới</span>
            </div>
            <div style="display:flex;align-items:center;gap:0.7rem;padding:0.5rem 0.7rem;
                        background:rgba(247,37,133,0.06);border-radius:8px;">
              <span class="role-badge role-admin">👑 Admin</span>
              <span style="color:#64748b;font-size:0.82rem;">Toàn quyền + Cấu hình mô hình</span>
            </div>
          </div>
        </div>
        """, unsafe_allow_html=True)


# =============================================================================
# TRANG: TRA CỨU DANH MỤC (tất cả role xem được)
# =============================================================================
def render_catalog_page() -> None:
    """Trang tra cứu danh mục thuốc và bệnh."""
    st.markdown('<div class="page-title fade-in">📚 Tra cứu danh mục</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-subtitle">Tìm kiếm thông tin thuốc, bệnh và protein trong cơ sở dữ liệu thực</div>',
                unsafe_allow_html=True)

    _DS_OPTIONS_CAT = ["B-dataset", "C-dataset", "F-dataset"]
    _DS_KEY_CAT = {"B-dataset": "b", "C-dataset": "c", "F-dataset": "f"}

    col_cat_ds, _, _ = st.columns([1.5, 1, 1.5])
    with col_cat_ds:
        cat_dataset = st.selectbox("📂 Chọn Dataset", _DS_OPTIONS_CAT, key="cat_dataset")
    cat_key = _DS_KEY_CAT[cat_dataset]

    _ROOT_CAT = Path(__file__).parent.parent / "data"

    @st.cache_data(ttl=300)
    def _load_catalog_data(ds_key: str, entity: str):
        try:
            with open(_ROOT_CAT / f"{entity}_{ds_key}.json", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []

    drugs_data = _load_catalog_data(cat_key, "thuoc")
    diseases_data = _load_catalog_data(cat_key, "benh")
    proteins_data = _load_catalog_data(cat_key, "protein")

    tab_drug, tab_disease, tab_protein = st.tabs([f"💊 Thuốc ({len(drugs_data)})", f"🦠 Bệnh ({len(diseases_data)})", f"🧬 Protein ({len(proteins_data)})"])

    with tab_drug:
        search_drug = st.text_input("🔍 Tìm kiếm thuốc", placeholder="Nhập tên thuốc...",
                                     key="catalog_drug_search").lower()
        filtered = [d for d in drugs_data if not search_drug or search_drug in d.get("name", "").lower()]
        
        df_drug = pd.DataFrame({
            "ID (Local)": [d.get("local_id") for d in filtered],
            "Tên thuốc": [d.get("name") for d in filtered],
            "Mã ngoài (External)": [d.get("external_id") for d in filtered],
            "SMILES": [d.get("smiles") for d in filtered],
        }) if filtered else pd.DataFrame(columns=["ID (Local)", "Tên thuốc", "Mã ngoài (External)", "SMILES"])
        st.dataframe(df_drug, use_container_width=True, hide_index=True)

    with tab_disease:
        search_dis = st.text_input("🔍 Tìm kiếm bệnh", placeholder="Nhập tên bệnh...",
                                    key="catalog_disease_search").lower()
        filtered_d = [d for d in diseases_data if not search_dis or search_dis in d.get("name", "").lower()]
        
        df_disease = pd.DataFrame({
            "ID (Local)": [d.get("local_id") for d in filtered_d],
            "Tên bệnh": [d.get("name") for d in filtered_d],
        }) if filtered_d else pd.DataFrame(columns=["ID (Local)", "Tên bệnh"])
        st.dataframe(df_disease, use_container_width=True, hide_index=True)

    with tab_protein:
        search_prot = st.text_input("🔍 Tìm kiếm protein", placeholder="Nhập tên/accession protein...",
                                     key="catalog_protein_search").lower()
        filtered_p = [p for p in proteins_data if not search_prot or search_prot in p.get("accession", "").lower() or search_prot in p.get("name", "").lower()]
        
        df_prot = pd.DataFrame({
            "ID (Local)": [p.get("local_id") for p in filtered_p],
            "Accession": [p.get("accession") for p in filtered_p],
            "Tên": [p.get("name") for p in filtered_p],
            "Gene": [p.get("gene") for p in filtered_p],
            "Trình tự (Sequence)": [p.get("sequence", "")[:50] + "..." if len(p.get("sequence", "")) > 50 else p.get("sequence") for p in filtered_p],
        }) if filtered_p else pd.DataFrame(columns=["ID (Local)", "Accession", "Tên", "Gene", "Trình tự (Sequence)"])
        st.dataframe(df_prot, use_container_width=True, hide_index=True)


# =============================================================================
# TRANG: TRẠM DỰ ĐOÁN (User, Expert, Admin)
# =============================================================================
# =============================================================================
# HELPER — Cấu trúc phân tử thuốc (rdkit server-side SVG)
# =============================================================================

try:
    from rdkit import Chem
    from rdkit.Chem.Draw import rdMolDraw2D
    from rdkit.Chem import AllChem
    _RDKIT_OK = True
except ImportError:
    _RDKIT_OK = False


def _smiles_to_svg(smiles: str, width: int = 220, height: int = 160) -> str:
    """Dùng rdkit tạo SVG từ SMILES. Trả '' nếu thất bại."""
    if not _RDKIT_OK:
        return ""
    try:
        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            return ""
        drawer = rdMolDraw2D.MolDraw2DSVG(width, height)
        opts = drawer.drawOptions()
        opts.clearBackground = True
        opts.backgroundColour = (0.067, 0.11, 0.157, 1.0)   # #111827
        opts.bondLineWidth = 1.8
        drawer.DrawMolecule(mol)
        drawer.FinishDrawing()
        svg = drawer.GetDrawingText()
        # Xoá dòng XML header để nhúng inline
        svg = svg.replace("<?xml version='1.0' encoding='iso-8859-1'?>", "").strip()
        return svg
    except Exception:
        return ""



def _smiles_to_3d_mol(smiles: str) -> str:
    if not _RDKIT_OK:
        return ""
    try:
        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            return ""
        mol = Chem.AddHs(mol)
        res = AllChem.EmbedMolecule(mol, randomSeed=42)
        if res == 0:
            AllChem.MMFFOptimizeMolecule(mol)
            return Chem.MolToMolBlock(mol)
    except Exception:
        pass
    return ""

def _build_mol_html(drug_smiles: list[tuple[str, str, str]]) -> str:
    """
    Tạo HTML hiển thị cấu trúc phân tử cho nhiều thuốc.
    Tích hợp 3Dmol.js: hiển thị SVG 2D, khi click sẽ mở popup 3D nhảy ra giữa màn hình.
    """
    if not drug_smiles:
        return ""

    import json
    cards_html = ""
    mol_3d_data = {}

    for i, (name, smiles, color) in enumerate(drug_smiles):
        mol_id = f"mol_{i}"
        
        # Cố gắng tạo 3D molBlock, nếu có thì bật cờ 3d_ok
        mol_block = _smiles_to_3d_mol(smiles)
        has_3d = False
        if mol_block:
            mol_3d_data[mol_id] = mol_block
            has_3d = True

        svg = _smiles_to_svg(smiles)
        smiles_preview = smiles[:44] + ("…" if len(smiles) > 44 else "")
        
        if svg:
            # Gắn sự kiện click nếu có 3D
            onclick_str = f"onclick=\"openModal('{mol_id}', '{name}')\"" if has_3d else ""
            cursor_str = "cursor:pointer;" if has_3d else ""
            overlay = '<div class="mol-3d-badge">🌐 3D</div>' if has_3d else ""
            
            mol_content = f'<div class="mol-svg" style="{cursor_str}position:relative;" {onclick_str}>{svg}{overlay}</div>'
        else:
            mol_content = (
                f'<div class="mol-svg mol-svg-err">'
                f'<span style="color:#475569;font-size:0.75rem;">⚠️ Không thể render<br>'
                f'<span style="font-size:0.60rem;font-family:monospace;">{smiles_preview}</span></span>'
                f'</div>'
            )
            
        cards_html += f"""
      <div class="mol-card" style="border-color:{color}70;">
        <div class="mol-name" style="color:{color};">{name}</div>
        {mol_content}
        <div class="mol-smiles" title="{smiles}">{smiles_preview}</div>
      </div>"""

    mol_data_json = json.dumps(mol_3d_data)

    return f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<script src="https://3Dmol.csb.pitt.edu/build/3Dmol-min.js"></script>
<style>
*{{box-sizing:border-box;margin:0;padding:0;}}
body{{background:#0d1b2a;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;padding:12px 16px;}}
.mol-grid{{display:flex;flex-wrap:wrap;gap:16px;}}
.mol-card{{background:rgba(255,255,255,0.05);border:1.5px solid;border-radius:12px;padding:10px 12px;text-align:center;flex:0 0 auto;width:244px;transition:box-shadow .2s;}}
.mol-card:hover{{box-shadow:0 0 18px rgba(0,245,212,0.22);}}
.mol-name{{font-size:0.85rem;font-weight:800;margin-bottom:6px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}}
.mol-svg{{width:220px;height:160px;border-radius:8px;overflow:hidden;display:flex;align-items:center;justify-content:center;background:#111827;transition:transform 0.2s;}}
.mol-svg:hover{{transform:scale(1.02);}}
.mol-svg svg{{width:220px;height:160px;}}
.mol-3d-badge{{position:absolute;bottom:4px;right:4px;background:rgba(0,245,212,0.8);color:#000;font-size:10px;padding:2px 6px;border-radius:4px;font-weight:bold;}}
.mol-svg-err{{font-size:0.75rem;color:#475569;padding:0.5rem;}}
.mol-smiles{{font-size:0.59rem;color:#475569;margin-top:5px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-family:monospace;}}

/* Modal Styles */
#molModal {{
    display: none; position: fixed; z-index: 9999; left: 0; top: 0; width: 100vw; height: 100vh;
    background-color: rgba(0,0,0,0.85); flex-direction: column; align-items: center; justify-content: center;
    opacity: 0; transition: opacity 0.3s ease;
}}
#molModal.show {{ opacity: 1; }}
.modal-content {{
    width: 85vw; height: 85vh; background: #0a101a; border-radius: 12px; border: 2px solid #00f5d4;
    display: flex; flex-direction: column; overflow: hidden; transform: scale(0.9); transition: transform 0.3s ease;
    box-shadow: 0 0 30px rgba(0,245,212,0.3);
}}
#molModal.show .modal-content {{ transform: scale(1); }}
.modal-header {{
    padding: 12px 20px; background: #111827; display: flex; justify-content: space-between; align-items: center;
    color: white; font-weight: bold; font-size: 1.2rem; border-bottom: 1px solid #1f2937;
}}
.close-btn {{ color: #ff4d6d; font-size: 28px; cursor: pointer; transition: color 0.2s; line-height: 1; }}
.close-btn:hover {{ color: #ff003c; }}
#modalViewer {{ flex: 1; position: relative; width: 100%; height: 100%; }}
</style></head><body>

<div class="mol-grid">{cards_html}</div>

<!-- 3D Modal -->
<div id="molModal">
    <div class="modal-content">
        <div class="modal-header">
            <span id="modalTitle">Molecule 3D</span>
            <span class="close-btn" onclick="closeModal()">&times;</span>
        </div>
        <div id="modalViewer"></div>
    </div>
</div>

<script>
const molData = {mol_data_json};
let viewer = null;

function openModal(mol_id, name) {{
    document.getElementById("modalTitle").innerText = name + " (Interactive 3D)";
    let modal = document.getElementById("molModal");
    modal.style.display = "flex";
    // Trigger reflow for animation
    void modal.offsetWidth; 
    modal.classList.add("show");
    
    let viewerDiv = document.getElementById("modalViewer");
    viewerDiv.innerHTML = "";
    
    viewer = $3Dmol.createViewer(viewerDiv, {{backgroundColor: '#0a101a'}});
    viewer.addModel(molData[mol_id], "sdf");
    viewer.setStyle({{}}, {{stick: {{radius: 0.15}}, sphere: {{radius: 0.4}}}});
    viewer.zoomTo();
    viewer.render();
}}

function closeModal() {{
    let modal = document.getElementById("molModal");
    modal.classList.remove("show");
    setTimeout(() => {{
        modal.style.display = "none";
        if(viewer) {{ viewer.clear(); viewer = null; }}
    }}, 300);
}}

// Close when clicking outside content
document.getElementById("molModal").addEventListener("click", function(e) {{
    if(e.target === this) closeModal();
}});
</script>

</body></html>"""


# =============================================================================
# HELPER — Bipartite diagram (thuốc/bệnh ← đường cong SVG → kết quả)
# =============================================================================

def _build_bipartite_html(
    sources: list[str],
    results_per_source: list[list[dict]],
    top_n: int,
    is_drug_mode: bool,
) -> str:
    """
    Tạo bipartite diagram thuần HTML/SVG/JS:
      Trái = node nguồn (thuốc hoặc bệnh) mỗi màu riêng
      Phải = kết quả dự đoán (bệnh hoặc thuốc)
      Giữa = đường cong bezier nối, màu theo node nguồn
    """
    src_header = "THUỐC ĐÃ CHỌN" if is_drug_mode else "BỆNH ĐÃ CHỌN"
    dst_header = "BỆNH LIÊN QUAN" if is_drug_mode else "THUỐC LIÊN QUAN"
    src_emoji  = "💊" if is_drug_mode else "🦠"
    dst_emoji  = "🦠" if is_drug_mode else "💊"
    src_type   = "THUỐC" if is_drug_mode else "BỆNH"

    # --- Tập hợp node đích theo thứ tự xuất hiện ----------------------------
    dst_order: list[str] = []
    dst_seen: set[str]   = set()
    connections: list[dict] = []

    for s_idx, res_list in enumerate(results_per_source):
        c_hex = _SRC_COLORS[s_idx % len(_SRC_COLORS)]["border"]
        for r in res_list[:top_n]:
            dst_name = r["name"]
            if dst_name not in dst_seen:
                dst_seen.add(dst_name)
                dst_order.append(dst_name)
            d_idx = dst_order.index(dst_name)
            connections.append({
                "src": s_idx,
                "dst": d_idx,
                "score": r["score"],
                "known": r["known"],
                "color": c_hex,
                "width": round(max(1.5, r["score"] * 3.5), 1),
            })

    # Trạng thái badge cho mỗi node đích (lấy theo lần xuất hiện đầu)
    dst_known: dict[int, bool] = {}
    dst_dot_color: dict[int, str] = {}
    for conn in connections:
        d = conn["dst"]
        if d not in dst_known:
            dst_known[d] = conn["known"]
            dst_dot_color[d] = conn["color"]

    # --- HTML các box nguồn --------------------------------------------------
    src_boxes_html = ""
    for s_idx, src_name in enumerate(sources):
        c = _SRC_COLORS[s_idx % len(_SRC_COLORS)]
        src_boxes_html += f"""
        <div class="src-node" id="src-{s_idx}"
             style="border-color:{c['border']};">
          <div class="src-label"
               style="color:{c['border']};">{src_emoji} {src_type} {s_idx+1} · ID {s_idx+1}</div>
          <div class="src-name">{src_name}</div>
        </div>"""

    # --- HTML các hàng đích --------------------------------------------------
    dst_rows_html = ""
    for d_idx, dst_name in enumerate(dst_order):
        dot_c  = dst_dot_color.get(d_idx, "#00b4d8")
        is_k   = dst_known.get(d_idx, False)
        badge  = ('<span class="badge-known">✅ Đã biết</span>'
                  if is_k else
                  '<span class="badge-pred">🔬 Dự đoán</span>')
        dst_rows_html += f"""
        <div class="dst-node" id="dst-{d_idx}">
          <div class="dst-dot" style="background:{dot_c};box-shadow:0 0 5px {dot_c}88;"></div>
          <div class="dst-content">
            <div class="dst-name-row">{badge}<span class="dst-name">{dst_name}</span></div>
            <div class="dst-bar" style="background:linear-gradient(90deg,{dot_c}44,transparent);"></div>
          </div>
        </div>"""

    # --- JS connections array ------------------------------------------------
    conn_js = "[" + ",".join(
        f'{{"src":{c["src"]},"dst":{c["dst"]},"color":"{c["color"]}","width":{c["width"]}}}'
        for c in connections
    ) + "]"

    # Ước tính chiều cao cần thiết cho iframe
    n_left  = len(sources)
    n_right = len(dst_order)
    est_h   = max(n_left * 88 + 70, n_right * 54 + 70) + 60

    return f"""<!DOCTYPE html><html><head><meta charset="utf-8"><style>
*{{box-sizing:border-box;margin:0;padding:0;}}
body{{background:#0d1b2a;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;
  padding:16px 20px;overflow-x:hidden;}}
#root{{position:relative;display:flex;align-items:flex-start;gap:0;}}
.panel-header{{font-size:0.68rem;font-weight:800;letter-spacing:0.1em;
  color:#475569;text-transform:uppercase;margin-bottom:10px;}}
#left-panel{{width:230px;flex-shrink:0;position:relative;z-index:2;}}
#mid-gap{{width:120px;flex-shrink:0;position:relative;z-index:0;}}
#right-panel{{flex:1;min-width:260px;position:relative;z-index:2;}}
#svg-layer{{position:absolute;top:0;left:0;width:100%;height:100%;
  pointer-events:none;overflow:visible;z-index:1;}}
.src-node{{border:1.5px solid;border-radius:8px;padding:10px 14px;
  margin-bottom:14px;background:rgba(255,255,255,0.04);transition:box-shadow .2s;}}
.src-node:hover{{box-shadow:0 0 14px rgba(255,255,255,0.15);}}
.src-label{{font-size:0.64rem;font-weight:700;text-transform:uppercase;
  letter-spacing:0.07em;margin-bottom:4px;}}
.src-name{{font-size:0.95rem;font-weight:800;color:#e2e8f0;padding-bottom:2px;}}
.dst-node{{display:flex;align-items:center;gap:8px;margin-bottom:12px;min-height:32px;}}
.dst-dot{{width:10px;height:10px;border-radius:50%;flex-shrink:0;}}
.dst-content{{flex:1;min-width:0;}}
.dst-name-row{{display:flex;align-items:center;gap:6px;margin-bottom:4px;flex-wrap:wrap;}}
.dst-name{{font-size:0.88rem;font-weight:600;color:#e2e8f0;}}
.dst-bar{{height:2px;border-radius:2px;width:100%;}}
.badge-known{{font-size:0.62rem;padding:1px 7px;border-radius:999px;white-space:nowrap;flex-shrink:0;
  background:rgba(74,222,128,.12);color:#4ade80;border:1px solid rgba(74,222,128,.4);}}
.badge-pred{{font-size:0.62rem;padding:1px 7px;border-radius:999px;white-space:nowrap;flex-shrink:0;
  background:rgba(0,180,216,.12);color:#00b4d8;border:1px solid rgba(0,180,216,.4);}}
</style></head><body>
<div id="root">
  <div id="left-panel">
    <div class="panel-header">{src_emoji} {src_header}</div>
    {src_boxes_html}
  </div>
  <div id="mid-gap"></div>
  <div id="right-panel">
    <div class="panel-header">{dst_emoji} {dst_header}</div>
    {dst_rows_html}
  </div>
  <svg id="svg-layer"></svg>
</div>
<script>
const conns = {conn_js};
function draw() {{
  const svg = document.getElementById('svg-layer');
  svg.innerHTML = '';
  const root = document.getElementById('root');
  const rootRect = root.getBoundingClientRect();
  svg.setAttribute('viewBox','0 0 '+rootRect.width+' '+rootRect.height);
  svg.setAttribute('width', rootRect.width);
  svg.setAttribute('height', rootRect.height);
  conns.forEach(c => {{
    const sEl = document.getElementById('src-'+c.src);
    const dEl = document.getElementById('dst-'+c.dst);
    if (!sEl || !dEl) return;
    const sR = sEl.getBoundingClientRect();
    const dR = dEl.getBoundingClientRect();
    const x1 = sR.right - rootRect.left;
    const y1 = sR.top - rootRect.top + sR.height / 2;
    const x2 = dR.left - rootRect.left;
    const y2 = dR.top - rootRect.top + dR.height / 2;
    const mx = (x1 + x2) / 2;
    const path = document.createElementNS('http://www.w3.org/2000/svg','path');
    path.setAttribute('d',`M ${{x1}} ${{y1}} C ${{mx}} ${{y1}}, ${{mx}} ${{y2}}, ${{x2}} ${{y2}}`);
    path.setAttribute('stroke', c.color);
    path.setAttribute('stroke-width', c.width);
    path.setAttribute('fill','none');
    path.setAttribute('opacity','0.72');
    svg.appendChild(path);
  }});
}}
if (document.readyState === 'loading') {{
  document.addEventListener('DOMContentLoaded', () => setTimeout(draw, 120));
}} else {{ setTimeout(draw, 120); }}
window.addEventListener('resize', () => {{ svg.innerHTML=''; draw(); }});
</script></body></html>""", est_h


# =============================================================================
# HELPER — Xây dựng đồ thị Pyvis kết quả dự đoán
# =============================================================================

# Bảng màu cho từng node nguồn (tối đa 5 màu)
_SRC_COLORS = [
    {"bg": "#0066ff", "border": "#00aaff", "hl_bg": "#3399ff"},  # xanh dương
    {"bg": "#7c3aed", "border": "#a855f7", "hl_bg": "#9333ea"},  # tím
    {"bg": "#0891b2", "border": "#22d3ee", "hl_bg": "#0e7490"},  # cyan
    {"bg": "#d97706", "border": "#fbbf24", "hl_bg": "#b45309"},  # cam
    {"bg": "#db2777", "border": "#f472b6", "hl_bg": "#be185d"},  # hồng
]

# Màu node đích cố định (bệnh = đỏ, thuốc = xanh lá)
_DST_DISEASE_COLOR = {"bg": "#ff3333", "border": "#ff6666", "hl_bg": "#ff5555"}
_DST_DRUG_COLOR    = {"bg": "#00cc66", "border": "#00ffaa", "hl_bg": "#00dd77"}


def _build_prediction_network(
    sources: list[str],
    results_per_source: list[list[dict]],
    top_n: int,
    mode_drug_to_disease: bool,
) -> str:
    """
    Tạo đồ thị Pyvis kết quả dự đoán và trả về chuỗi HTML.

    sources              : danh sách tên thuốc (hoặc bệnh) được chọn
    results_per_source   : mỗi phần tử là list kết quả Top-K cho source tương ứng
    top_n                : số kết quả tối đa hiển thị mỗi source
    mode_drug_to_disease : True = Thuốc→Bệnh, False = Bệnh→Thuốc
    """
    if not _PYVIS_OK:
        return "<p style='color:red'>pyvis chưa được cài đặt.</p>"

    net = PyvisNetwork(height="540px", width="100%", bgcolor="#0d1b2a", font_color="#e2e8f0")
    net.toggle_physics(True)
    net.set_options("""
    {
      "physics": {
        "barnesHut": {
          "gravitationalConstant": -9000,
          "centralGravity": 0.25,
          "springLength": 160,
          "springConstant": 0.04,
          "damping": 0.1,
          "avoidOverlap": 0.3
        },
        "minVelocity": 0.75
      },
      "interaction": {
        "hover": true,
        "tooltipDelay": 100,
        "navigationButtons": true,
        "keyboard": true
      },
      "nodes": { "borderWidth": 2, "borderWidthSelected": 4 },
      "edges": { "smooth": { "type": "dynamic" } }
    }
    """)

    # ── Thêm node nguồn (thuốc hoặc bệnh được chọn) ──────────────────────────
    src_shape = "square"    if mode_drug_to_disease else "dot"
    dst_shape = "dot"       if mode_drug_to_disease else "square"
    src_emoji = "💊"        if mode_drug_to_disease else "🦠"
    dst_emoji = "🦠"        if mode_drug_to_disease else "💊"
    src_type  = "Thuốc"     if mode_drug_to_disease else "Bệnh"
    dst_type  = "Bệnh"      if mode_drug_to_disease else "Thuốc"
    dst_color = _DST_DISEASE_COLOR if mode_drug_to_disease else _DST_DRUG_COLOR

    added_dst: dict[str, str] = {}   # tên → node_id của node đích đã thêm

    for s_idx, (src_name, results) in enumerate(zip(sources, results_per_source)):
        c = _SRC_COLORS[s_idx % len(_SRC_COLORS)]
        src_id = f"src_{s_idx}"
        net.add_node(
            n_id=src_id,
            label=src_name,
            shape=src_shape,
            color={
                "background": c["bg"],
                "border":     c["border"],
                "highlight":  {"background": c["hl_bg"], "border": "#00f5d4"},
                "hover":      {"background": c["hl_bg"], "border": "#00f5d4"},
            },
            size=28,
            title=f"{src_emoji} <b>{src_type}</b>: {src_name}",
            font={"color": "#ffffff", "size": 14, "bold": True},
            shadow=True,
        )

        # ── Thêm node đích và cạnh nối ────────────────────────────────────────
        top_results = sorted(results, key=lambda x: x["score"], reverse=True)[:top_n]
        for rank, r in enumerate(top_results):
            dst_name = r["name"]
            score    = r["score"]
            is_known = r["known"]

            # Tạo node đích nếu chưa có
            if dst_name not in added_dst:
                dst_id = f"dst_{len(added_dst)}"
                added_dst[dst_name] = dst_id
                edge_lbl_color = "#4ade80" if is_known else "#00b4d8"
                status_txt = "Đã biết ✅" if is_known else "Dự đoán 🔬"
                net.add_node(
                    n_id=dst_id,
                    label=dst_name,
                    shape=dst_shape,
                    color={
                        "background": dst_color["bg"],
                        "border":     dst_color["border"],
                        "highlight":  {"background": dst_color["hl_bg"], "border": "#00f5d4"},
                        "hover":      {"background": dst_color["hl_bg"], "border": "#00f5d4"},
                    },
                    size=22,
                    title=f"{dst_emoji} <b>{dst_type}</b>: {dst_name}<br>"
                          f"Xác suất cao nhất: {score:.3f}<br>Trạng thái: {status_txt}",
                    font={"color": "#ffffff", "size": 13},
                    shadow=True,
                )
            else:
                dst_id = added_dst[dst_name]

            # Màu cạnh theo từng node nguồn
            edge_color_hex = c["border"]
            edge_label     = f"{score:.2f}"
            net.add_edge(
                src_id, dst_id,
                value=score,
                title=f"{src_name} → {dst_name}<br>"
                      f"Xác suất: {score:.4f}<br>"
                      f"Rank: #{rank + 1}",
                label=edge_label,
                color={"color": edge_color_hex, "highlight": "#00f5d4", "hover": "#00f5d4"},
                width=max(1.5, score * 5),
                arrows="to",
                font={"color": edge_color_hex, "size": 10, "bold": True,
                      "strokeWidth": 2, "strokeColor": "#0d1b2a"},
            )

    # ── Lưu và trả về HTML ────────────────────────────────────────────────────
    with tempfile.NamedTemporaryFile(mode="w", suffix=".html",
                                     delete=False, encoding="utf-8") as f:
        net.save_graph(f.name)
        tmp_path = f.name
    with open(tmp_path, "r", encoding="utf-8") as f:
        html_str = f.read()
    try:
        os.unlink(tmp_path)
    except OSError:
        pass
    return html_str


def render_prediction_page() -> None:
    """
    Trạm Dự Đoán AI — FuzzyGCN.
    Cho phép chọn N thuốc (hoặc N bệnh), dự đoán và hiển thị
    kết quả dạng đồ thị Pyvis: node nguồn nối với Top-5 kết quả.
    """
    if not _can("user"):
        st.markdown("""
        <div class="access-denied fade-in">
          <div style="font-size:3rem;margin-bottom:0.8rem;">🚫</div>
          <div style="font-size:1.2rem;font-weight:800;margin-bottom:0.5rem;">
            Không có quyền truy cập</div>
          <div style="font-size:0.88rem;color:rgba(247,37,133,0.7);">
            Chức năng này yêu cầu vai trò <strong>Bác sĩ</strong> trở lên.<br>
            Vui lòng đăng nhập hoặc chuyển role ở cuối Sidebar.
          </div>
        </div>
        """, unsafe_allow_html=True)
        return

    st.markdown('<div class="page-title fade-in">⚗️ Trạm Dự Đoán AI</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-subtitle">Chọn nhiều Thuốc / Bệnh — AI trả về liên kết dạng đồ thị trực quan</div>',
                unsafe_allow_html=True)

    # ── BẢNG ĐIỀU KHIỂN (cột trái) + ĐỒ THỊ KẾT QUẢ (cột phải) ─────────────
    col_ctrl, col_vis = st.columns([1, 2])

    with col_ctrl:
        st.markdown('<div class="glass-card" style="padding:1.4rem 1.6rem;">', unsafe_allow_html=True)

        # Dataset
        dataset = st.selectbox(
            "📂 Dataset",
            ["B-dataset", "C-dataset", "F-dataset"],
            key="pred_dataset",
        )

        # Loại truy vấn
        query_type = st.radio(
            "🔎 Chiều dự đoán",
            ["💊 Thuốc → Tìm Bệnh", "🦠 Bệnh → Tìm Thuốc"],
            key="pred_query_type",
            horizontal=False,
        )
        is_drug_mode = "Thuốc" in query_type

        st.markdown("<div class='neon-hr'></div>", unsafe_allow_html=True)

        # ── Load danh sách thuốc/bệnh theo dataset được chọn ─────────────────
        _DS_KEY = {"B-dataset": "b", "C-dataset": "c", "F-dataset": "f"}
        _ds_key = _DS_KEY.get(dataset, "b")
        _ROOT   = Path(__file__).parent.parent / "data"

        def _load_names(fname: str, fallback: list[str]) -> list[str]:
            try:
                with open(_ROOT / fname, encoding="utf-8") as _f:
                    return [r["name"] for r in json.load(_f) if r.get("name")]
            except Exception:
                return fallback

        def _load_smiles_map(fname: str) -> dict[str, str]:
            """Trả về dict {name: smiles} từ file JSON thuốc."""
            try:
                with open(_ROOT / fname, encoding="utf-8") as _f:
                    return {r["name"]: r.get("smiles", "") for r in json.load(_f) if r.get("name")}
            except Exception:
                return {}

        _drug_pool    = _load_names(f"thuoc_{_ds_key}.json", SAMPLE_DRUGS)
        _disease_pool = _load_names(f"benh_{_ds_key}.json",  SAMPLE_DISEASES)
        _smiles_map   = _load_smiles_map(f"thuoc_{_ds_key}.json")

        # ── Chọn số lượng node nguồn ─────────────────────────────────────────
        src_label  = "Thuốc" if is_drug_mode else "Bệnh"
        src_pool   = _drug_pool if is_drug_mode else _disease_pool
        src_emoji  = "💊" if is_drug_mode else "🦠"

        n_src = st.number_input(
            f"🔢 Số {src_label} muốn so sánh (Không giới hạn)",
            min_value=1, value=1, step=1,
            key="pred_n_src",
            help="Mỗi node sẽ có màu đường nối riêng trên đồ thị.",
        )

        # Chọn từng tên
        st.markdown(
            f'<div style="font-size:0.75rem;color:#475569;font-weight:700;'
            f'text-transform:uppercase;letter-spacing:0.06em;margin:0.6rem 0 0.4rem;">'
            f'{src_emoji} Chọn tên {src_label}</div>',
            unsafe_allow_html=True,
        )
        selected_sources: list[str] = []
        for i in range(int(n_src)):
            c_hex = _SRC_COLORS[i % len(_SRC_COLORS)]["border"]
            st.markdown(
                f'<div style="height:3px;background:{c_hex};'
                f'border-radius:3px;margin-bottom:3px;"></div>',
                unsafe_allow_html=True,
            )
            nm = st.selectbox(
                f"{src_emoji} {src_label} {i + 1}",
                src_pool,
                index=min(i, len(src_pool) - 1),
                key=f"pred_src_{i}_{query_type}_{_ds_key}",
                label_visibility="collapsed",
            )
            selected_sources.append(nm)

        st.markdown("<div class='neon-hr'></div>", unsafe_allow_html=True)

        # ── Số kết quả hiển thị (không giới hạn) ─────────────────────────────
        top_n = st.number_input(
            "📊 Số kết quả hiển thị",
            min_value=1,
            max_value=10000,
            value=50,
            step=10,
            key="pred_top_n",
            help="Nhập số lượng kết quả muốn xem. Không giới hạn — có thể nhập số bất kỳ.",
        )
        top_n = int(top_n)

        # Tham số kỹ thuật (chỉ Admin)
        if _can("admin"):
            with st.expander("⚙️ Tham số kỹ thuật (Admin)"):
                st.slider("Ngưỡng xác suất tối thiểu", 0.0, 1.0, 0.3, 0.01, key="pred_threshold")
                st.slider("Fuzzy membership α", 0.1, 2.0, 1.0, 0.05, key="pred_alpha")
                st.toggle("Sử dụng ensemble", value=True, key="pred_ensemble")

        do_predict = st.button(
            "🚀 Dự đoán & Vẽ đồ thị",
            use_container_width=True, type="primary", key="btn_do_predict",
        )
        st.markdown("</div>", unsafe_allow_html=True)


    # ── CỘT PHẢI: đồ thị + bảng kết quả ────────────────────────────────────
    with col_vis:
        # Khi nhấn Dự đoán: sinh dữ liệu mẫu và lưu session
        if do_predict:
            # Loại bỏ trùng lặp, giữ thứ tự
            unique_src = list(dict.fromkeys(s for s in selected_sources if s))

            # Map dataset UI label -> API dataset key
            _DS_API_MAP = {
                "B-dataset": "B-dataset",
                "C-dataset": "C-dataset",
                "F-dataset": "F-dataset",
            }
            api_dataset = _DS_API_MAP.get(dataset, "B-dataset")
            threshold = st.session_state.get("pred_threshold", 0.3)

            results_per_src: list[list[dict]] = []

            if _API_OK:
                import logging
                _pred_log = logging.getLogger("MedLink_Frontend")
                if not _pred_log.handlers:
                    _h = logging.StreamHandler()
                    _h.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
                    _pred_log.addHandler(_h)
                _pred_log.setLevel(logging.INFO)

                client = ApiClient(API_DEFAULT)
                if st.session_state.get("api_token"):
                    client.token = st.session_state["api_token"]

                predict_ok = True
                for src_name in unique_src:
                    try:
                        if is_drug_mode:
                            _pred_log.info(f">>> [AI] Gọi predict drug→disease: '{src_name}', top_k={top_n}, dataset={api_dataset}")
                            res = client.predict_drug_to_disease(
                                name=src_name, top_k=top_n,
                                threshold=threshold, dataset=api_dataset,
                            )
                        else:
                            _pred_log.info(f">>> [AI] Gọi predict disease→drug: '{src_name}', top_k={top_n}, dataset={api_dataset}")
                            res = client.predict_disease_to_drug(
                                name=src_name, top_k=top_n,
                                threshold=threshold, dataset=api_dataset,
                            )
                        _pred_log.info(f"<<< [AI] Trả về {len(res.get('results', []))} kết quả cho '{src_name}'")

                        api_results = []
                        for item in res.get("results", []):
                            api_results.append({
                                "name":  item.get("name", item.get("disease_name", item.get("drug_name", "?"))),
                                "score": round(item.get("score", 0), 4),
                                "known": item.get("known", False),
                            })
                        api_results.sort(key=lambda x: x["score"], reverse=True)
                        results_per_src.append(api_results)
                    except Exception as e:
                        _pred_log.error(f"!!! [AI] Lỗi dự đoán cho '{src_name}': {e}")
                        st.error(f"Lỗi khi dự đoán cho '{src_name}': {e}")
                        predict_ok = False
                        results_per_src.append([])

            else:
                st.error("Không thể kết nối API Backend. Kiểm tra server FastAPI đã chạy chưa.")
                predict_ok = False
                for _ in unique_src:
                    results_per_src.append([])

            st.session_state["pred_sources"]         = unique_src
            st.session_state["pred_results_per_src"]  = results_per_src
            st.session_state["pred_is_drug_mode"]    = is_drug_mode
            st.session_state["pred_saved_top_n"]     = top_n
            st.session_state["pred_dataset_label"]   = dataset
            # Lưu SMILES cho mode thuốc
            if is_drug_mode:
                st.session_state["pred_src_smiles"] = {
                    nm: _smiles_map.get(nm, "") for nm in unique_src
                }
            else:
                st.session_state["pred_src_smiles"] = {}

            # Lưu lịch sử
            for src_name, res in zip(unique_src, results_per_src):
                HISTORY_RECORDS.append({
                    "Truy vấn": f"{'💊' if is_drug_mode else '🦠'} {src_name}",
                    "Chiều":    "Thuốc→Bệnh" if is_drug_mode else "Bệnh→Thuốc",
                    "Dataset":  dataset,
                    "Top score": res[0]["score"] if res else 0,
                })

        # Lấy dữ liệu từ session
        saved_src  = st.session_state.get("pred_sources", [])
        saved_res  = st.session_state.get("pred_results_per_src", [])
        saved_mode = st.session_state.get("pred_is_drug_mode", True)
        saved_topn = st.session_state.get("pred_saved_top_n", 5)
        saved_ds   = st.session_state.get("pred_dataset_label", dataset)

        if saved_src and saved_res:
            src_names_str = ", ".join(saved_src)
            dst_type_lbl = "Benh" if saved_mode else "Thuoc"
            unique_targets = len({r["name"] for res_list in saved_res for r in res_list})
            known_count = sum(1 for res_list in saved_res for r in res_list if r.get("known"))
            predicted_count = sum(1 for res_list in saved_res for r in res_list if not r.get("known"))

            st.markdown(f"""
            <div class="glass-card" style="padding:1rem 1.4rem;margin-bottom:0.8rem;border-color:rgba(0,245,212,0.2);">
              <div style="font-size:0.92rem;font-weight:800;color:#00f5d4;">Kết quả dự đoán Top-{saved_topn} {dst_type_lbl}</div>
              <div style="font-size:0.78rem;color:#475569;margin-top:0.25rem;">
                Nguồn: <strong style="color:#e2e8f0;">{src_names_str}</strong>
                &nbsp;|&nbsp; Dataset: {saved_ds}
              </div>
            </div>
            """, unsafe_allow_html=True)

            summary_cols = st.columns(4)
            for idx, (label, value, color) in enumerate([("Nguồn", len(saved_src), "#00f5d4"), ("Đích duy nhất", unique_targets, "#00b4d8"), ("Đã biết", known_count, "#4ade80"), ("AI dự đoán", predicted_count, "#fbbf24")]):
                with summary_cols[idx]:
                    st.markdown(f'<div class="metric-card" style="padding:1rem 0.9rem;"><div class="metric-value" style="font-size:1.8rem;color:{color};text-shadow:none;">{value}</div><div class="metric-label">{label}</div></div>', unsafe_allow_html=True)

            legend_html = '<div style="display:flex;flex-wrap:wrap;gap:0.5rem;margin:0.8rem 0 0.6rem;">'
            for i, src_nm in enumerate(saved_src):
                c = _SRC_COLORS[i % len(_SRC_COLORS)]
                legend_html += (
                    f'<div style="display:flex;align-items:center;gap:0.4rem;background:rgba(255,255,255,0.04);border:1px solid {c["border"]}33;border-radius:999px;padding:0.2rem 0.7rem;">'
                    f'<div style="width:10px;height:10px;border-radius:2px;background:{c["bg"]};"></div>'
                    f'<span style="font-size:0.78rem;color:#e2e8f0;font-weight:600;">{src_nm}</span></div>'
                )
            legend_html += "</div>"
            st.markdown(legend_html, unsafe_allow_html=True)

            result_tab_graph, result_tab_molecule, result_tab_table = st.tabs(["Đồ thị", "Phân tử", "Danh sách"])
            with result_tab_graph:
                bip_html, bip_h = _build_bipartite_html(sources=saved_src, results_per_source=saved_res, top_n=saved_topn, is_drug_mode=saved_mode)
                st.markdown('<div class="glass-card" style="padding:0.4rem;">', unsafe_allow_html=True)
                _html_iframe(bip_html, height=bip_h + 24, scrolling=False)
                st.markdown("</div>", unsafe_allow_html=True)

            saved_smiles: dict[str, str] = st.session_state.get("pred_src_smiles", {})
            if saved_mode:
                mol_entries = [(nm, saved_smiles.get(nm, ""), _SRC_COLORS[i % len(_SRC_COLORS)]["bg"]) for i, nm in enumerate(saved_src) if saved_smiles.get(nm)]
            else:
                mol_entries = []
                seen = set()
                for i, (_, res_list) in enumerate(zip(saved_src, saved_res)):
                    for r in res_list[:3]:
                        drug_nm = r["name"]
                        if drug_nm not in seen:
                            smiles_val = _smiles_map.get(drug_nm, "")
                            if smiles_val:
                                mol_entries.append((drug_nm, smiles_val, _SRC_COLORS[i % len(_SRC_COLORS)]["bg"]))
                                seen.add(drug_nm)

            with result_tab_molecule:
                if mol_entries:
                    mol_html = _build_mol_html(mol_entries)
                    mol_h = max(220, len(mol_entries) * 10 + 220)
                    st.markdown('<div class="glass-card" style="padding:0.6rem;">', unsafe_allow_html=True)
                    _html_iframe(mol_html, height=mol_h, scrolling=True)
                    st.markdown("</div>", unsafe_allow_html=True)
                else:
                    st.info("Không có cấu trúc phân tử phù hợp để hiển thị.")

            with result_tab_table:
                tab_objs = st.tabs([f"{'Thuốc' if saved_mode else 'Bệnh'} {s}" for s in saved_src])
                for tab_obj, (_, res_list) in zip(tab_objs, zip(saved_src, saved_res)):
                    with tab_obj:
                        for rank, r in enumerate(res_list):
                            score = r["score"]
                            bar_w = int(score * 100)
                            badge = ('<span class="badge-known">Đã biết</span>' if r["known"] else '<span class="badge-pred">Dự đoán</span>')
                            color = "#4ade80" if r["known"] else "#00b4d8"
                            st.markdown(f"""
                            <div style="display:flex;align-items:center;gap:0.8rem;padding:0.6rem 0.9rem;margin-bottom:0.35rem;background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.07);border-radius:10px;">
                              <div style="min-width:22px;font-size:0.74rem;color:#475569;font-weight:700;">#{rank + 1}</div>
                              <div style="flex:1;min-width:0;">
                                <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:0.28rem;">
                                  <span style="font-size:0.86rem;font-weight:700;color:#e2e8f0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;max-width:200px;">{r['name']}</span>
                                  {badge}
                                </div>
                                <div class="score-bar-bg"><div class="score-bar-fill" style="width:{bar_w}%;background:linear-gradient(90deg,{color},{color}88);box-shadow:0 0 8px {color}88;"></div></div>
                              </div>
                              <div style="min-width:46px;text-align:right;font-size:0.9rem;font-weight:800;color:{color};">{score:.3f}</div>
                            </div>
                            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div style="text-align:center;padding:5rem 2rem;color:#334155;">
              <div style="font-size:4rem;margin-bottom:1.2rem;filter:drop-shadow(0 0 20px rgba(0,245,212,0.3));">AI</div>
              <div style="font-size:1rem;font-weight:700;color:#475569;margin-bottom:0.5rem;">Chưa có kết quả</div>
              <div style="font-size:0.85rem;color:#334155;">Chọn thuốc hoặc bệnh ở cột bên trái rồi nhấn<br><strong style="color:#00f5d4;">Dự đoán &amp; Vẽ đồ thị</strong></div>
            </div>
            """, unsafe_allow_html=True)

    # ── Lịch sử dự đoán phiên hiện tại ───────────────────────────────────────
    if _can("user"):
        history_error = None
        history_rows: list[dict] = []
        if st.session_state.get("api_token") and _API_OK:
            try:
                history_rows = _load_prediction_history(force=True)
            except Exception as exc:  # noqa: BLE001
                history_error = str(exc)

        st.markdown("<div class='neon-hr'></div>", unsafe_allow_html=True)
        st.markdown(
            '<div style="font-size:0.9rem;font-weight:800;color:#94a3b8;margin-bottom:0.5rem;">'
            '🕑 Lịch sử dự đoán</div>',
            unsafe_allow_html=True,
        )

        if history_error:
            st.warning(f"Không tải được lịch sử từ máy chủ: {history_error}")
        elif history_rows:
            df_hist = _format_history_rows(history_rows[:50])
            st.dataframe(df_hist, use_container_width=True, hide_index=True)
        elif HISTORY_RECORDS:
            df_hist = pd.DataFrame(HISTORY_RECORDS[-15:])
            st.dataframe(df_hist, use_container_width=True, hide_index=True)
        else:
            st.info("Chưa có lịch sử dự đoán.")
# =============================================================================
# TRANG: LƯỚI SINH HỌC — PYVIS (tất cả role xem được)
# =============================================================================
def render_network_page() -> None:
    """
    Render đồ thị sinh học 15 nodes bằng pyvis:
      5 Thuốc (vuông, xanh dương), 5 Bệnh (tròn, đỏ), 5 Protein (tam giác, xanh lá).
    """
    st.markdown('<div class="page-title fade-in">🌐 Lưới Sinh Học</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-subtitle">Trực quan hóa mạng tương tác Thuốc – Bệnh – Protein</div>',
                unsafe_allow_html=True)

    if not _PYVIS_OK:
        st.error("""
        ❌ Thư viện **pyvis** chưa được cài đặt.
        Chạy lệnh: `pip install pyvis` rồi khởi động lại ứng dụng.
        """)
        return

    # ── Dataset selector ───────────────────────────────────────────────────────
    _DS_OPTIONS = ["B-dataset", "C-dataset", "F-dataset"]
    _DS_KEY_MAP = {"B-dataset": "b", "C-dataset": "c", "F-dataset": "f"}
    col_ds, col_seed, col_phys = st.columns([1.2, 1.2, 0.8])
    with col_ds:
        net_dataset = st.selectbox("📂 Dataset", _DS_OPTIONS, key="net_dataset")
    _ds_key = _DS_KEY_MAP[net_dataset]
    _ROOT_DATA = Path(__file__).parent.parent / "data"

    # ── Helper: dịch tên OMIM sang tiếng Việt ────────────────────────────────
    def _net_translate_disease(name: str) -> str:
        """Dịch mã OMIM (D102100) sang tên Tiếng Việt. Dataset B không bị ảnh hưởng."""
        n = str(name).strip()
        if n.upper().startswith("D") and n[1:].isdigit() and 5 <= len(n) <= 8:
            try:
                import sys as _sys
                _src_root = Path(__file__).resolve().parents[2]
                if str(_src_root) not in _sys.path:
                    _sys.path.insert(0, str(_src_root))
                from data.omim_viet_dict import get_viet_name
                viet = get_viet_name(n.upper())
                if viet != n:
                    return f"{viet} ({n})"
            except Exception:
                pass
        return n

    def _net_load(fname: str, field: str, fallback: list[str]) -> list[str]:
        try:
            with open(_ROOT_DATA / fname, encoding="utf-8") as _f:
                raw = [r[field] for r in json.load(_f) if r.get(field)]
            # Dịch tên bệnh OMIM → tiếng Việt (dataset C/F)
            if field == "name":
                return [_net_translate_disease(n) for n in raw]
            return raw
        except Exception:
            return fallback

    _net_drug_pool    = _net_load(f"thuoc_{_ds_key}.json",   "name",      SAMPLE_DRUGS)
    _net_disease_pool = _net_load(f"benh_{_ds_key}.json",    "name",      SAMPLE_DISEASES)
    _net_protein_pool = _net_load(f"protein_{_ds_key}.json", "accession", SAMPLE_PROTEINS)

    # ── Bộ điều khiển đồ thị ────────────────────────────────────────────────
    with col_seed:
        random_seed = st.slider("🎲 Hạt giống ngẫu nhiên", 0, 99, 42, key="net_seed",
                                help="Thay đổi để tái tạo mạng với cấu trúc khác.")
    with col_phys:
        show_physics = st.toggle("⚡ Bật vật lý", value=True, key="net_physics")

    col_legend_row, col_ai_btn = st.columns([1.4, 1.6])
    with col_legend_row:
        st.markdown("""
        <div class="glass-card" style="padding:0.8rem 1.2rem;font-size:0.82rem;">
          <div style="font-weight:800;color:#e2e8f0;margin-bottom:0.6rem;">📖 Chú thích cạnh đồ thị</div>
          <div style="display:flex;align-items:center;gap:0.5rem;margin-bottom:0.3rem;">
            <div style="width:14px;height:14px;background:#0066ff;border-radius:3px;"></div>
            <span style="color:#94a3b8;">Thuốc (hình vuông)</span>
          </div>
          <div style="display:flex;align-items:center;gap:0.5rem;margin-bottom:0.3rem;">
            <div style="width:14px;height:14px;background:#ff3333;border-radius:50%;"></div>
            <span style="color:#94a3b8;">Bệnh (hình tròn)</span>
          </div>
          <div style="display:flex;align-items:center;gap:0.5rem;margin-bottom:0.5rem;">
            <div style="width:0;height:0;border-left:8px solid transparent;
                        border-right:8px solid transparent;border-bottom:14px solid #00cc66;"></div>
            <span style="color:#94a3b8;">Protein (tam giác)</span>
          </div>
          <div style="border-top:1px solid rgba(255,255,255,0.07);padding-top:0.5rem;margin-top:0.2rem;">
            <div style="display:flex;align-items:center;gap:0.5rem;margin-bottom:0.3rem;">
              <div style="width:30px;height:2px;background:#00ccff;border-radius:2px;"></div>
              <span style="color:#00ccff;font-size:0.78rem;">─── Liên kết đã biết (nét liền)</span>
            </div>
            <div style="display:flex;align-items:center;gap:0.5rem;margin-bottom:0.3rem;">
              <div style="width:30px;height:2px;background:#f72585;
                          background: repeating-linear-gradient(90deg,#f72585 0,#f72585 4px,transparent 4px,transparent 8px);
                          "></div>
              <span style="color:#f72585;font-size:0.78rem;">- - - Thuốc→Bệnh (AI dự đoán)</span>
            </div>
            <div style="display:flex;align-items:center;gap:0.5rem;">
              <div style="width:30px;height:2px;
                          background: repeating-linear-gradient(90deg,#a78bfa 0,#a78bfa 4px,transparent 4px,transparent 8px);
                          "></div>
              <span style="color:#a78bfa;font-size:0.78rem;">- - - Thuốc/Bệnh→Protein (dữ liệu thực)</span>
            </div>
          </div>
        </div>
        """, unsafe_allow_html=True)

    with col_ai_btn:
        st.markdown("""
        <div class="glass-card" style="padding:0.9rem 1.2rem;border:1px solid rgba(247,37,133,0.3);
             box-shadow:0 0 20px rgba(247,37,133,0.08);">
          <div style="font-weight:800;color:#f72585;margin-bottom:0.5rem;font-size:0.92rem;">
            🤖 Dự đoán AI Liên kết
          </div>
          <div style="font-size:0.78rem;color:#94a3b8;margin-bottom:0.8rem;line-height:1.5;">
            FuzzyGCN chỉ dự đoán các liên kết <strong style="color:#f72585;">Thuốc–Bệnh</strong> và
            <strong style="color:#fb923c;">Bệnh–Thuốc</strong> từ mô hình đã huấn luyện.
            Các cạnh protein vẫn lấy từ dữ liệu thực, không dùng mô phỏng.
          </div>
        </div>
        """, unsafe_allow_html=True)
        _col_toggle, _col_thresh = st.columns(2)
        with _col_toggle:
            net_ai_predict = st.toggle(
                "🔮 Bật dự đoán AI",
                value=st.session_state.get("net_ai_predict", False),
                key="net_ai_predict",
                help="Bật để FuzzyGCN tự động thêm các liên kết dự đoán thật từ file trọng số .pth vào lưới"
            )
        with _col_thresh:
            ai_threshold = st.slider(
                "Ngưỡng xác suất",
                min_value=0.0, max_value=1.0,
                value=st.session_state.get("net_ai_threshold", 0.3),
                step=0.05,
                key="net_ai_threshold",
                help="Chỉ hiển thị liên kết dự đoán có xác suất ≥ ngưỡng này"
            )
        if net_ai_predict:
            st.markdown("""
            <div style="background:rgba(247,37,133,0.08);border:1px solid rgba(247,37,133,0.2);
                        border-radius:8px;padding:0.45rem 0.7rem;font-size:0.76rem;color:#f9a8d4;">
              ⚡ Đang dự đoán liên kết thật từ mô hình .pth. Đường nét đứt chỉ áp dụng cho cạnh AI Thuốc–Bệnh.
            </div>
            """, unsafe_allow_html=True)

    # ── Chọn tên nodes ────────────────────────────────────────────────────────
    col_d, col_dis, col_p = st.columns(3)
    with col_d:
        sel_drugs = st.multiselect(
            "💊 Chọn Thuốc hiển thị",
            _net_drug_pool,
            default=_net_drug_pool[:5],
            key=f"net_drugs_{_ds_key}",
            max_selections=10,
        )
    with col_dis:
        sel_diseases = st.multiselect(
            "🦠 Chọn Bệnh hiển thị",
            _net_disease_pool,
            default=_net_disease_pool[:5],
            key=f"net_diseases_{_ds_key}",
            max_selections=10,
        )
    with col_p:
        sel_proteins = st.multiselect(
            "🧬 Chọn Protein hiển thị",
            _net_protein_pool,
            default=_net_protein_pool[:5],
            key=f"net_proteins_{_ds_key}",
            max_selections=10,
        )

    # Đảm bảo luôn có ít nhất 1 node mỗi loại
    drugs    = sel_drugs    or SAMPLE_DRUGS[:1]
    diseases = sel_diseases or SAMPLE_DISEASES[:1]
    proteins = sel_proteins or SAMPLE_PROTEINS[:1]

    # ── Xây dựng đồ thị Pyvis ────────────────────────────────────────────────
    net = PyvisNetwork(
        height="600px",
        width="100%",
        bgcolor="#0d1b2a",
        font_color="#e2e8f0",
    )
    net.set_options(f"""
    {{
      "physics": {{
        "enabled": {str(show_physics).lower()},
        "barnesHut": {{
          "gravitationalConstant": -8000,
          "centralGravity": 0.3,
          "springLength": 130,
          "springConstant": 0.04,
          "damping": 0.09,
          "avoidOverlap": 0.2
        }},
        "minVelocity": 0.75
      }},
      "interaction": {{
        "hover": true,
        "tooltipDelay": 150,
        "navigationButtons": true,
        "keyboard": true
      }},
      "nodes": {{
        "borderWidth": 2,
        "borderWidthSelected": 4
      }},
      "edges": {{
        "smooth": {{ "type": "dynamic" }}
      }},
      "layout": {{
        "randomSeed": {random_seed}
      }}
    }}
    """)

    for i, drug in enumerate(drugs):
        net.add_node(
            n_id=f"D_{i}",
            label=drug,
            shape="square",
            color={
                "background": "#0066ff",
                "border":     "#00aaff",
                "highlight":  {"background": "#3399ff", "border": "#00f5d4"},
                "hover":      {"background": "#2277ff", "border": "#00f5d4"},
            },
            size=22,
            title=f"💊 <b>Thuốc</b>: {drug}<br>DrugBank: DB{10000+i:05d}",
            font={"color": "#ffffff", "size": 13, "bold": True},
            shadow=True,
        )

    for i, disease in enumerate(diseases):
        net.add_node(
            n_id=f"Dis_{i}",
            label=disease,
            shape="dot",
            color={
                "background": "#ff3333",
                "border":     "#ff6666",
                "highlight":  {"background": "#ff5555", "border": "#00f5d4"},
                "hover":      {"background": "#ff4444", "border": "#00f5d4"},
            },
            size=22,
            title=f"🦠 <b>Bệnh</b>: {disease}<br>ICD-10: E{10+i:02d}",
            font={"color": "#ffffff", "size": 13, "bold": True},
            shadow=True,
        )

    for i, protein in enumerate(proteins):
        net.add_node(
            n_id=f"P_{i}",
            label=protein,
            shape="triangle",
            color={
                "background": "#00cc66",
                "border":     "#00ffaa",
                "highlight":  {"background": "#00dd77", "border": "#00f5d4"},
                "hover":      {"background": "#00bb55", "border": "#00f5d4"},
            },
            size=22,
            title=f"🧬 <b>Protein</b>: {protein}<br>UniProt: P{10000+i:05d}",
            font={"color": "#ffffff", "size": 13, "bold": True},
            shadow=True,
        )

    # ── Thêm edges từ dữ liệu thực (file JSON liên kết) ────────────────────────
    nd = len(drugs)
    ndis = len(diseases)
    np_ = len(proteins)

    # Tạo lookup maps để kiểm tra node có tồn tại không
    drug_set = set(drugs)
    disease_set = set(diseases)
    protein_set = set(proteins)

    # Đọc liên kết thật từ file JSON
    def _load_links_json(fname: str) -> list[dict]:
        try:
            with open(_ROOT_DATA / fname, encoding="utf-8") as _f:
                return json.load(_f)
        except Exception:
            return []

    # Đọc tên thuốc/bệnh/protein theo local_id để map
    def _load_local_id_name_map(fname: str, name_field: str = "name") -> dict[int, str]:
        try:
            with open(_ROOT_DATA / fname, encoding="utf-8") as _f:
                return {r.get("local_id", r.get("id")): r.get(name_field, "") for r in json.load(_f)}
        except Exception:
            return {}

    drug_id_map = _load_local_id_name_map(f"thuoc_{_ds_key}.json")
    disease_id_map = _load_local_id_name_map(f"benh_{_ds_key}.json")
    protein_id_map = _load_local_id_name_map(f"protein_{_ds_key}.json", "accession")

    # Reverse maps: name -> node_id
    drug_name_to_idx = {d: f"D_{i}" for i, d in enumerate(drugs)}
    disease_name_to_idx = {d: f"Dis_{i}" for i, d in enumerate(diseases)}
    protein_name_to_idx = {p: f"P_{i}" for i, p in enumerate(proteins)}

    edge_count = 0
    verified_dd_pairs = set()

    # Thuốc–Bệnh edges (Đã xác nhận - Nét liền)
    dd_links = _load_links_json(f"lien_ket_{_ds_key}.json")
    for link in dd_links:
        d_id = link.get("drug_local_id", link.get("drug_id"))
        dis_id = link.get("disease_local_id", link.get("disease_id"))
        d_name = drug_id_map.get(d_id, "")
        dis_name = disease_id_map.get(dis_id, "")
        if d_name in drug_set and dis_name in disease_set:
            d_node = drug_name_to_idx[d_name]
            dis_node = disease_name_to_idx[dis_name]
            score = round(link.get("score", 1.0), 2)
            net.add_edge(
                d_node, dis_node,
                value=score,
                color={"color": "#00ccff", "highlight": "#00f5d4", "hover": "#00f5d4"},
                title=f"\u2705 Thuốc\u2013Bệnh · Đã xác nhận<br>Score: {score:.3f}",
                width=max(1.5, score * 2.5),
            )
            verified_dd_pairs.add((d_name, dis_name))
            edge_count += 1

    # Thêm cạnh dự đoán (Nét đứt) chỉ khi toggle bật
    predicted_edge_count = 0
    prediction_errors: list[str] = []
    _ai_node_counter = len(drugs) + len(diseases)  # counter for new AI node IDs

    if net_ai_predict and _API_OK and nd > 0 and ndis > 0:
        client = ApiClient(API_DEFAULT)
        if st.session_state.get("api_token"):
            client.token = st.session_state["api_token"]

        # Giới hạn số node AI mới để đồ thị không quá lớn
        _MAX_AI_NODES = 15
        _ai_added_nodes = 0

        with st.spinner("🤖 FuzzyGCN đang dự đoán liên kết Thuốc–Bệnh..."):
            # Thuốc → Bệnh (nét đứt hồng)
            for drug in drugs:
                try:
                    response = client.predict_drug_to_disease(
                        name=drug, top_k=30, threshold=ai_threshold,
                        dataset=_ds_key.upper() + "-dataset"
                    )
                    preds = response.get("results", []) if isinstance(response, dict) else []
                    for p in preds:
                        if not isinstance(p, dict):
                            continue
                        dis_name = p.get("name", "")
                        score = round(p.get("score", 0.0), 2)
                        if score < ai_threshold:
                            continue
                        if (drug, dis_name) in verified_dd_pairs:
                            continue
                        is_known = p.get("known", False)
                        status_txt = "✅ Đã biết" if is_known else "🔬 Dự đoán"
                        # Tự động thêm node bệnh mới nếu chưa có trong đồ thị
                        if dis_name not in disease_name_to_idx:
                            if _ai_added_nodes >= _MAX_AI_NODES:
                                continue
                            new_id = f"AI_Dis_{_ai_node_counter}"
                            _ai_node_counter += 1
                            _ai_added_nodes += 1
                            net.add_node(
                                n_id=new_id,
                                label=dis_name,
                                shape="dot",
                                color={
                                    "background": "#ff3333",
                                    "border":     "#f72585",
                                    "highlight":  {"background": "#ff5555", "border": "#00f5d4"},
                                    "hover":      {"background": "#ff4444", "border": "#00f5d4"},
                                },
                                size=18,
                                title=f"🤖 <b>AI Dự đoán Bệnh</b>: {dis_name}<br>Score: {score:.3f}<br>{status_txt}",
                                font={"color": "#f9a8d4", "size": 12},
                                shadow=True,
                                borderWidth=1,
                            )
                            disease_name_to_idx[dis_name] = new_id
                        d_node = drug_name_to_idx[drug]
                        dis_node = disease_name_to_idx[dis_name]
                        if is_known:
                            e_color = {"color": "#00ccff", "highlight": "#00f5d4", "hover": "#00f5d4"}
                            e_title = f"✅ Thuốc→Bệnh · Đã xác nhận<br>Score: {score:.3f}"
                        else:
                            e_color = {"color": "#f72585", "highlight": "#ff4d6d", "hover": "#ff4d6d"}
                            e_title = f"🤖 AI Dự đoán Thuốc→Bệnh<br>Xác suất: {score:.3f}"
                        net.add_edge(
                            d_node, dis_node,
                            value=score,
                            color=e_color,
                            title=e_title,
                            width=max(1.0, score * 3),
                            dashes=not is_known,
                        )
                        predicted_edge_count += 1
                        verified_dd_pairs.add((drug, dis_name))
                except Exception as exc:
                    prediction_errors.append(f"Thuốc→Bệnh `{drug}`: {exc}")

            # Bệnh → Thuốc (nét đứt cam - chiều ngược)
            for disease in diseases:
                try:
                    response_d2d = client.predict_disease_to_drug(
                        name=disease, top_k=20, threshold=ai_threshold,
                        dataset=_ds_key.upper() + "-dataset"
                    )
                    preds_d2d = response_d2d.get("results", []) if isinstance(response_d2d, dict) else []
                    for p in preds_d2d:
                        if not isinstance(p, dict):
                            continue
                        drug_name_val = p.get("name", "")
                        score = round(p.get("score", 0.0), 2)
                        if score < ai_threshold:
                            continue
                        if (drug_name_val, disease) in verified_dd_pairs:
                            continue
                        is_known = p.get("known", False)
                        status_txt = "✅ Đã biết" if is_known else "🔬 Dự đoán"
                        # Tự động thêm node thuốc mới nếu chưa có trong đồ thị
                        if drug_name_val not in drug_name_to_idx:
                            if _ai_added_nodes >= _MAX_AI_NODES:
                                continue
                            new_id = f"AI_D_{_ai_node_counter}"
                            _ai_node_counter += 1
                            _ai_added_nodes += 1
                            net.add_node(
                                n_id=new_id,
                                label=drug_name_val,
                                shape="square",
                                color={
                                    "background": "#0066ff",
                                    "border":     "#fb923c",
                                    "highlight":  {"background": "#3399ff", "border": "#00f5d4"},
                                    "hover":      {"background": "#2277ff", "border": "#00f5d4"},
                                },
                                size=18,
                                title=f"🤖 <b>AI Dự đoán Thuốc</b>: {drug_name_val}<br>Score: {score:.3f}<br>{status_txt}",
                                font={"color": "#fdba74", "size": 12},
                                shadow=True,
                                borderWidth=1,
                            )
                            drug_name_to_idx[drug_name_val] = new_id
                        d_node = drug_name_to_idx[drug_name_val]
                        dis_node = disease_name_to_idx[disease]
                        if is_known:
                            e_color = {"color": "#00ccff", "highlight": "#00f5d4", "hover": "#00f5d4"}
                            e_title = f"✅ Bệnh→Thuốc · Đã xác nhận<br>Score: {score:.3f}"
                        else:
                            e_color = {"color": "#fb923c", "highlight": "#fbbf24", "hover": "#fbbf24"}
                            e_title = f"🤖 AI Dự đoán Bệnh→Thuốc<br>Xác suất: {score:.3f}"
                        net.add_edge(
                            dis_node, d_node,
                            value=score,
                            color=e_color,
                            title=e_title,
                            width=max(1.0, score * 3),
                            dashes=not is_known,
                        )
                        predicted_edge_count += 1
                        verified_dd_pairs.add((drug_name_val, disease))
                except Exception as exc:
                    prediction_errors.append(f"Bệnh→Thuốc `{disease}`: {exc}")

        if predicted_edge_count > 0:
            st.success(f"✅ FuzzyGCN dự đoán được **{predicted_edge_count}** liên kết mới (ngưỡng ≥ {ai_threshold:.0%})")
        elif not prediction_errors:
            st.info("ℹ️ Không tìm thấy liên kết dự đoán nào vượt ngưỡng. Thử giảm ngưỡng xác suất.")
        if prediction_errors:
            st.error("Không thể tạo một phần cạnh AI từ file trọng số .pth.")
            st.code("\n".join(prediction_errors[:12]), language="text")

    # ── Thuốc–Protein edges: tự động thêm node nếu cần ──────────────────────────
    # Giới hạn: chỉ thêm node mới khi protein đã có trong graph (phải được chọn),
    # nhưng thuốc/bệnh có liên kết protein có thể tự động được thêm
    _MAX_PROT_NODES = 10
    _prot_added = 0

    dp_links = _load_links_json("drug_protein_links.json")
    for link in dp_links:
        d_id = link.get("drug_id")
        p_id = link.get("protein_id")
        d_name = drug_id_map.get(d_id, "")
        p_name = protein_id_map.get(p_id, "")
        if not d_name or not p_name:
            continue
        # Chỉ xử lý nếu thuốc hoăc protein đã có trong graph
        if d_name not in drug_name_to_idx and p_name not in protein_name_to_idx:
            continue
        # Tự động thêm node thuốc nếu chưa có
        if d_name not in drug_name_to_idx:
            if _prot_added >= _MAX_PROT_NODES:
                continue
            new_did = f"AutoD_{_ai_node_counter}"
            _ai_node_counter += 1
            _prot_added += 1
            net.add_node(
                n_id=new_did,
                label=d_name,
                shape="square",
                color={
                    "background": "#0066ff",
                    "border":     "#fb923c",
                },
                size=18,
                title=f"Thuốc thêm tự động từ liên kết protein",
            )
            drug_name_to_idx[d_name] = new_did
        # Tự động thêm node protein nếu chưa có
        if p_name not in protein_name_to_idx:
            if _prot_added >= _MAX_PROT_NODES:
                continue
            new_pid = f"AutoP_{_ai_node_counter}"
            _ai_node_counter += 1
            _prot_added += 1
            net.add_node(
                n_id=new_pid,
                label=p_name,
                shape="triangle",
                color={
                    "background": "#00cc66",
                    "border":     "#00ffaa",
                },
                size=18,
                title=f"\U0001f9ec Protein tự động thêm từ thuốc",
            )
            protein_name_to_idx[p_name] = new_pid
        d_node = drug_name_to_idx[d_name]
        p_node = protein_name_to_idx[p_name]
        net.add_edge(
            d_node, p_node,
            color={"color": "#9966ff", "highlight": "#cc99ff", "hover": "#cc99ff"},
            title=f"\U0001f9ec Thuốc–Protein · Tương tác thực<br>{d_name} \u2192 {p_name}",
            width=1.5,
            dashes=True,
        )
        edge_count += 1

    # Bệnh–Protein edges
    dis_p_links = _load_links_json("protein_disease_links.json")
    for link in dis_p_links:
        dis_id = link.get("disease_id")
        p_id = link.get("protein_id")
        dis_name = disease_id_map.get(dis_id, "")
        p_name = protein_id_map.get(p_id, "")
        if not dis_name or not p_name:
            continue
        # Chỉ xử lý nếu bệnh hoặc protein đã có trong graph
        if dis_name not in disease_name_to_idx and p_name not in protein_name_to_idx:
            continue
        # Tự động thêm node bệnh nếu chưa có
        if dis_name not in disease_name_to_idx:
            if _prot_added >= _MAX_PROT_NODES:
                continue
            new_did = f"AutoDis_{_ai_node_counter}"
            _ai_node_counter += 1
            _prot_added += 1
            net.add_node(
                n_id=new_did,
                label=dis_name,
                shape="dot",
                color={
                    "background": "#ff3333",
                    "border":     "#f72585",
                },
                size=18,
                title=f"Bệnh thêm tự động từ liên kết protein",
            )
            disease_name_to_idx[dis_name] = new_did
        # Tự động thêm node protein nếu chưa có
        if p_name not in protein_name_to_idx:
            if _prot_added >= _MAX_PROT_NODES:
                continue
            new_pid = f"AutoP_{_ai_node_counter}"
            _ai_node_counter += 1
            _prot_added += 1
            net.add_node(
                n_id=new_pid,
                label=p_name,
                shape="triangle",
                color={
                    "background": "#00cc66",
                    "border":     "#00ffaa",
                },
                size=18,
                title=f"\U0001f9ec Protein tự động thêm từ bệnh",
            )
            protein_name_to_idx[p_name] = new_pid
        dis_node = disease_name_to_idx[dis_name]
        p_node = protein_name_to_idx[p_name]
        net.add_edge(
            dis_node, p_node,
            color={"color": "#ff9900", "highlight": "#ffcc33", "hover": "#ffcc33"},
            title=f"\U0001f9ec Bệnh–Protein · Liên quan thực<br>{dis_name} \u2192 {p_name}",
            width=1.5,
            dashes=True,
        )
        edge_count += 1

    if edge_count == 0 and not net_ai_predict:
        st.info("ℹ️ Không tìm thấy liên kết nào giữa các node đã chọn. "
                "Hãy thử chọn các thuốc/bệnh/protein khác, hoặc bật dự đoán AI.")

    # ── Lưu HTML và render ─────────────────────────────────────────────────────
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".html", delete=False, encoding="utf-8"
    ) as tmp_file:
        net.save_graph(tmp_file.name)
        tmp_path = tmp_file.name

    # Đọc nội dung HTML ra string trước, rồi mới xóa file tạm
    # (Không được xóa file trong finally khi dùng st.iframe(path)
    #  vì browser chưa kịp đọc — dẫn đến iframe trống và mất cạnh nối)
    with open(tmp_path, "r", encoding="utf-8") as _f:
        _net_html = _f.read()
    try:
        os.unlink(tmp_path)
    except OSError:
        pass

    # Render đồ thị qua _html_iframe (giống với Trạm Dự Đoán)
    st.markdown('<div class="glass-card" style="padding:0.5rem;">', unsafe_allow_html=True)
    _html_iframe(_net_html, height=630, scrolling=False)
    st.markdown("</div>", unsafe_allow_html=True)

    # Thống kê nhanh
    st.markdown(f"""
    <div style="display:flex;gap:1rem;margin-top:0.8rem;flex-wrap:wrap;">
      <div class="metric-card" style="flex:1;min-width:120px;">
        <div class="metric-value" style="font-size:1.8rem;color:#0066ff;">{len(drugs)}</div>
        <div class="metric-label">Thuốc</div>
      </div>
      <div class="metric-card" style="flex:1;min-width:120px;">
        <div class="metric-value" style="font-size:1.8rem;color:#ff3333;">{len(diseases)}</div>
        <div class="metric-label">Bệnh</div>
      </div>
      <div class="metric-card" style="flex:1;min-width:120px;">
        <div class="metric-value" style="font-size:1.8rem;color:#00cc66;">{len(proteins)}</div>
        <div class="metric-label">Protein</div>
      </div>
      <div class="metric-card" style="flex:1;min-width:120px;">
        <div class="metric-value" style="font-size:1.8rem;color:#00f5d4;">{len(drugs)+len(diseases)+len(proteins)}</div>
        <div class="metric-label">Tổng nodes</div>
      </div>
      <div class="metric-card" style="flex:1;min-width:120px;">
        <div class="metric-value" style="font-size:1.8rem;color:#fbbf24;">{edge_count}</div>
        <div class="metric-label">Liên kết thực</div>
      </div>
      <div class="metric-card" style="flex:1;min-width:120px;">
        <div class="metric-value" style="font-size:1.8rem;color:#f72585;">{predicted_edge_count}</div>
        <div class="metric-label">AI Dự đoán</div>
      </div>
    </div>
    """, unsafe_allow_html=True)


# =============================================================================
# TRANG: DUYỆT LIÊN KẾT (Expert only)
# =============================================================================
def render_review_page() -> None:
    """Giao diện cho Expert duyệt các liên kết mới được AI tìm ra."""
    if not _can("expert"):
        st.markdown("""
        <div class="access-denied fade-in">
          <div style="font-size:3rem;margin-bottom:0.8rem;">🔒</div>
          <div style="font-size:1.2rem;font-weight:800;margin-bottom:0.5rem;">
            Yêu cầu vai trò Chuyên gia hoặc Quản trị viên</div>
          <div style="font-size:0.88rem;color:rgba(247,37,133,0.7);">
            Chức năng Duyệt Liên Kết chỉ dành cho vai trò
            <strong>Chuyên gia</strong> hoặc <strong>Quản trị viên</strong>.
          </div>
        </div>
        """, unsafe_allow_html=True)
        return

    st.markdown('<div class="page-title fade-in">✅ Duyệt Liên Kết</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-subtitle">Xác nhận hoặc loại bỏ các liên kết Thuốc–Bệnh theo từng Dataset</div>',
                unsafe_allow_html=True)

    # ── Chọn Dataset ──────────────────────────────────────────────────────────
    _DS_OPTIONS_RV = ["B-dataset", "C-dataset", "F-dataset"]
    _DS_KEY_RV = {"B-dataset": "b", "C-dataset": "c", "F-dataset": "f"}

    col_ds_rv, col_page_rv, _ = st.columns([1.5, 1, 1.5])
    with col_ds_rv:
        rv_dataset = st.selectbox("📂 Chọn Dataset để duyệt", _DS_OPTIONS_RV, key="rv_dataset")
    rv_key = _DS_KEY_RV[rv_dataset]

    # ── Load dữ liệu liên kết thực từ JSON ───────────────────────────────────
    _ROOT_RV = Path(__file__).parent.parent / "data"

    @st.cache_data(ttl=300)
    def _load_review_links(ds_key: str, page: int = 0, per_page: int = 20):
        """Load liên kết thực từ file JSON, phân trang."""
        # Load drug name map: local_id -> name
        try:
            with open(_ROOT_RV / f"thuoc_{ds_key}.json", encoding="utf-8") as f:
                drugs_data = json.load(f)
            drug_map = {r["local_id"]: r["name"] for r in drugs_data if "local_id" in r}
        except Exception:
            drug_map = {}

        # Load disease name map: local_id -> name
        try:
            with open(_ROOT_RV / f"benh_{ds_key}.json", encoding="utf-8") as f:
                diseases_data = json.load(f)
            disease_map = {r["local_id"]: r["name"] for r in diseases_data if "local_id" in r}
        except Exception:
            disease_map = {}

        # Load links
        try:
            with open(_ROOT_RV / f"lien_ket_{ds_key}.json", encoding="utf-8") as f:
                all_links = json.load(f)
        except Exception:
            all_links = []

        total = len(all_links)
        start = page * per_page
        end = min(start + per_page, total)
        page_links = all_links[start:end]

        result = []
        for link in page_links:
            d_name = drug_map.get(link.get("drug_local_id"), f"Drug#{link.get('drug_local_id', '?')}")
            dis_name = disease_map.get(link.get("disease_local_id"), f"Disease#{link.get('disease_local_id', '?')}")
            result.append({
                "id": link.get("id", 0),
                "drug": d_name,
                "disease": dis_name,
                "drug_local_id": link.get("drug_local_id", -1),
                "disease_local_id": link.get("disease_local_id", -1),
                "score": link.get("score", 1.0),
                "status": "Chờ duyệt",
            })
        return result, total

    # Phân trang
    with col_page_rv:
        per_page = 20
        _, total_links = _load_review_links(rv_key, 0, 1)
        max_page = max(0, (total_links - 1) // per_page)
        current_page = st.number_input(
            f"Trang (tổng {total_links:,} liên kết)",
            min_value=0, max_value=max_page, value=0, step=1, key="rv_page",
        )

    pending_links, total_links = _load_review_links(rv_key, current_page, per_page)

    if not pending_links:
        st.info(f"📋 Không tìm thấy liên kết nào trong dataset {rv_dataset}.")
        return

    # Khởi tạo trạng thái duyệt trong session
    if "review_statuses" not in st.session_state:
        st.session_state["review_statuses"] = {}
    # Đảm bảo mọi link đều có status
    for link in pending_links:
        if link["id"] not in st.session_state["review_statuses"]:
            st.session_state["review_statuses"][link["id"]] = link["status"]

    # Thống kê nhanh
    statuses = st.session_state["review_statuses"]
    relevant_ids = {link["id"] for link in pending_links}
    n_pending  = sum(1 for lid, s in statuses.items() if lid in relevant_ids and s == "Chờ duyệt")
    n_approved = sum(1 for lid, s in statuses.items() if lid in relevant_ids and s == "Đã duyệt ✅")
    n_rejected = sum(1 for lid, s in statuses.items() if lid in relevant_ids and s == "Đã từ chối ❌")

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(f"""<div class="metric-card">
          <div class="metric-value" style="color:#fbbf24;">{n_pending}</div>
          <div class="metric-label">Chờ duyệt</div></div>""", unsafe_allow_html=True)
    with c2:
        st.markdown(f"""<div class="metric-card">
          <div class="metric-value" style="color:#4ade80;">{n_approved}</div>
          <div class="metric-label">Đã duyệt</div></div>""", unsafe_allow_html=True)
    with c3:
        st.markdown(f"""<div class="metric-card">
          <div class="metric-value" style="color:#f87171;">{n_rejected}</div>
          <div class="metric-label">Đã từ chối</div></div>""", unsafe_allow_html=True)

    st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)

    # ── Bảng duyệt liên kết ────────────────────────────────────────────────────
    st.markdown('<div class="glass-card" style="padding:1.2rem;">', unsafe_allow_html=True)
    st.markdown("""
    <div style="font-size:0.85rem;color:#475569;margin-bottom:0.8rem;">
      💡 Nhấn <strong style="color:#4ade80;">Duyệt ✅</strong> để chấp nhận hoặc
      <strong style="color:#f87171;">Từ chối ❌</strong> để loại bỏ liên kết.
    </div>
    """, unsafe_allow_html=True)

    for link in pending_links:
        lid    = link["id"]
        status = st.session_state["review_statuses"].get(lid, "Chờ duyệt")

        # Màu nền theo trạng thái
        if status == "Đã duyệt ✅":
            bg = "rgba(74,222,128,0.06)"; brd = "rgba(74,222,128,0.3)"
        elif status == "Đã từ chối ❌":
            bg = "rgba(248,113,113,0.06)"; brd = "rgba(248,113,113,0.3)"
        else:
            bg = "rgba(255,255,255,0.03)"; brd = "rgba(255,255,255,0.1)"

        col_info, col_score, col_status, col_btn = st.columns([3, 1.2, 1.5, 2])

        with col_info:
            st.markdown(f"""
            <div style="padding:0.5rem 0;">
              <div style="font-size:0.9rem;font-weight:700;color:#e2e8f0;">
                💊 {link['drug']} → 🦠 {link['disease']}
              </div>
              <div style="font-size:0.75rem;color:#475569;margin-top:0.15rem;">
                Liên kết #{lid} · AI FuzzyGCN
              </div>
            </div>
            """, unsafe_allow_html=True)

        with col_score:
            score_color = "#4ade80" if link["score"] >= 0.75 else \
                          "#fbbf24" if link["score"] >= 0.6 else "#94a3b8"
            st.markdown(f"""
            <div style="padding:0.5rem 0;text-align:center;">
              <div style="font-size:1.3rem;font-weight:900;color:{score_color};
                          text-shadow:0 0 12px {score_color}88;">
                {link['score']:.0%}
              </div>
              <div style="font-size:0.7rem;color:#475569;">xác suất</div>
            </div>
            """, unsafe_allow_html=True)

        with col_status:
            st.markdown(f"""
            <div style="padding:0.6rem 0;font-size:0.82rem;font-weight:700;
                        color:{'#4ade80' if 'duyệt ✅' in status else
                               '#f87171' if 'từ chối' in status else '#fbbf24'};">
              {status}
            </div>
            """, unsafe_allow_html=True)

        with col_btn:
            b1, b2 = st.columns(2)
            with b1:
                if st.button("✅", key=f"approve_{lid}",
                             help="Duyệt liên kết này",
                             disabled=(status == "Đã duyệt ✅")):
                    st.session_state["review_statuses"][lid] = "Đã duyệt ✅"
                    st.rerun()
            with b2:
                if st.button("❌", key=f"reject_{lid}",
                             help="Từ chối liên kết này",
                             disabled=(status == "Đã từ chối ❌")):
                    st.session_state["review_statuses"][lid] = "Đã từ chối ❌"
                    st.rerun()

        st.markdown(f"""
        <div style="border:1px solid {brd};background:{bg};border-radius:8px;
                    height:2px;margin-bottom:0.3rem;"></div>
        """, unsafe_allow_html=True)

        st.markdown("</div>", unsafe_allow_html=True)


# =============================================================================
# DATA HELPERS
# =============================================================================
def _data_root() -> Path:
    return Path(__file__).parent.parent / "data"


def _load_json_records(filename: str) -> list[dict]:
    try:
        with open(_data_root() / filename, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except Exception:
        return []


def _save_json_records(filename: str, rows: list[dict]) -> None:
    with open(_data_root() / filename, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)


def _flatten_history_rows(history_rows: list[dict], users: list[dict]) -> pd.DataFrame:
    user_map = {
        "user1": "doctor_nguyen",
        "user2": "expert_tran",
        "1": "admin",
        "2": "user",
        "3": "expert",
    }
    for user in users:
        user_id = user.get("id")
        username = user.get("username")
        if user_id is not None and username:
            user_map[str(user_id)] = username

    flat_rows: list[dict] = []
    for item in reversed(history_rows):
        top_results = item.get("results", [])
        top_name = top_results[0].get("name") if top_results else (item.get("target_name") or "")
        top_score = top_results[0].get("score") if top_results else (item.get("score") or item.get("top_score") or 0)
        raw_direction = str(item.get("query_type") or item.get("direction") or "")
        if "drug_to_disease" in raw_direction:
            display_direction = "Thuoc -> Benh"
        elif "disease_to_drug" in raw_direction:
            display_direction = "Benh -> Thuoc"
        else:
            display_direction = raw_direction or "Khac"

        user_id_val = item.get("user_id")
        username_val = item.get("username")
        display_user = username_val or user_map.get(str(user_id_val), str(user_id_val or "Khach"))

        flat_rows.append({
            "ID": item.get("id"),
            "Thoi gian": str(item.get("timestamp", ""))[:19].replace("T", " "),
            "Nguoi dung": display_user,
            "Loai truy van": display_direction,
            "Tu khoa": item.get("query") or item.get("input_name", ""),
            "Ket qua Top 1": top_name,
            "Diem so": round(float(top_score), 4) if top_score not in (None, "") else None,
        })

    return pd.DataFrame(flat_rows)


def _metrics_table_from_weights() -> pd.DataFrame:
    all_metrics = _load_kfold_metrics()
    rows = []
    for dataset, data in all_metrics.items():
        mean_vals = data.get("mean", {})
        std_vals = data.get("std", {})
        row = {"Dataset": dataset, "Folds": data.get("so_fold", len(data.get("folds", [])))}
        for metric in ["AUC", "AUPR", "Accuracy", "Precision", "Recall", "F1", "MCC"]:
            row[metric] = mean_vals.get(metric)
            row[f"{metric}_std"] = std_vals.get(metric)
        rows.append(row)
    return pd.DataFrame(rows)


def _db_schema_groups() -> dict[str, list[tuple[str, str]]]:
    return {
        "Nhom loi": [
            ("nguoi_dung", "Tài khoản, vai trò, xác thực"),
            ("thuoc", "Danh mục thuốc dùng chung"),
            ("benh", "Danh mục bệnh dùng chung"),
            ("protein", "Danh mục protein dùng chung"),
            ("lich_su_du_doan", "Lịch sử dự đoán theo người dùng"),
            ("lien_ket_thuoc_benh", "Quan hệ thuốc - bệnh đã xác nhận"),
            ("lien_ket_thuoc_protein", "Quan hệ thuốc - protein"),
            ("lien_ket_protein_benh", "Quan hệ protein - bệnh"),
        ],
        "Theo dataset": [
            ("thuoc_b / thuoc_c / thuoc_f", "Bản sao dữ liệu thuốc theo từng bộ dữ liệu"),
            ("benh_b / benh_c / benh_f", "Bản sao dữ liệu bệnh theo từng bộ dữ liệu"),
            ("protein_b / protein_c / protein_f", "Bản sao dữ liệu protein theo từng bộ dữ liệu"),
            ("lien_ket_b / lien_ket_c / lien_ket_f", "Liên kết thuốc - bệnh gốc theo dataset"),
        ],
        "Lop dong bo": [
            ("src/data/*.json", "JSON cache cho frontend và fallback khi DB không sẵn sàng"),
            ("app_local.db", "SQLite cục bộ khi không dùng SQL Server"),
        ],
    }


# =============================================================================
# TRANG: CẤU HÌNH & METRICS (Admin only)
# =============================================================================
def render_config_page() -> None:
    """Trang cau hinh mo hinh va xem metrics chi tiet (chi Admin)."""
    if not _can("admin"):
        st.markdown("""
        <div class="access-denied fade-in">
          <div style="font-size:3rem;margin-bottom:0.8rem;">ADMIN</div>
          <div style="font-size:1.2rem;font-weight:800;margin-bottom:0.5rem;">Yeu cau quyen Admin</div>
          <div style="font-size:0.88rem;color:rgba(247,37,133,0.7);">Trang Cau Hinh & Metrics chi danh cho <strong>Quan tri vien</strong>.</div>
        </div>
        """, unsafe_allow_html=True)
        return

    st.markdown('<div class="page-title fade-in">Cấu Hình & Metrics</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-subtitle">Sắp xếp theo 4 khối: hiệu suất, cấu hình huấn luyện, đối chiếu dataset và kiến trúc lưu trữ</div>', unsafe_allow_html=True)

    metrics_df = _metrics_table_from_weights()
    tab_metrics, tab_train, tab_compare, tab_db = st.tabs(["Hiệu suất mô hình", "Tham số huấn luyện", "So sánh Dataset", "Quản lý CSDL"])

    with tab_metrics:
        st.markdown("<div style='height:0.4rem'></div>", unsafe_allow_html=True)
        if metrics_df.empty:
            st.warning("Không tìm thấy file `kfold_metrics.json` trong thư mục `weights/`.")
        else:
            selected_dataset = st.selectbox("Dataset đang xem", metrics_df["Dataset"].tolist(), key="cfg_metrics_dataset")
            selected_row = metrics_df.loc[metrics_df["Dataset"] == selected_dataset].iloc[0]
            metric_cols = st.columns(4)
            for idx, (metric_name, color) in enumerate([("AUC", "#00f5d4"), ("AUPR", "#00b4d8"), ("F1", "#a78bfa"), ("MCC", "#fbbf24")]):
                with metric_cols[idx]:
                    st.markdown(f"""
                        <div class="metric-card">
                          <div class="metric-value" style="color:{color};text-shadow:0 0 20px {color}55;">{float(selected_row[metric_name]):.4f}</div>
                          <div class="metric-label">{metric_name}</div>
                          <div class="metric-delta" style="color:#94a3b8;">+- {float(selected_row[f'{metric_name}_std']):.4f}</div>
                        </div>
                    """, unsafe_allow_html=True)

            left_metrics, right_metrics = st.columns([1.45, 1])
            with left_metrics:
                st.markdown('<div class="glass-card">', unsafe_allow_html=True)
                st.markdown('<div style="font-size:0.95rem;font-weight:800;color:#00f5d4;margin-bottom:0.8rem;">Bảng metrics theo dataset</div>', unsafe_allow_html=True)
                st.dataframe(metrics_df[["Dataset", "Folds", "AUC", "AUPR", "Accuracy", "Precision", "Recall", "F1", "MCC"]], use_container_width=True, hide_index=True)
                st.markdown("</div>", unsafe_allow_html=True)

            with right_metrics:
                st.markdown('<div class="glass-card">', unsafe_allow_html=True)
                st.markdown('<div style="font-size:0.95rem;font-weight:800;color:#fbbf24;margin-bottom:0.8rem;">Xếp hạng nhanh</div>', unsafe_allow_html=True)
                for label, row, metric_name, color in [("AUC cao nhất", metrics_df.sort_values("AUC", ascending=False).iloc[0], "AUC", "#00f5d4"), ("F1 cao nhất", metrics_df.sort_values("F1", ascending=False).iloc[0], "F1", "#a78bfa"), ("MCC cao nhất", metrics_df.sort_values("MCC", ascending=False).iloc[0], "MCC", "#fbbf24")]:
                    st.markdown(f"""
                        <div style="padding:0.7rem 0.9rem;margin-bottom:0.55rem;background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.08);border-left:3px solid {color};border-radius:10px;">
                          <div style="font-size:0.72rem;color:#94a3b8;text-transform:uppercase;font-weight:700;">{label}</div>
                          <div style="font-size:0.95rem;font-weight:800;color:#e2e8f0;">{row['Dataset']}</div>
                          <div style="font-size:0.82rem;color:{color};font-weight:700;">{float(row[metric_name]):.4f}</div>
                        </div>
                    """, unsafe_allow_html=True)
                st.markdown("</div>", unsafe_allow_html=True)

            st.markdown('<div class="glass-card" style="margin-top:0.8rem;">', unsafe_allow_html=True)
            st.markdown('<div style="font-size:0.95rem;font-weight:800;color:#a78bfa;margin-bottom:0.8rem;">So sánh trực quan AUC và AUPR</div>', unsafe_allow_html=True)
            st.bar_chart(metrics_df.set_index("Dataset")[["AUC", "AUPR"]], color=["#00f5d4", "#a78bfa"])
            st.markdown("</div>", unsafe_allow_html=True)

    with tab_train:
        st.markdown("<div style='height:0.4rem'></div>", unsafe_allow_html=True)
        col_l, col_r = st.columns(2)
        with col_l:
            st.markdown('<div class="glass-card">', unsafe_allow_html=True)
            st.markdown('<div style="font-size:0.95rem;font-weight:800;color:#00f5d4;margin-bottom:1rem;">1. Siêu tham số chung</div>', unsafe_allow_html=True)
            dataset_sel = st.selectbox("Dataset mục tiêu", ["B-dataset", "C-dataset", "F-dataset"], key="cfg_dataset")
            epochs_val = st.slider("Số Epoch", 10, 500, 200, 10, key="cfg_epochs")
            lr_val = st.select_slider("Learning Rate", options=[0.0001, 0.0005, 0.001, 0.005, 0.01, 0.05], value=0.001, key="cfg_lr", format_func=lambda x: f"{x:.4f}")
            batch_sz = st.slider("Kích thước Batch", 16, 512, 64, 16, key="cfg_batch")
            dropout = st.slider("Dropout", 0.0, 0.8, 0.3, 0.05, key="cfg_dropout")
            st.markdown("</div>", unsafe_allow_html=True)
        with col_r:
            st.markdown('<div class="glass-card">', unsafe_allow_html=True)
            st.markdown('<div style="font-size:0.95rem;font-weight:800;color:#a78bfa;margin-bottom:1rem;">2. Kiến trúc GCN</div>', unsafe_allow_html=True)
            hidden_dim = st.select_slider("Hidden Dim", options=[32, 64, 128, 256, 512], value=128, key="cfg_hidden")
            num_layers = st.slider("Số lớp GCN", 1, 6, 3, key="cfg_layers")
            fuzzy_m = st.slider("Fuzzy m", 1.1, 3.0, 2.0, 0.1, key="cfg_fuzzy_m")
            aggregator = st.selectbox("Aggregator", ["mean", "sum", "max", "attention"], key="cfg_aggregator")
            use_batch_norm = st.toggle("Batch Normalization", value=True, key="cfg_bn")
            use_residual = st.toggle("Residual connections", value=False, key="cfg_res")
            st.markdown("</div>", unsafe_allow_html=True)

        cfg_preview = {"dataset": dataset_sel, "epochs": epochs_val, "lr": lr_val, "batch_size": batch_sz, "dropout": dropout, "hidden_dim": hidden_dim, "num_layers": num_layers, "fuzzy_m": fuzzy_m, "aggregator": aggregator, "batch_norm": use_batch_norm, "residual": use_residual}
        save_col, preview_col = st.columns([1, 2])
        with save_col:
            if st.button("Lưu cấu hình", type="primary", use_container_width=True, key="btn_save_cfg"):
                st.session_state["saved_config"] = cfg_preview
                st.success(f"Đã lưu cấu hình cho `{dataset_sel}`.")
        with preview_col:
            st.markdown('<div class="glass-card" style="padding:1rem 1.2rem;">', unsafe_allow_html=True)
            st.markdown('<div style="font-size:0.88rem;font-weight:800;color:#94a3b8;margin-bottom:0.5rem;">3. Xem trước cấu hình</div>', unsafe_allow_html=True)
            st.json(cfg_preview)
            st.markdown("</div>", unsafe_allow_html=True)

    with tab_compare:
        st.markdown("<div style='height:0.4rem'></div>", unsafe_allow_html=True)
        if metrics_df.empty:
            st.warning("Không có dữ liệu metrics để so sánh dataset.")
        else:
            compare_df = metrics_df[["Dataset", "Folds", "AUC", "AUPR", "Accuracy", "F1", "MCC"]].copy()
            st.markdown('<div class="glass-card">', unsafe_allow_html=True)
            st.markdown('<div style="font-size:0.95rem;font-weight:800;color:#00f5d4;margin-bottom:0.8rem;">Bảng so sánh dataset</div>', unsafe_allow_html=True)
            st.dataframe(compare_df, use_container_width=True, hide_index=True)
            st.markdown("</div>", unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            with c1:
                st.markdown('<div class="glass-card">', unsafe_allow_html=True)
                st.markdown('<div style="font-size:0.9rem;font-weight:700;color:#fbbf24;margin-bottom:0.6rem;">AUC / AUPR</div>', unsafe_allow_html=True)
                st.bar_chart(compare_df.set_index("Dataset")[["AUC", "AUPR"]], color=["#00f5d4", "#a78bfa"])
                st.markdown("</div>", unsafe_allow_html=True)
            with c2:
                st.markdown('<div class="glass-card">', unsafe_allow_html=True)
                st.markdown('<div style="font-size:0.9rem;font-weight:700;color:#00b4d8;margin-bottom:0.6rem;">F1 / MCC / Accuracy</div>', unsafe_allow_html=True)
                st.bar_chart(compare_df.set_index("Dataset")[["F1", "MCC", "Accuracy"]], color=["#00b4d8", "#fbbf24", "#4ade80"])
                st.markdown("</div>", unsafe_allow_html=True)

    with tab_db:
        st.markdown("<div style='height:0.4rem'></div>", unsafe_allow_html=True)
        db_info = None
        if _API_OK:
            try:
                client = ApiClient(API_DEFAULT)
                if st.session_state.get("api_token"):
                    client.token = st.session_state["api_token"]
                db_info = client.db_status()
            except Exception as e:
                st.error(f"Không thể kiểm tra trạng thái DB: {e}")

        db_overview_tab, db_schema_tab, db_maintenance_tab = st.tabs(["Tổng quan lưu trữ", "Sơ đồ bảng", "Bảo trì & kết nối"])
        with db_overview_tab:
            st.markdown('<div class="glass-card">', unsafe_allow_html=True)
            st.markdown('<div style="font-size:0.95rem;font-weight:800;color:#00f5d4;margin-bottom:0.8rem;">Trạng thái hiện tại</div>', unsafe_allow_html=True)
            if db_info:
                source = db_info.get("source", "unknown")
                is_connected = db_info.get("is_db_connected", False)
                db_server = db_info.get("db_server", "") or "N/A"
                db_name = db_info.get("db_name", "") or "N/A"
                json_counts = db_info.get("json_counts", {}) or {}
                total_json = sum(json_counts.values())
                state_label = "SQL Server hoạt động" if is_connected and source == "mssql" else "SQLite dự phòng" if source == "sqlite" else "JSON-only / chưa có DB"
                state_color = "#4ade80" if is_connected and source == "mssql" else "#fbbf24" if source == "sqlite" else "#f87171"
                kpi_cols = st.columns(4)
                for idx, (label, value, color) in enumerate([("Nguồn dữ liệu", state_label, state_color), ("DB Server", db_server, "#00b4d8"), ("Database", db_name, "#a78bfa"), ("JSON cache", f"{total_json:,} bản ghi", "#fbbf24")]):
                    with kpi_cols[idx]:
                        st.markdown(f'<div class="metric-card" style="padding:1.1rem 1rem;"><div style="font-size:0.8rem;color:#94a3b8;text-transform:uppercase;font-weight:700;">{label}</div><div style="font-size:1rem;font-weight:800;color:{color};margin-top:0.5rem;">{value}</div></div>', unsafe_allow_html=True)
                if json_counts:
                    json_df = pd.DataFrame([{"Bảng JSON": k, "Số bản ghi": v} for k, v in sorted(json_counts.items()) if v > 0])
                    if not json_df.empty:
                        st.markdown("<div style='height:0.8rem'></div>", unsafe_allow_html=True)
                        st.dataframe(json_df, use_container_width=True, hide_index=True)
            else:
                st.warning("Không thể kết nối Backend API để đọc trạng thái DB.")
            st.markdown("</div>", unsafe_allow_html=True)

        with db_schema_tab:
            schema_cols = st.columns(len(_db_schema_groups()))
            for idx, (group_name, rows) in enumerate(_db_schema_groups().items()):
                with schema_cols[idx]:
                    st.markdown('<div class="glass-card" style="height:100%;">', unsafe_allow_html=True)
                    st.markdown(f'<div style="font-size:0.95rem;font-weight:800;color:#00f5d4;margin-bottom:0.8rem;">{group_name}</div>', unsafe_allow_html=True)
                    for table_name, desc in rows:
                        st.markdown(f'<div style="padding:0.55rem 0.7rem;margin-bottom:0.45rem;background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.07);border-radius:10px;"><div style="font-size:0.8rem;font-weight:800;color:#e2e8f0;">{table_name}</div><div style="font-size:0.76rem;color:#94a3b8;margin-top:0.18rem;line-height:1.55;">{desc}</div></div>', unsafe_allow_html=True)
                    st.markdown("</div>", unsafe_allow_html=True)

        with db_maintenance_tab:
            left_maintain, right_maintain = st.columns([1.2, 1])
            with left_maintain:
                st.markdown('<div class="glass-card">', unsafe_allow_html=True)
                st.markdown('<div style="font-size:0.95rem;font-weight:800;color:#a78bfa;margin-bottom:0.6rem;">Công cụ kết nối SQL Server</div>', unsafe_allow_html=True)
                st.markdown('<div style="font-size:0.82rem;color:#94a3b8;line-height:1.7;margin-bottom:1rem;">Công cụ sẽ bật dịch vụ SQL Server, tạo `He_Thong_Du_Doan_Thuoc`, sinh toàn bộ bảng ORM và seed tài khoản mặc định.</div><div style="background:rgba(251,191,36,0.08);border:1px solid rgba(251,191,36,0.25);border-radius:8px;padding:0.6rem 0.9rem;font-size:0.78rem;color:#fbbf24;margin-bottom:1rem;">Yêu cầu SQL Server Express đã được cài trên máy. Quá trình có thể mất 30-60 giây.</div>', unsafe_allow_html=True)
                if st.button("Chạy Cài đặt & Kết nối SQL", type="primary", use_container_width=True, key="btn_db_setup"):
                    if _API_OK and st.session_state.get("api_token"):
                        client = ApiClient(API_DEFAULT)
                        client.token = st.session_state["api_token"]
                        with st.spinner("Dang chay setup_database.py..."):
                            try:
                                setup_result = client.admin_db_setup()
                                success = setup_result.get("success", False)
                                log_output = setup_result.get("log", "")
                                error_output = setup_result.get("error", "")
                                if success:
                                    st.success("Cài đặt và kết nối SQL Server thành công.")
                                else:
                                    st.warning(f"Quá trình hoàn tất nhưng có lỗi (exit code: {setup_result.get('exit_code', '?')}).")
                                clean_log = re.sub(r"\[[0-9;]*m", "", log_output)
                                st.code(clean_log if clean_log.strip() else "(không có output)", language="text")
                                if error_output:
                                    st.code(error_output[:2000], language="text")
                            except Exception as e:
                                st.error(f"Lỗi khi chạy setup: {e}")
                    else:
                        st.error("Cần đăng nhập Admin và có kết nối API để chạy chức năng này.")
                st.markdown("</div>", unsafe_allow_html=True)
            with right_maintain:
                st.markdown('<div class="glass-card">', unsafe_allow_html=True)
                st.markdown('<div style="font-size:0.95rem;font-weight:800;color:#00b4d8;margin-bottom:0.6rem;">Gợi ý vận hành</div>', unsafe_allow_html=True)
                for tip in ["Dùng `nguoi_dung`, `thuoc`, `benh`, `protein` làm lớp dữ liệu nghiệp vụ chuẩn.", "Giữ các bảng `*_b`, `*_c`, `*_f` cho seed và đối chiếu dataset, không thay thế bảng lõi.", "JSON trong `src/data` chỉ nên là cache hoặc fallback khi DB không khả dụng.", "Ưu tiên làm mới theo dataset trước khi reset toàn bộ dữ liệu lõi."]:
                    st.markdown(f'<div style="padding:0.55rem 0.7rem;margin-bottom:0.45rem;background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.07);border-radius:10px;font-size:0.8rem;color:#cbd5e1;line-height:1.6;">{tip}</div>', unsafe_allow_html=True)
                if st.button("Làm mới trạng thái", use_container_width=True, key="btn_db_refresh"):
                    st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)


# =============================================================================
# TRANG: SO SANH MODEL (User / Expert / Admin)
# =============================================================================
def _load_kfold_metrics() -> dict:
    """Đọc kfold_metrics.json của cả 3 dataset. Trả về dict {label: data}."""
    ROOT = Path(__file__).resolve().parents[2]
    result = {}
    for label in ["B-dataset", "C-dataset", "F-dataset"]:
        fpath = ROOT / "weights" / label / "kfold_metrics.json"
        if fpath.exists():
            with open(fpath, "r", encoding="utf-8") as f:
                result[label] = json.load(f)
    return result


def render_compare_page() -> None:
    """Trang So Sánh Model — expert/admin đều xem được."""
    if not _can("expert"):
        st.markdown("""
        <div class="access-denied fade-in">
          <div style="font-size:3rem;margin-bottom:0.8rem;">📊</div>
          <div style="font-size:1.2rem;font-weight:800;margin-bottom:0.5rem;">
            Yêu cầu quyền Chuyên gia</div>
          <div style="font-size:0.88rem;color:rgba(247,37,133,0.7);">
            Vui lòng đăng nhập với quyền Chuyên gia hoặc Quản trị viên để xem trang So Sánh Model.
          </div>
        </div>
        """, unsafe_allow_html=True)
        return

    st.markdown('<div class="page-title fade-in">📊 So Sánh Model</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="page-subtitle">So sánh hiệu suất FuzzyGCN trên 3 bộ dataset — '
        'dữ liệu thực từ 10-Fold Cross Validation</div>',
        unsafe_allow_html=True,
    )
    tab_dataset, tab_model = st.tabs(["📊 So sánh Dataset", "🆚 So sánh Mô hình"])
    with tab_dataset:

        all_metrics = _load_kfold_metrics()
        if not all_metrics:
            st.warning("⚠️ Không tìm thấy file kfold_metrics.json trong thư mục weights/.")
            return

        METRICS_SHOW = ["AUC", "AUPR", "Accuracy", "Precision", "Recall", "F1", "MCC"]
        COLORS_DS = {"B-dataset": "#00f5d4", "C-dataset": "#a855f7", "F-dataset": "#fbbf24"}
        LABEL_MAP = {"B-dataset": "🔵 B", "C-dataset": "🟣 C", "F-dataset": "🟡 F"}

        # ── KPI cards: top metrics của từng dataset ─────────────────────────────
        cols_ds = st.columns(len(all_metrics))
        for i, (label, data) in enumerate(all_metrics.items()):
            color = COLORS_DS.get(label, "#00f5d4")
            mn = data.get("mean", {})
            with cols_ds[i]:
                st.markdown(f"""
                <div class="glass-card" style="border-color:{color}33;text-align:center;">
                  <div style="font-size:1rem;font-weight:800;color:{color};
                              margin-bottom:0.8rem;letter-spacing:0.05em;">{label}</div>
                  <div style="display:grid;grid-template-columns:1fr 1fr;gap:0.4rem;">
                    <div style="background:rgba(255,255,255,0.04);border-radius:8px;padding:0.4rem;">
                      <div style="font-size:1.35rem;font-weight:800;color:{color};
                        text-shadow:0 0 15px {color}55;">{mn.get('AUC',0):.4f}</div>
                      <div style="font-size:0.68rem;color:#64748b;font-weight:600;">AUC-ROC</div>
                    </div>
                    <div style="background:rgba(255,255,255,0.04);border-radius:8px;padding:0.4rem;">
                      <div style="font-size:1.35rem;font-weight:800;color:{color};
                        text-shadow:0 0 15px {color}55;">{mn.get('AUPR',0):.4f}</div>
                      <div style="font-size:0.68rem;color:#64748b;font-weight:600;">AUC-PR</div>
                    </div>
                    <div style="background:rgba(255,255,255,0.04);border-radius:8px;padding:0.4rem;">
                      <div style="font-size:1.1rem;font-weight:800;color:#e2e8f0;">{mn.get('F1',0):.4f}</div>
                      <div style="font-size:0.68rem;color:#64748b;font-weight:600;">F1</div>
                    </div>
                    <div style="background:rgba(255,255,255,0.04);border-radius:8px;padding:0.4rem;">
                      <div style="font-size:1.1rem;font-weight:800;color:#e2e8f0;">{mn.get('MCC',0):.4f}</div>
                      <div style="font-size:0.68rem;color:#64748b;font-weight:600;">MCC</div>
                    </div>
                  </div>
                </div>
                """, unsafe_allow_html=True)

        st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)

        # ── Bảng so sánh tổng hợp ──────────────────────────────────────────────
        rows = []
        for label, data in all_metrics.items():
            mn = data.get("mean", {})
            sd = data.get("std", {})
            row = {"Dataset": label, "Folds": data.get("so_fold", 10)}
            for m in METRICS_SHOW:
                row[m] = f"{mn.get(m, 0):.4f} ± {sd.get(m, 0):.4f}"
            rows.append(row)
        df_summary = pd.DataFrame(rows)

        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.markdown("""<div style="font-size:0.95rem;font-weight:800;color:#00f5d4;
                       margin-bottom:0.8rem;">📋 Bảng tổng hợp (Mean ± Std — 10-Fold CV)</div>""",
                    unsafe_allow_html=True)
        st.dataframe(df_summary, use_container_width=True, hide_index=True)
        st.markdown("</div>", unsafe_allow_html=True)

        # ── Biểu đồ bar so sánh ────────────────────────────────────────────────
        st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)
        col_bar1, col_bar2 = st.columns(2)

        with col_bar1:
            st.markdown('<div class="glass-card">', unsafe_allow_html=True)
            st.markdown("""<div style="font-size:0.9rem;font-weight:700;color:#00f5d4;
                           margin-bottom:0.6rem;">📊 AUC-ROC & AUC-PR</div>""",
                        unsafe_allow_html=True)
            bar_data_1 = {
                "Dataset": [d for d in all_metrics],
                "AUC":  [all_metrics[d]["mean"].get("AUC", 0)  for d in all_metrics],
                "AUPR": [all_metrics[d]["mean"].get("AUPR", 0) for d in all_metrics],
            }
            df_bar1 = pd.DataFrame(bar_data_1).set_index("Dataset")
            st.bar_chart(df_bar1, color=["#00f5d4", "#a78bfa"])
            st.markdown("</div>", unsafe_allow_html=True)

        with col_bar2:
            st.markdown('<div class="glass-card">', unsafe_allow_html=True)
            st.markdown("""<div style="font-size:0.9rem;font-weight:700;color:#fbbf24;
                           margin-bottom:0.6rem;">📊 F1 & MCC</div>""",
                        unsafe_allow_html=True)
            bar_data_2 = {
                "Dataset": [d for d in all_metrics],
                "F1":  [all_metrics[d]["mean"].get("F1",  0) for d in all_metrics],
                "MCC": [all_metrics[d]["mean"].get("MCC", 0) for d in all_metrics],
            }
            df_bar2 = pd.DataFrame(bar_data_2).set_index("Dataset")
            st.bar_chart(df_bar2, color=["#fbbf24", "#f472b6"])
            st.markdown("</div>", unsafe_allow_html=True)

        # ── Admin only: per-fold breakdown ─────────────────────────────────────
        if _can("admin"):
            st.markdown("<div class='neon-hr'></div>", unsafe_allow_html=True)
            st.markdown("""<div style="font-size:0.95rem;font-weight:800;color:#f72585;
                           margin:0.5rem 0 0.8rem;">👑 Chi tiết từng Fold (Admin only)</div>""",
                        unsafe_allow_html=True)

            selected_ds_cmp = st.selectbox(
                "Chọn dataset xem chi tiết",
                list(all_metrics.keys()),
                key="cmp_ds_sel",
            )
            sel_metric_cmp = st.selectbox(
                "Chọn metric",
                METRICS_SHOW,
                key="cmp_metric_sel",
            )

            data_sel = all_metrics[selected_ds_cmp]
            folds = data_sel.get("folds", [])
            if folds:
                fold_vals = {
                    f"Fold {i+1}": folds[i].get(sel_metric_cmp, 0)
                    for i in range(len(folds))
                }
                mean_v = data_sel["mean"].get(sel_metric_cmp, 0)
                std_v  = data_sel["std"].get(sel_metric_cmp, 0)

                df_fold = pd.DataFrame({
                    "Fold": list(fold_vals.keys()),
                    sel_metric_cmp: list(fold_vals.values()),
                    "Mean": [mean_v] * len(folds),
                }).set_index("Fold")

                col_fc, col_fi = st.columns([2, 1])
                with col_fc:
                    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
                    st.markdown(f"""<div style="font-size:0.88rem;font-weight:700;color:#a78bfa;
                                   margin-bottom:0.5rem;">📈 {sel_metric_cmp} theo Fold
                                   — {selected_ds_cmp}</div>""", unsafe_allow_html=True)
                    st.line_chart(df_fold, color=["#00f5d4", "#f72585"])
                    st.markdown("</div>", unsafe_allow_html=True)

                with col_fi:
                    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
                    st.markdown(f"""<div style="font-size:0.88rem;font-weight:700;color:#fbbf24;
                                   margin-bottom:0.8rem;">📐 Thống kê</div>""",
                                unsafe_allow_html=True)
                    best_fold  = max(fold_vals, key=fold_vals.get)
                    worst_fold = min(fold_vals, key=fold_vals.get)
                    best_v  = fold_vals[best_fold]
                    worst_v = fold_vals[worst_fold]
                    st.markdown(f"""
                    <div style="display:flex;flex-direction:column;gap:0.6rem;">
                      <div style="background:rgba(0,245,212,0.08);border-radius:8px;padding:0.6rem;">
                        <div style="font-size:0.7rem;color:#64748b;font-weight:600;">MEAN</div>
                        <div style="font-size:1.3rem;font-weight:800;color:#00f5d4;">{mean_v:.4f}</div>
                      </div>
                      <div style="background:rgba(255,255,255,0.04);border-radius:8px;padding:0.6rem;">
                        <div style="font-size:0.7rem;color:#64748b;font-weight:600;">STD</div>
                        <div style="font-size:1.1rem;font-weight:700;color:#94a3b8;">±{std_v:.4f}</div>
                      </div>
                      <div style="background:rgba(74,222,128,0.08);border-radius:8px;padding:0.6rem;">
                        <div style="font-size:0.7rem;color:#64748b;font-weight:600;">TỐT NHẤT</div>
                        <div style="font-size:0.85rem;font-weight:700;color:#4ade80;">
                          {best_fold}: {best_v:.4f}</div>
                      </div>
                      <div style="background:rgba(251,113,133,0.08);border-radius:8px;padding:0.6rem;">
                        <div style="font-size:0.7rem;color:#64748b;font-weight:600;">KÉM NHẤT</div>
                        <div style="font-size:0.85rem;font-weight:700;color:#fb7185;">
                          {worst_fold}: {worst_v:.4f}</div>
                      </div>
                    </div>
                    """, unsafe_allow_html=True)
                    st.markdown("</div>", unsafe_allow_html=True)

                # Bảng chi tiết từng fold
                st.markdown('<div class="glass-card" style="margin-top:0.5rem;">', unsafe_allow_html=True)
                st.markdown(f"""<div style="font-size:0.88rem;font-weight:700;color:#00b4d8;
                               margin-bottom:0.5rem;">🔢 Bảng chi tiết tất cả metric — mỗi fold</div>""",
                            unsafe_allow_html=True)
                fold_rows = []
                for i, f in enumerate(folds):
                    row = {"Fold": f"Fold {i+1}"}
                    for m in METRICS_SHOW:
                        row[m] = round(f.get(m, 0), 4)
                    fold_rows.append(row)
                df_fold_all = pd.DataFrame(fold_rows).set_index("Fold")
                st.dataframe(
                    df_fold_all.style.highlight_max(axis=0, color="rgba(0,245,212,0.2)")
                                     .highlight_min(axis=0, color="rgba(247,37,133,0.12)"),
                    use_container_width=True,
                )
                st.markdown("</div>", unsafe_allow_html=True)


    with tab_model:
        st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.markdown("""<div style="font-size:0.95rem;font-weight:800;color:#00f5d4;
                       margin-bottom:0.8rem;">🆚 So sánh mô hình (Tùy chọn vs Hệ thống)</div>""",
                    unsafe_allow_html=True)
        
        st.markdown("Vui lòng tải lên tệp `.pth` của model tùy chọn và/hoặc tệp `.pth` của model hệ thống để đánh giá thực tế.")
        
        cmp_dataset = st.selectbox("📂 Chọn Dataset để đánh giá", ["B-dataset", "C-dataset", "F-dataset"], key="cmp_eval_ds")
        
        col_up1, col_up2 = st.columns(2)
        with col_up1:
            uploaded_file_custom = st.file_uploader("1. Tải lên file model tùy chọn (.pth hoặc .json)", type=["pth", "json"], key="custom_uploader")
            custom_model_name = st.text_input("Tên Model Tùy chọn", value="Model Tùy chọn", placeholder="Nhập tên model...")
        with col_up2:
            uploaded_file_system = st.file_uploader("2. Tải lên file model hệ thống (.pth) - Tùy chọn", type=["pth"], key="system_uploader")
            
        if uploaded_file_custom is not None:
            if uploaded_file_custom.name.endswith(".pth"):
                if st.button("🔍 Phân tích cấu trúc file .pth (Inspect)", key="inspect_btn"):
                    client = ApiClient(API_DEFAULT)
                    if st.session_state.get("api_token"):
                        client.token = st.session_state["api_token"]
                    with st.spinner("Đang đọc file .pth..."):
                        try:
                            info = client.inspect_model(uploaded_file_custom.getvalue(), uploaded_file_custom.name)
                            if "error" in info:
                                st.error(f"Lỗi: {info['error']}")
                            else:
                                st.success(f"✅ Nhận diện mô hình: **{info.get('model_type', 'Unknown')}**")
                                st.info(f"Tổng số tham số (Parameters): **{info.get('total_parameters', 0):,}**")
                                with st.expander("📄 Chi tiết các Layer trong file .pth"):
                                    layers = info.get("layers", [])
                                    if layers:
                                        df_layers = pd.DataFrame(layers)
                                        st.dataframe(df_layers, use_container_width=True)
                                    else:
                                        st.write("Không tìm thấy layer nào.")
                        except Exception as e:
                            st.error(f"Lỗi kết nối API: {e}")

            if st.button("🚀 Chạy Đánh Giá Model", type="primary"):
                # Nếu là file JSON (đã có kết quả)
                if uploaded_file_custom.name.endswith(".json"):
                    import json
                    try:
                        custom_json = json.loads(uploaded_file_custom.getvalue().decode("utf-8"))
                        uploaded_metrics = {}
                        # Lấy các chỉ số từ mục 'mean' nếu có, hoặc lấy trực tiếp
                        mean_data = custom_json.get("mean", custom_json)
                        for m in ["AUC", "AUPR", "Accuracy", "Precision", "Recall", "F1", "MCC"]:
                            # Tìm các key khác nhau (ví dụ: 'mean_AUC', 'AUC')
                            val = mean_data.get(m, custom_json.get(f"mean_{m}", 0))
                            uploaded_metrics[m] = val
                            
                        # Ghi đè tên model nếu trong JSON có
                        if "model" in custom_json and custom_model_name == "Model Tùy chọn":
                            custom_model_name = custom_json["model"]
                            
                        st.success(f"Đã tải kết quả đánh giá từ file JSON thành công (Model: {custom_model_name})")
                    except Exception as e:
                        st.error(f"Lỗi khi đọc file JSON: {e}")
                        uploaded_metrics = None
                else:
                    if not _API_OK:
                        st.error("❌ Không thể kết nối API Backend.")
                        return
                    client = ApiClient(API_DEFAULT)
                    if st.session_state.get("api_token"):
                        client.token = st.session_state["api_token"]
                        
                    with st.spinner("Đang chạy inference để đánh giá model tùy chọn..."):
                        try:
                            res_custom = client.evaluate_model(uploaded_file_custom.getvalue(), uploaded_file_custom.name, cmp_dataset)
                            uploaded_metrics = res_custom.get("metrics", {})
                        except Exception as e:
                            st.error(f"Lỗi khi đánh giá model tùy chọn: {e}")
                            uploaded_metrics = None
                        
                system_model_metrics = None
                if uploaded_file_system is not None:
                    with st.spinner("Đang chạy inference để đánh giá model hệ thống..."):
                        try:
                            res_sys = client.evaluate_model(uploaded_file_system.getvalue(), uploaded_file_system.name, cmp_dataset)
                            system_model_metrics = res_sys.get("metrics", {})
                        except Exception as e:
                            st.error(f"Lỗi khi đánh giá model hệ thống: {e}")
                else:
                    # Nếu không upload model hệ thống, lấy metrics tốt nhất từ JSON
                    best_auc = 0
                    if 'all_metrics' in locals() and all_metrics and cmp_dataset in all_metrics:
                        data = all_metrics[cmp_dataset]
                        for fold in data.get('folds', []):
                            if fold.get('AUC', 0) > best_auc:
                                best_auc = fold.get('AUC', 0)
                                system_model_metrics = {m: fold.get(m, 0) for m in ["AUC", "AUPR", "Accuracy", "Precision", "Recall", "F1", "MCC"]}

                if uploaded_metrics:
                    st.markdown("<div class='neon-hr'></div>", unsafe_allow_html=True)
                    
                    compare_rows = []
                    compare_rows.append({"Model": custom_model_name, **uploaded_metrics})
                    if system_model_metrics:
                        compare_rows.append({"Model": "MedLink_AI", **system_model_metrics})
                    df_model_comp = pd.DataFrame(compare_rows)
                    
                    st.markdown("""<div style="font-size:0.9rem;font-weight:700;color:#00f5d4;
                                   margin-bottom:0.6rem;">📋 Bảng chi tiết Metrics</div>""",
                                unsafe_allow_html=True)
                    st.dataframe(df_model_comp, use_container_width=True, hide_index=True)
                    
                    st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)
                    st.markdown("""<div style="font-size:0.9rem;font-weight:700;color:#fbbf24;
                                   margin-bottom:0.6rem;">📊 Biểu đồ so sánh</div>""",
                                unsafe_allow_html=True)
                    
                    df_pivot = df_model_comp.set_index("Model").T
                    st.bar_chart(df_pivot, color=["#f472b6", "#00f5d4"][:len(compare_rows)])


        st.markdown("</div>", unsafe_allow_html=True)


# =============================================================================
# TRANG: QUẢN LÝ TÀI KHOẢN (Admin only)
# =============================================================================
def render_account_management_page() -> None:
    """Trang quan ly tai khoan va lich su du doan cho Admin."""
    if not _can("admin"):
        st.markdown("""
        <div class="access-denied fade-in">
          <div style="font-size:3rem;margin-bottom:0.8rem;">ADMIN</div>
          <div style="font-size:1.2rem;font-weight:800;margin-bottom:0.5rem;">Yêu cầu quyền Admin</div>
          <div style="font-size:0.88rem;color:rgba(247,37,133,0.7);">Trang này chỉ dành cho <strong>Quản trị viên</strong>.</div>
        </div>
        """, unsafe_allow_html=True)
        return

    users = _load_json_records("users.json")
    history_rows = _load_json_records("prediction_history.json")

    st.markdown('<div class="page-title fade-in">Quản Trị Hệ Thống</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-subtitle">Sắp xếp lại khu quản trị theo 2 phần rõ ràng: tài khoản và lịch sử tra cứu</div>', unsafe_allow_html=True)

    total_users = len(users)
    total_admins = sum(1 for u in users if str(u.get("role", "")).lower() == "admin")
    total_experts = sum(1 for u in users if str(u.get("role", "")).lower() in {"expert", "researcher"})
    total_standard = total_users - total_admins - total_experts
    kpi_cols = st.columns(4)
    for idx, (label, value, color) in enumerate([("Tài khoản", total_users, "#00f5d4"), ("Admin", total_admins, "#f72585"), ("Chuyên gia", total_experts, "#a78bfa"), ("Người dùng", total_standard, "#00b4d8")]):
        with kpi_cols[idx]:
            st.markdown(f'<div class="metric-card"><div class="metric-value" style="color:{color};text-shadow:0 0 20px {color}55;">{value}</div><div class="metric-label">{label}</div></div>', unsafe_allow_html=True)

    tab_users, tab_history = st.tabs(["Quản Lý Tài Khoản", "Lịch Sử Tra Cứu"])

    with tab_users:
        left_col, right_col = st.columns([1.25, 1])
        with left_col:
            st.markdown('<div class="glass-card">', unsafe_allow_html=True)
            st.markdown('<div style="font-size:0.95rem;font-weight:800;color:#00f5d4;margin-bottom:0.8rem;">Danh sách tài khoản</div>', unsafe_allow_html=True)
            if users:
                df_users = pd.DataFrame(users)
                display_cols = [c for c in ["id", "username", "email", "role"] if c in df_users.columns]
                st.dataframe(df_users[display_cols], use_container_width=True, hide_index=True, height=420)
            else:
                st.info("Chưa có dữ liệu tài khoản.")
            st.markdown("</div>", unsafe_allow_html=True)

        with right_col:
            st.markdown('<div class="glass-card">', unsafe_allow_html=True)
            action_tabs = st.tabs(["Thêm", "Sửa", "Xóa"])
            with action_tabs[0]:
                with st.form("form_add_user"):
                    new_user = st.text_input("Tên đăng nhập")
                    new_email = st.text_input("Email")
                    new_role = st.selectbox("Vai trò", ["user", "expert", "admin"])
                    new_pass = st.text_input("Mật khẩu", type="password")
                    submitted = st.form_submit_button("Thêm tài khoản", type="primary", use_container_width=True)
                    if submitted:
                        if not new_user.strip() or not new_pass:
                            st.error("Vui lòng nhập tên đăng nhập và mật khẩu.")
                        elif any(str(u.get("username", "")).lower() == new_user.strip().lower() for u in users):
                            st.error("Tên đăng nhập đã tồn tại.")
                        else:
                            new_id = max([int(u.get("id", 0)) for u in users] + [0]) + 1
                            users.append({"id": new_id, "username": new_user.strip(), "email": new_email.strip(), "role": new_role, "password_hash": auth_hash_password(new_pass)})
                            _save_json_records("users.json", users)
                            try:
                                from backend.app.database import SessionLocal
                                from backend.app.models import User
                                from data.data_source_status import data_source
                                if data_source.is_db_connected():
                                    with SessionLocal() as db:
                                        new_db_user = User(
                                            username=new_user.strip(),
                                            email=new_email.strip(),
                                            password_hash=auth_hash_password(new_pass),
                                            role=new_role
                                        )
                                        db.add(new_db_user)
                                        db.commit()
                            except Exception as e:
                                print("Error updating SQL DB:", e)
                            st.success(f"Đã thêm tài khoản `{new_user.strip()}`.")
                            st.rerun()

            with action_tabs[1]:
                if users:
                    usernames = [u.get("username", "") for u in users if u.get("username")]
                    selected_user = st.selectbox("Chọn tài khoản", usernames, key="admin_edit_username")
                    target = next((u for u in users if u.get("username") == selected_user), None)
                    if target:
                        with st.form("form_edit_user"):
                            edit_email = st.text_input("Email", value=target.get("email", ""))
                            current_role = target.get("role", "user")
                            role_options = ["user", "expert", "admin"]
                            role_index = role_options.index(current_role) if current_role in role_options else 0
                            edit_role = st.selectbox("Vai trò", role_options, index=role_index)
                            edit_pass = st.text_input("Mật khẩu mới", type="password", help="Để trống nếu không đổi")
                            submitted_edit = st.form_submit_button("Cập nhật", type="primary", use_container_width=True)
                            if submitted_edit:
                                target["email"] = edit_email.strip()
                                target["role"] = edit_role
                                if edit_pass:
                                    target["password_hash"] = auth_hash_password(edit_pass)
                                _save_json_records("users.json", users)
                                try:
                                    from backend.app.database import SessionLocal
                                    from backend.app.models import User
                                    from data.data_source_status import data_source
                                    if data_source.is_db_connected():
                                        with SessionLocal() as db:
                                            db_user = db.query(User).filter(User.username == selected_user).first()
                                            if db_user:
                                                db_user.email = edit_email.strip()
                                                db_user.role = edit_role
                                                if edit_pass:
                                                    db_user.password_hash = target["password_hash"]
                                                db.commit()
                                except Exception as e:
                                    print("Error updating SQL DB:", e)
                                st.success(f"Đã cập nhật `{selected_user}`.")
                                st.rerun()
                else:
                    st.info("Chưa có tài khoản để chỉnh sửa.")

            with action_tabs[2]:
                current_user = st.session_state.get("username", "")
                deletable = [u.get("username", "") for u in users if u.get("username") and u.get("username") != current_user]
                if deletable:
                    selected_del = st.selectbox("Chọn tài khoản cần xóa", deletable, key="admin_delete_username")
                    st.caption("Tài khoản đang đăng nhập không được phép tự xóa.")
                    if st.button("Xóa tài khoản", type="primary", use_container_width=True, key="btn_delete_user"):
                        updated_users = [u for u in users if u.get("username") != selected_del]
                        _save_json_records("users.json", updated_users)
                        try:
                            from backend.app.database import SessionLocal
                            from backend.app.models import User
                            from data.data_source_status import data_source
                            if data_source.is_db_connected():
                                with SessionLocal() as db:
                                    db.query(User).filter(User.username == selected_del).delete()
                                    db.commit()
                        except Exception as e:
                            print("Error updating SQL DB:", e)
                        st.success(f"Đã xóa `{selected_del}`.")
                        st.rerun()
                else:
                    st.info("Không có tài khoản phù hợp để xóa.")
            st.markdown("</div>", unsafe_allow_html=True)

    with tab_history:
        df_history = _flatten_history_rows(history_rows, users)
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.markdown('<div style="font-size:0.95rem;font-weight:800;color:#00f5d4;margin-bottom:0.8rem;">Lịch sử dự đoán</div>', unsafe_allow_html=True)
        if df_history.empty:
            st.info("Chưa có dữ liệu lịch sử dự đoán.")
        else:
            filter_cols = st.columns([1.2, 1, 1])
            with filter_cols[0]:
                user_filter = st.selectbox("Người dùng", ["Tất cả"] + sorted(df_history["Nguoi dung"].dropna().astype(str).unique().tolist()), key="history_user_filter")
            with filter_cols[1]:
                query_filter = st.selectbox("Loại truy vấn", ["Tất cả"] + sorted(df_history["Loai truy van"].dropna().astype(str).unique().tolist()), key="history_query_filter")
            with filter_cols[2]:
                search_term = st.text_input("Tìm từ khóa", key="history_search_term")

            filtered_history = df_history.copy()
            if user_filter != "Tất cả":
                filtered_history = filtered_history[filtered_history["Nguoi dung"] == user_filter]
            if query_filter != "Tất cả":
                filtered_history = filtered_history[filtered_history["Loai truy van"] == query_filter]
            if search_term.strip():
                mask = filtered_history["Tu khoa"].astype(str).str.contains(search_term.strip(), case=False, na=False)
                filtered_history = filtered_history[mask]

            history_kpis = st.columns(3)
            history_kpis[0].metric("Tong luot hien thi", len(filtered_history))
            history_kpis[1].metric("Thuoc -> Benh", int((filtered_history["Loai truy van"] == "Thuoc -> Benh").sum()))
            history_kpis[2].metric("Benh -> Thuoc", int((filtered_history["Loai truy van"] == "Benh -> Thuoc").sum()))
            st.markdown("<div style='height:0.6rem'></div>", unsafe_allow_html=True)
            st.dataframe(filtered_history, use_container_width=True, hide_index=True, height=460)
        st.markdown("</div>", unsafe_allow_html=True)


# =============================================================================
# ENTRY POINT CHÍNH
# =============================================================================

def render_landing_page() -> None:
    """Render trang chủ công khai với form đăng nhập và chọn demo role."""

    # CSS landing: ẩn hoàn toàn sidebar (chỉ trang này)
    st.markdown("""
    <style>
    section[data-testid="stSidebar"] { display: none !important; }
    .main .block-container {
      padding-top: 0 !important;
      padding-left: 0 !important;
      padding-right: 0 !important;
      max-width: 100% !important;
    }
    </style>
    """, unsafe_allow_html=True)

    # ── NAVBAR CỐ ĐỊNH ────────────────────────────────────────────────────────
    st.markdown("""
    <div style="
      position:fixed; top:0; left:0; right:0; z-index:9999;
      display:flex; align-items:center; justify-content:space-between;
      padding:0 2.5rem; height:62px;
      background:rgba(10,15,30,0.95); backdrop-filter:blur(16px);
      border-bottom:1px solid rgba(0,245,212,0.15);
      box-shadow:0 2px 24px rgba(0,0,0,0.4);
    ">
      <div style="font-size:1.25rem;font-weight:900;color:#00f5d4;
                  text-shadow:0 0 20px rgba(0,245,212,0.5);letter-spacing:-0.03em;">
        💊 <span style="color:#e2e8f0;">MedLink</span> AI
      </div>
      <div style="display:flex;gap:0.5rem;align-items:center;">
        <span style="padding:0.3rem 1rem;color:rgba(255,255,255,0.65);
                     font-size:0.85rem;">FuzzyGCN · Drug–Disease AI</span>
        <span style="
          padding:0.35rem 1.1rem;
          background:linear-gradient(90deg,#00f5d4,#00b4d8);
          color:#0a0f1e; border-radius:8px;
          font-size:0.84rem; font-weight:800;
        ">v2.0</span>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # ── TOP RIGHT BUTTONS ─────────────────────────────────────────────────────
    st.markdown("""
    <style>
    div[data-testid="stHorizontalBlock"] {
        margin-top: -40px !important;
        margin-bottom: -15px !important;
    }
    div[data-testid="stHorizontalBlock"] button {
        padding: 0.1rem 0.5rem !important;
        font-size: 0.8rem !important;
        min-height: 30px !important;
        height: 30px !important;
        white-space: nowrap !important;
    }
    </style>
    <div style='height:55px'></div>
    """, unsafe_allow_html=True)
    _, col_btn1, col_btn2 = st.columns([6.8, 1.6, 1.6])
    with col_btn1:
        if st.button("🔑 Đăng nhập / Đăng ký", use_container_width=True):
            render_login_dialog()
    with col_btn2:
        if st.button("🚀 Khám Phá", use_container_width=True, type="primary"):
            st.session_state["guest_workspace"] = True
            st.rerun()

    # ── HERO SECTION ──────────────────────────────────────────────────────────
    st.markdown("""
    <div style="
      min-height:calc(100vh - 120px); display:flex; align-items:center; justify-content:center;
      padding:20px 2rem 4rem; position:relative; overflow:hidden;
    ">
      <!-- Vòng trang trí nền -->
      <div style="position:absolute;top:-100px;right:-80px;width:500px;height:500px;
                  border-radius:50%;border:1px solid rgba(0,245,212,0.08);
                  background:radial-gradient(circle,rgba(0,245,212,0.04) 0%,transparent 70%);"></div>
      <div style="position:absolute;bottom:40px;left:-60px;width:300px;height:300px;
                  border-radius:50%;border:1px solid rgba(0,180,216,0.08);
                  background:radial-gradient(circle,rgba(0,180,216,0.04) 0%,transparent 70%);"></div>
      <!-- Nội dung chính -->
      <div style="position:relative;z-index:2;text-align:center;max-width:820px;">
        <div style="
          display:inline-block;background:rgba(0,245,212,0.1);
          border:1px solid rgba(0,245,212,0.3);color:#00f5d4;
          border-radius:999px;padding:0.3rem 1.2rem;
          font-size:0.75rem;font-weight:700;letter-spacing:0.12em;
          text-transform:uppercase;margin-bottom:1.4rem;
          box-shadow:0 0 20px rgba(0,245,212,0.15);
        ">⚡ Powered by FuzzyGCN · Graph Neural Network</div>
        <h1 style="
          font-size:clamp(2.4rem,5.5vw,3.8rem);font-weight:900;
          color:#e2e8f0;line-height:1.12;
          margin:0 0 1.1rem;letter-spacing:-0.04em;
        ">
          Dự Đoán <span style="
            background:linear-gradient(90deg,#00f5d4,#00b4d8);
            -webkit-background-clip:text;-webkit-text-fill-color:transparent;
          ">Liên Kết</span><br>Thuốc – Bệnh
        </h1>
        <p style="font-size:1.05rem;color:rgba(226,232,240,0.8);line-height:1.8;
                  margin:0 0 2.5rem;">
          Hệ thống AI sử dụng <strong style="color:#00f5d4;">FuzzyGCN</strong> kết hợp logic mờ và
          mạng nơ-ron đồ thị để khám phá các liên kết tiềm năng giữa Thuốc, Bệnh và Protein.
        </p>
        <!-- Thống kê nhanh -->
        <div style="display:flex;gap:3rem;justify-content:center;flex-wrap:wrap;
                    margin-bottom:3rem;">
          <div>
            <div style="font-size:2.2rem;font-weight:900;color:#00f5d4;
                        text-shadow:0 0 20px rgba(0,245,212,0.4);">1,373</div>
            <div style="font-size:0.75rem;color:rgba(255,255,255,0.55);
                        text-transform:uppercase;letter-spacing:0.08em;margin-top:0.2rem;">Thuốc</div>
          </div>
          <div>
            <div style="font-size:2.2rem;font-weight:900;color:#00b4d8;
                        text-shadow:0 0 20px rgba(0,180,216,0.4);">5,603</div>
            <div style="font-size:0.75rem;color:rgba(255,255,255,0.55);
                        text-transform:uppercase;letter-spacing:0.08em;margin-top:0.2rem;">Bệnh</div>
          </div>
          <div>
            <div style="font-size:2.2rem;font-weight:900;color:#a78bfa;
                        text-shadow:0 0 20px rgba(124,58,237,0.4);">13,384</div>
            <div style="font-size:0.75rem;color:rgba(255,255,255,0.55);
                        text-transform:uppercase;letter-spacing:0.08em;margin-top:0.2rem;">Protein</div>
          </div>
          <div>
            <div style="font-size:2.2rem;font-weight:900;color:#f72585;
                        text-shadow:0 0 20px rgba(247,37,133,0.4);">96.3%</div>
            <div style="font-size:0.75rem;color:rgba(255,255,255,0.55);
                        text-transform:uppercase;letter-spacing:0.08em;margin-top:0.2rem;">AUC ROC</div>
          </div>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)


# =============================================================================
# ENTRY POINT CHÍNH
# =============================================================================
def main() -> None:
    """Hàm điều phối chính — routing theo role và menu."""

    # Inject CSS toàn cục
    st.markdown(GLOBAL_CSS, unsafe_allow_html=True)
    st.markdown(_BG_DECO_HTML, unsafe_allow_html=True)

    # Khởi tạo session mặc định
    if "demo_role" not in st.session_state:
        st.session_state["demo_role"] = "guest"
    if "username" not in st.session_state:
        st.session_state["username"] = "Khách"

    # ── Khôi phục session sau F5 từ URL query params ──────────────────────────
    _restore_session_from_url()


    # ── Đã đăng nhập → Sidebar CỐ ĐỊNH luôn hiển thị, không toggle được ──────
    st.markdown("""
    <style>
    /* Force sidebar luôn mở, cố định chiều rộng */
    section[data-testid="stSidebar"] {
        display: flex !important;
        min-width: 21rem !important;
        max-width: 21rem !important;
        width: 21rem !important;
        transform: none !important;
        position: relative !important;
        flex-shrink: 0 !important;
    }
    section[data-testid="stSidebar"] > div:first-child {
        display: flex !important;
        min-width: 21rem !important;
        width: 21rem !important;
        opacity: 1 !important;
        pointer-events: auto !important;
        overflow-y: auto !important;
    }
    /* Ẩn TẤT CẢ nút toggle sidebar */
    [data-testid="collapsedControl"]        { display: none !important; }
    [data-testid="stSidebarCollapseButton"] { display: none !important; }
    button[data-testid="baseButton-headerNoPadding"] { display: none !important; }
    /* Điều chỉnh layout chính cho phù hợp sidebar cố định */
    .main { margin-left: 0 !important; }
    </style>
    """, unsafe_allow_html=True)
    selected_menu = render_sidebar()

    # Nếu là guest và chưa vào workspace → hiện landing page
    if _role() == "guest" and not st.session_state.get("guest_workspace", False):
        render_landing_page()
        return

    # Routing theo menu được chọn
    if "Tổng quan" in selected_menu:
        render_intro_page()

    elif "Tra cứu" in selected_menu:
        render_catalog_page()

    elif "Trạm Dự Đoán" in selected_menu:
        render_prediction_page()

    elif "Lưới Sinh Học" in selected_menu:
        render_network_page()

    elif "So Sánh Model" in selected_menu:
        render_compare_page()

    elif "Duyệt Liên Kết" in selected_menu:
        render_review_page()

    elif "Cấu Hình" in selected_menu:
        render_config_page()

    elif "Quản Lý Tài Khoản" in selected_menu:
        render_account_management_page()

    else:
        render_intro_page()






# ── Xử lý guest vào thẳng workspace ──────────────────────────────────────────
# Khi guest nhấn "Vào với tư cách Khách", ta set flag guest_workspace
# để bỏ qua landing page và hiện sidebar (chỉ với quyền guest)
_original_role = st.session_state.get("demo_role", "guest")
if _original_role == "guest" and st.session_state.get("guest_workspace", False):
    pass  # sẽ được xử lý trong main()

if __name__ == "__main__":
    main()
