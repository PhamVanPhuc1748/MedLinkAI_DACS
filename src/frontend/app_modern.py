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
import sys
import tempfile
from pathlib import Path

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

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


def _role() -> str:
    """Lấy vai trò hiện tại từ session_state."""
    return st.session_state.get("demo_role", "guest")


def _can(min_role: str) -> bool:
    """Kiểm tra người dùng có đủ quyền tối thiểu không."""
    return ROLE_LEVELS.get(_role(), 0) >= ROLE_LEVELS.get(min_role, 999)


def _is_logged_in() -> bool:
    """Giả lập trạng thái đăng nhập: guest = chưa đăng nhập."""
    return _role() != "guest"


# =============================================================================
# COMPONENT — TRANG LANDING / ĐĂNG NHẬP (giữ nguyên đồ họa)
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

    # ── HERO SECTION ──────────────────────────────────────────────────────────
    st.markdown("""
    <div style="
      min-height:100vh; display:flex; align-items:center; justify-content:center;
      background:linear-gradient(135deg, #0a0f1e 0%, #0d1a35 50%, #08101e 100%);
      padding:80px 2rem 4rem; position:relative; overflow:hidden;
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

    # ── FORM ĐĂNG NHẬP ────────────────────────────────────────────────────────
    st.markdown("<div style='height:2rem'></div>", unsafe_allow_html=True)

    # Căn giữa form bằng cột Streamlit
    _, col_form, _ = st.columns([1, 1.4, 1])
    with col_form:
        st.markdown("""
        <div class="glass-card fade-in" style="
          border:1px solid rgba(0,245,212,0.25);
          box-shadow:0 0 40px rgba(0,245,212,0.08), 0 8px 48px rgba(0,0,0,0.5);
          padding:2.2rem 2rem;
        ">
          <div style="text-align:center;margin-bottom:1.6rem;">
            <div style="font-size:2.8rem;line-height:1;">💊</div>
            <div style="font-size:1.45rem;font-weight:900;
                        color:#00f5d4;margin-top:0.4rem;letter-spacing:-0.03em;
                        text-shadow:0 0 20px rgba(0,245,212,0.3);">MedLink AI</div>
            <div style="font-size:0.76rem;color:#64748b;
                        text-transform:uppercase;letter-spacing:0.08em;margin-top:0.2rem;">
              FuzzyGCN · Đăng nhập hệ thống</div>
          </div>
        </div>
        """, unsafe_allow_html=True)

        # Tab chọn đăng nhập / đăng ký (giao diện giả lập)
        tab_login, tab_register, tab_guest = st.tabs(["🔑 Đăng nhập", "📝 Đăng ký", "👤 Vào nhanh"])

        with tab_login:
            # --- Demo: chọn role để giả lập đăng nhập ---
            st.markdown("""
            <div style="background:rgba(0,245,212,0.06);border:1px dashed rgba(0,245,212,0.25);
                        border-radius:10px;padding:0.8rem 1rem;font-size:0.82rem;
                        color:rgba(226,232,240,0.7);margin-bottom:1rem;">
              🧪 <strong style="color:#00f5d4;">Demo Mode</strong> — Chọn vai trò để trải nghiệm phân quyền.
            </div>
            """, unsafe_allow_html=True)

            demo_role_map = {
                "🩺 Bác sĩ (User)":       "user",
                "🔬 Chuyên gia (Expert)":  "expert",
                "👑 Quản trị (Admin)":     "admin",
            }
            chosen_label = st.selectbox(
                "Vai trò demo",
                list(demo_role_map.keys()),
                key="landing_role_select",
                label_visibility="collapsed",
            )
            username_in = st.text_input("Tên đăng nhập", value="demo_user",
                                        placeholder="Nhập tên đăng nhập...")
            password_in = st.text_input("Mật khẩu", type="password",
                                        value="••••••••",
                                        placeholder="Nhập mật khẩu...")

            if st.button("🚀 Đăng nhập", use_container_width=True, type="primary",
                         key="btn_demo_login"):
                if username_in.strip():
                    st.session_state["demo_role"] = demo_role_map[chosen_label]
                    st.session_state["username"]  = username_in.strip()
                    st.rerun()
                else:
                    st.error("Vui lòng nhập tên đăng nhập.")

        with tab_register:
            st.markdown("""
            <div style="background:rgba(124,58,237,0.08);border:1px solid rgba(124,58,237,0.25);
                        border-radius:10px;padding:0.8rem 1rem;font-size:0.83rem;color:#a78bfa;">
              📋 Chức năng đăng ký đang được phát triển. Vui lòng dùng Demo Mode.
            </div>
            """, unsafe_allow_html=True)
            st.text_input("Email", placeholder="email@hospital.vn")
            st.text_input("Họ và tên", placeholder="Nguyễn Văn A")
            st.text_input("Mật khẩu mới", type="password", placeholder="••••••••")
            if st.button("📝 Gửi yêu cầu đăng ký", use_container_width=True, key="btn_register"):
                st.info("✉️ Yêu cầu đã được gửi đến quản trị viên. Vui lòng chờ phê duyệt.")

        with tab_guest:
            st.markdown("""
            <div style="background:rgba(148,163,184,0.08);border:1px solid rgba(148,163,184,0.2);
                        border-radius:10px;padding:0.9rem 1rem;font-size:0.83rem;color:#94a3b8;
                        margin-bottom:1rem;">
              👤 Chế độ <strong>Khách</strong> — Chỉ xem trang Giới thiệu và Tra cứu danh mục.
              Không có quyền dùng AI dự đoán hoặc xem lịch sử.
            </div>
            """, unsafe_allow_html=True)
            if st.button("🚪 Vào với tư cách Khách", use_container_width=True,
                         key="btn_guest_enter"):
                st.session_state["demo_role"]       = "guest"
                st.session_state["username"]        = "Khách"
                st.session_state["guest_workspace"] = True  # bỏ qua landing page
                st.rerun()

    # ── SECTION TÍNH NĂNG ────────────────────────────────────────────────────
    st.markdown("<div style='height:2.5rem'></div>", unsafe_allow_html=True)
    st.markdown("""
    <div style="text-align:center;padding:1rem 2rem 2rem;">
      <div style="font-size:clamp(1.4rem,2.5vw,2rem);font-weight:800;
                  background:linear-gradient(90deg,#00f5d4,#00b4d8);
                  -webkit-background-clip:text;-webkit-text-fill-color:transparent;
                  margin-bottom:0.5rem;">Tính năng nổi bật</div>
      <div style="color:#64748b;font-size:0.9rem;">
        Hệ sinh thái AI toàn diện cho nghiên cứu Dược - Bệnh</div>
    </div>
    """, unsafe_allow_html=True)

    feat_cols = st.columns(4)
    features = [
        ("🧠", "FuzzyGCN Model", "Graph Neural Network kết hợp logic mờ, AUC > 96%"),
        ("🔗", "Lưới Sinh Học", "Trực quan hóa tương tác Thuốc–Bệnh–Protein"),
        ("🛡️", "Phân Quyền RBAC", "4 cấp vai trò: Khách, Bác sĩ, Chuyên gia, Admin"),
        ("📊", "Phân Tích Sâu", "Biểu đồ hiệu suất mô hình và tinh chỉnh siêu tham số"),
    ]
    for i, (icon, title, desc) in enumerate(features):
        with feat_cols[i]:
            st.markdown(f"""
            <div class="glass-card" style="text-align:center;height:180px;
              border:1px solid rgba(0,245,212,0.15);transition:all 0.3s ease;">
              <div style="font-size:2.2rem;margin-bottom:0.7rem;">{icon}</div>
              <div style="font-size:0.95rem;font-weight:800;color:#e2e8f0;
                          margin-bottom:0.5rem;">{title}</div>
              <div style="font-size:0.8rem;color:#64748b;line-height:1.55;">{desc}</div>
            </div>
            """, unsafe_allow_html=True)


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

        # ── Thông tin người dùng ───────────────────────────────────────────────
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
        # Tất cả các role đều thấy: Giới thiệu, Tra cứu
        menu_items   = ["🏠 Giới thiệu", "📚 Tra cứu"]
        menu_icons   = ["house-fill", "search"]

        if _can("user"):     # User, Expert, Admin
            menu_items  += ["⚗️ Trạm Dự Đoán"]
            menu_icons  += ["activity"]
        menu_items      += ["🌐 Lưới Sinh Học"]
        menu_icons      += ["diagram-3-fill"]

        if _can("user"):     # User, Expert, Admin
            menu_items  += ["📊 So Sánh Model"]
            menu_icons  += ["bar-chart-line-fill"]

        if _can("expert"):   # Expert, Admin
            menu_items  += ["✅ Duyệt Liên Kết"]
            menu_icons  += ["check2-circle"]

        if _can("admin"):    # Admin only
            menu_items  += ["⚙️ Cấu Hình & Metrics"]
            menu_icons  += ["sliders"]

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
            selected = st.radio(
                "Menu",
                menu_items,
                key="sidebar_menu_fallback",
                label_visibility="collapsed",
            )

        st.markdown("<div class='neon-hr'></div>", unsafe_allow_html=True)

        # ── Nút đăng xuất ─────────────────────────────────────────────────────
        if st.button("🚪 Đăng xuất", use_container_width=True, key="btn_signout"):
            for k in ["demo_role", "username", "sidebar_menu", "sidebar_menu_fallback",
                      "guest_workspace", "pred_results", "pred_query_label",
                      "review_statuses", "saved_config"]:
                st.session_state.pop(k, None)
            st.rerun()

        # ── Selector test role (cuối sidebar) ─────────────────────────────────
        st.markdown("<div class='neon-hr'></div>", unsafe_allow_html=True)
        st.markdown("""
        <div style="font-size:0.7rem;color:#475569;text-transform:uppercase;
                    letter-spacing:0.08em;margin-bottom:0.4rem;font-weight:600;">
          🧪 Test Role (Demo)
        </div>
        """, unsafe_allow_html=True)
        role_options_map = {
            "👤 Khách (Guest)":       "guest",
            "🩺 Bác sĩ (User)":       "user",
            "🔬 Chuyên gia (Expert)": "expert",
            "👑 Quản trị (Admin)":    "admin",
        }
        current_label = next(
            (k for k, v in role_options_map.items() if v == role),
            "👤 Khách (Guest)"
        )
        new_role_label = st.selectbox(
            "Chuyển role",
            list(role_options_map.keys()),
            index=list(role_options_map.keys()).index(current_label),
            key="role_switcher",
            label_visibility="collapsed",
        )
        if role_options_map[new_role_label] != role:
            st.session_state["demo_role"] = role_options_map[new_role_label]
            # Cũng đặt lại username cho phù hợp
            st.session_state["username"] = new_role_label.split("(")[0].strip().split(" ", 1)[1]
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
# TRANG: GIỚI THIỆU (tất cả role xem được)
# =============================================================================
def render_intro_page() -> None:
    """Trang giới thiệu về hệ thống FuzzyGCN."""
    st.markdown('<div class="page-title fade-in">🏠 Giới thiệu hệ thống</div>', unsafe_allow_html=True)
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

    st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)

    # Thẻ mô tả
    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("""
        <div class="glass-card fade-in">
          <div style="font-size:1.1rem;font-weight:800;color:#00f5d4;margin-bottom:0.8rem;">
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
          <div style="font-size:1.1rem;font-weight:800;color:#00b4d8;margin-bottom:0.8rem;">
            🔐 Phân quyền hệ thống
          </div>
          <div style="display:flex;flex-direction:column;gap:0.6rem;">
            <div style="display:flex;align-items:center;gap:0.7rem;padding:0.5rem 0.7rem;
                        background:rgba(148,163,184,0.06);border-radius:8px;">
              <span class="role-badge role-guest">👤 Khách</span>
              <span style="color:#64748b;font-size:0.82rem;">Xem Giới thiệu & Tra cứu danh mục</span>
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
    st.markdown('<div class="page-subtitle">Tìm kiếm thông tin thuốc, bệnh và protein trong cơ sở dữ liệu</div>',
                unsafe_allow_html=True)

    tab_drug, tab_disease, tab_protein = st.tabs(["💊 Thuốc", "🦠 Bệnh", "🧬 Protein"])

    with tab_drug:
        search_drug = st.text_input("🔍 Tìm kiếm thuốc", placeholder="Nhập tên thuốc...",
                                     key="catalog_drug_search")
        filtered = [d for d in SAMPLE_DRUGS
                    if not search_drug or search_drug.lower() in d.lower()]
        df_drug = pd.DataFrame({
            "Tên thuốc": filtered,
            "Mã DrugBank": [f"DB{10000+i:05d}" for i in range(len(filtered))],
            "Nhóm": [random.choice(["Kháng sinh", "Tim mạch", "Thần kinh", "Chuyển hóa"])
                     for _ in filtered],
            "Đã có liên kết": [f"{random.randint(3,25)} bệnh" for _ in filtered],
        })
        st.dataframe(df_drug, use_container_width=True, hide_index=True)

    with tab_disease:
        search_dis = st.text_input("🔍 Tìm kiếm bệnh", placeholder="Nhập tên bệnh...",
                                    key="catalog_disease_search")
        filtered_d = [d for d in SAMPLE_DISEASES
                      if not search_dis or search_dis.lower() in d.lower()]
        df_disease = pd.DataFrame({
            "Tên bệnh": filtered_d,
            "Mã ICD-10": [f"E{10+i:02d}" for i in range(len(filtered_d))],
            "Hệ cơ quan": [random.choice(["Tim mạch", "Thần kinh", "Miễn dịch", "Nội tiết"])
                           for _ in filtered_d],
            "Thuốc liên quan": [f"{random.randint(2,18)} thuốc" for _ in filtered_d],
        })
        st.dataframe(df_disease, use_container_width=True, hide_index=True)

    with tab_protein:
        search_prot = st.text_input("🔍 Tìm kiếm protein", placeholder="Nhập tên protein...",
                                     key="catalog_protein_search")
        filtered_p = [p for p in SAMPLE_PROTEINS
                      if not search_prot or search_prot.lower() in p.lower()]
        df_prot = pd.DataFrame({
            "Tên protein": filtered_p,
            "UniProt ID": [f"P{10000+i:05d}" for i in range(len(filtered_p))],
            "Chức năng": [random.choice(["Receptor", "Enzyme", "Transporter", "Ion channel"])
                          for _ in filtered_p],
            "Tương tác": [f"{random.randint(5,40)} đối tác" for _ in filtered_p],
        })
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


def _build_mol_html(drug_smiles: list[tuple[str, str, str]]) -> str:
    """
    Tạo HTML hiển thị cấu trúc phân tử cho nhiều thuốc.
    drug_smiles: list of (drug_name, smiles, border_color)
    Dùng rdkit render server-side → SVG inline, không cần CDN.
    """
    if not drug_smiles:
        return ""

    cards_html = ""
    for name, smiles, color in drug_smiles:
        svg = _smiles_to_svg(smiles)
        smiles_preview = smiles[:44] + ("…" if len(smiles) > 44 else "")
        if svg:
            mol_content = f'<div class="mol-svg">{svg}</div>'
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

    return f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<style>
*{{box-sizing:border-box;margin:0;padding:0;}}
body{{background:#0d1b2a;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;
  padding:12px 16px;}}
.mol-grid{{display:flex;flex-wrap:wrap;gap:16px;}}
.mol-card{{background:rgba(255,255,255,0.05);border:1.5px solid;
  border-radius:12px;padding:10px 12px;text-align:center;
  flex:0 0 auto;width:244px;transition:box-shadow .2s;}}
.mol-card:hover{{box-shadow:0 0 18px rgba(0,245,212,0.22);}}
.mol-name{{font-size:0.85rem;font-weight:800;margin-bottom:6px;
  overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}}
.mol-svg{{width:220px;height:160px;border-radius:8px;overflow:hidden;
  display:flex;align-items:center;justify-content:center;
  background:#111827;}}
.mol-svg svg{{width:220px;height:160px;}}
.mol-svg-err{{font-size:0.75rem;color:#475569;padding:0.5rem;}}
.mol-smiles{{font-size:0.59rem;color:#475569;margin-top:5px;
  overflow:hidden;text-overflow:ellipsis;white-space:nowrap;
  font-family:monospace;}}
</style></head><body>
<div class="mol-grid">{cards_html}</div>
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
            ["B-dataset (Gottlieb)", "C-dataset (HDVD)", "F-dataset (FDataset)"],
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
        _DS_KEY = {"B-dataset (Gottlieb)": "b", "C-dataset (HDVD)": "c", "F-dataset (FDataset)": "f"}
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
            f"🔢 Số {src_label} muốn so sánh (1–5)",
            min_value=1, max_value=5, value=2, step=1,
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
                key=f"pred_src_{i}_{query_type}",
                label_visibility="collapsed",
            )
            selected_sources.append(nm)

        st.markdown("<div class='neon-hr'></div>", unsafe_allow_html=True)

        # Top-N kết quả mỗi node
        top_n = st.slider(
            "🎯 Top-N kết quả mỗi node",
            min_value=3, max_value=10, value=5, step=1,
            key="pred_top_n",
            help="Mỗi thuốc/bệnh sẽ nối với tối đa N kết quả trên đồ thị.",
        )

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
            dst_pool   = _disease_pool if is_drug_mode else _drug_pool

            results_per_src: list[list[dict]] = []
            random.seed(hash(tuple(unique_src)) % (2**31))

            for src_name in unique_src:
                # Mỗi source cho Top kết quả riêng (seed khác nhau theo tên)
                rng = random.Random(hash(src_name) % (2**31))
                pool = [d for d in dst_pool if d != src_name]
                rng.shuffle(pool)
                top_results = []
                for dst_name in pool[:top_n]:
                    score    = round(rng.uniform(0.42, 0.98), 4)
                    is_known = rng.random() > 0.5
                    top_results.append({
                        "name":  dst_name,
                        "score": score,
                        "known": is_known,
                    })
                top_results.sort(key=lambda x: x["score"], reverse=True)
                results_per_src.append(top_results)

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
            # ── Header kết quả ────────────────────────────────────────────────
            src_names_str = ", ".join(saved_src)
            dst_type_lbl  = "Bệnh" if saved_mode else "Thuốc"
            st.markdown(f"""
            <div class="glass-card" style="padding:1rem 1.4rem;margin-bottom:0.8rem;
              border-color:rgba(0,245,212,0.2);">
              <div style="font-size:0.92rem;font-weight:800;color:#00f5d4;">
                📊 Kết quả dự đoán Top-{saved_topn} {dst_type_lbl}
              </div>
              <div style="font-size:0.78rem;color:#475569;margin-top:0.25rem;">
                Nguồn: <strong style="color:#e2e8f0;">{src_names_str}</strong>
                &nbsp;·&nbsp; Dataset: {saved_ds}
              </div>
            </div>
            """, unsafe_allow_html=True)

            # ── Chú thích màu node nguồn ───────────────────────────────────────
            legend_html = '<div style="display:flex;flex-wrap:wrap;gap:0.5rem;margin-bottom:0.6rem;">'
            for i, src_nm in enumerate(saved_src):
                c = _SRC_COLORS[i % len(_SRC_COLORS)]
                legend_html += (
                    f'<div style="display:flex;align-items:center;gap:0.4rem;'
                    f'background:rgba(255,255,255,0.04);border:1px solid {c["border"]}33;'
                    f'border-radius:999px;padding:0.2rem 0.7rem;">'
                    f'<div style="width:10px;height:10px;border-radius:2px;'
                    f'background:{c["bg"]};"></div>'
                    f'<span style="font-size:0.78rem;color:#e2e8f0;font-weight:600;">'
                    f'{src_nm}</span></div>'
                )
            legend_html += "</div>"
            st.markdown(legend_html, unsafe_allow_html=True)

            # ── Bipartite diagram ─────────────────────────────────────────────
            bip_html, bip_h = _build_bipartite_html(
                sources=saved_src,
                results_per_source=saved_res,
                top_n=saved_topn,
                is_drug_mode=saved_mode,
            )
            st.markdown('<div class="glass-card" style="padding:0.4rem;">', unsafe_allow_html=True)
            components.html(bip_html, height=bip_h + 24, scrolling=False)
            st.markdown("</div>", unsafe_allow_html=True)

            # ── Cấu trúc phân tử thuốc ────────────────────────────────────────
            saved_smiles: dict[str, str] = st.session_state.get("pred_src_smiles", {})
            # Drug mode: hiển thị SMILES của các thuốc được chọn
            # Disease mode: hiển thị SMILES của top kết quả thuốc trả về
            if saved_mode:
                # Thuốc → Bệnh: SMILES từ saved_smiles (thuốc nguồn)
                mol_entries = [
                    (nm, saved_smiles.get(nm, ""), _SRC_COLORS[i % len(_SRC_COLORS)]["bg"])
                    for i, nm in enumerate(saved_src)
                    if saved_smiles.get(nm)
                ]
            else:
                # Bệnh → Thuốc: lấy SMILES từ _smiles_map cho top-1 thuốc kết quả mỗi bệnh
                mol_entries = []
                seen = set()
                for i, (src_nm, res_list) in enumerate(zip(saved_src, saved_res)):
                    for r in res_list[:3]:
                        drug_nm = r["name"]
                        if drug_nm not in seen:
                            smiles_val = _smiles_map.get(drug_nm, "")
                            if smiles_val:
                                mol_entries.append((drug_nm, smiles_val,
                                                    _SRC_COLORS[i % len(_SRC_COLORS)]["bg"]))
                                seen.add(drug_nm)
            if mol_entries:
                st.markdown("<div class='neon-hr'></div>", unsafe_allow_html=True)
                st.markdown(
                    '<div style="font-size:0.88rem;font-weight:800;color:#94a3b8;margin-bottom:0.6rem;">'
                    '🔬 Cấu trúc phân tử</div>',
                    unsafe_allow_html=True,
                )
                mol_html = _build_mol_html(mol_entries)
                mol_h = max(220, len(mol_entries) * 10 + 220)
                st.markdown('<div class="glass-card" style="padding:0.6rem;">', unsafe_allow_html=True)
                components.html(mol_html, height=mol_h, scrolling=True)
                st.markdown("</div>", unsafe_allow_html=True)

            # ── Bảng chi tiết kết quả ─────────────────────────────────────────
            st.markdown("<div class='neon-hr'></div>", unsafe_allow_html=True)
            st.markdown(
                '<div style="font-size:0.88rem;font-weight:800;color:#94a3b8;margin-bottom:0.5rem;">'
                '📋 Chi tiết kết quả</div>',
                unsafe_allow_html=True,
            )
            tab_objs = st.tabs([f"{'💊' if saved_mode else '🦠'} {s}" for s in saved_src])
            for tab_obj, (src_nm, res_list) in zip(tab_objs, zip(saved_src, saved_res)):
                with tab_obj:
                    for rank, r in enumerate(res_list):
                        score = r["score"]
                        bar_w = int(score * 100)
                        badge = ('<span class="badge-known">✅ Đã biết</span>'
                                 if r["known"] else
                                 '<span class="badge-pred">🔬 Dự đoán</span>')
                        color = "#4ade80" if r["known"] else "#00b4d8"
                        st.markdown(f"""
                        <div style="display:flex;align-items:center;gap:0.8rem;
                          padding:0.6rem 0.9rem;margin-bottom:0.35rem;
                          background:rgba(255,255,255,0.03);
                          border:1px solid rgba(255,255,255,0.07);border-radius:10px;">
                          <div style="min-width:22px;font-size:0.74rem;
                                      color:#475569;font-weight:700;">#{rank+1}</div>
                          <div style="flex:1;min-width:0;">
                            <div style="display:flex;align-items:center;
                                        justify-content:space-between;margin-bottom:0.28rem;">
                              <span style="font-size:0.86rem;font-weight:700;
                                           color:#e2e8f0;overflow:hidden;
                                           text-overflow:ellipsis;white-space:nowrap;
                                           max-width:200px;">{r['name']}</span>
                              {badge}
                            </div>
                            <div class="score-bar-bg">
                              <div class="score-bar-fill" style="width:{bar_w}%;
                                background:linear-gradient(90deg,{color},{color}88);
                                box-shadow:0 0 8px {color}88;"></div>
                            </div>
                          </div>
                          <div style="min-width:46px;text-align:right;font-size:0.9rem;
                                      font-weight:800;color:{color};">{score:.3f}</div>
                        </div>
                        """, unsafe_allow_html=True)
        else:
            # Placeholder khi chưa dự đoán
            st.markdown("""
            <div style="text-align:center;padding:5rem 2rem;color:#334155;">
              <div style="font-size:4rem;margin-bottom:1.2rem;
                          filter:drop-shadow(0 0 20px rgba(0,245,212,0.3));">🧬</div>
              <div style="font-size:1rem;font-weight:700;color:#475569;margin-bottom:0.5rem;">
                Chưa có kết quả</div>
              <div style="font-size:0.85rem;color:#334155;">
                Chọn thuốc/bệnh ở bên trái và nhấn<br>
                <strong style="color:#00f5d4;">🚀 Dự đoán &amp; Vẽ đồ thị</strong>
              </div>
            </div>
            """, unsafe_allow_html=True)

    # ── Lịch sử dự đoán phiên hiện tại ───────────────────────────────────────
    if HISTORY_RECORDS and _can("user"):
        st.markdown("<div class='neon-hr'></div>", unsafe_allow_html=True)
        st.markdown(
            '<div style="font-size:0.9rem;font-weight:800;color:#94a3b8;margin-bottom:0.5rem;">'
            '🕑 Lịch sử phiên hiện tại</div>',
            unsafe_allow_html=True,
        )
        df_hist = pd.DataFrame(HISTORY_RECORDS[-15:])
        st.dataframe(df_hist, use_container_width=True, hide_index=True)


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
    _DS_OPTIONS = ["B-dataset (Gottlieb)", "C-dataset (HDVD)", "F-dataset (FDataset)"]
    _DS_KEY_MAP = {"B-dataset (Gottlieb)": "b", "C-dataset (HDVD)": "c", "F-dataset (FDataset)": "f"}
    col_ds, col_seed, col_phys = st.columns([1.2, 1.2, 0.8])
    with col_ds:
        net_dataset = st.selectbox("📂 Dataset", _DS_OPTIONS, key="net_dataset")
    _ds_key = _DS_KEY_MAP[net_dataset]
    _ROOT_DATA = Path(__file__).parent.parent / "data"

    def _net_load(fname: str, field: str, fallback: list[str]) -> list[str]:
        try:
            with open(_ROOT_DATA / fname, encoding="utf-8") as _f:
                return [r[field] for r in json.load(_f) if r.get(field)]
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

    col_legend_row, _ = st.columns([1, 2])
    with col_legend_row:
        st.markdown("""
        <div class="glass-card" style="padding:0.8rem 1.2rem;font-size:0.82rem;">
          <div style="font-weight:800;color:#e2e8f0;margin-bottom:0.6rem;">📖 Chú thích</div>
          <div style="display:flex;align-items:center;gap:0.5rem;margin-bottom:0.35rem;">
            <div style="width:14px;height:14px;background:#0066ff;border-radius:3px;"></div>
            <span style="color:#94a3b8;">Thuốc (hình vuông)</span>
          </div>
          <div style="display:flex;align-items:center;gap:0.5rem;margin-bottom:0.35rem;">
            <div style="width:14px;height:14px;background:#ff3333;border-radius:50%;"></div>
            <span style="color:#94a3b8;">Bệnh (hình tròn)</span>
          </div>
          <div style="display:flex;align-items:center;gap:0.5rem;">
            <div style="width:0;height:0;border-left:8px solid transparent;
                        border-right:8px solid transparent;border-bottom:14px solid #00cc66;"></div>
            <span style="color:#94a3b8;">Protein (tam giác)</span>
          </div>
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
    random.seed(random_seed)

    net = PyvisNetwork(
        height="600px",
        width="100%",
        bgcolor="#0d1b2a",
        font_color="#e2e8f0",
    )
    net.toggle_physics(show_physics)
    net.set_options("""
    {
      "physics": {
        "barnesHut": {
          "gravitationalConstant": -8000,
          "centralGravity": 0.3,
          "springLength": 130,
          "springConstant": 0.04,
          "damping": 0.09,
          "avoidOverlap": 0.2
        },
        "minVelocity": 0.75
      },
      "interaction": {
        "hover": true,
        "tooltipDelay": 150,
        "navigationButtons": true,
        "keyboard": true
      },
      "nodes": {
        "borderWidth": 2,
        "borderWidthSelected": 4
      }
    }
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

    # ── Thêm edges ngẫu nhiên (chỉ dùng index trong phạm vi node hiện có) ────
    nd = len(drugs)
    ndis = len(diseases)
    np_ = len(proteins)

    # Thuốc–Bệnh
    if nd > 0 and ndis > 0:
        for _ in range(random.randint(max(3, nd), max(5, nd + 3))):
            d_idx   = random.randint(0, nd - 1)
            dis_idx = random.randint(0, ndis - 1)
            score   = round(random.uniform(0.5, 0.99), 2)
            net.add_edge(
                f"D_{d_idx}", f"Dis_{dis_idx}",
                value=score,
                color={"color": "#00ccff", "highlight": "#00f5d4", "hover": "#00f5d4"},
                title=f"Thuốc–Bệnh · Xác suất: {score}",
                width=max(1, int(score * 4)),
                arrows="to",
            )

    # Thuốc–Protein
    if nd > 0 and np_ > 0:
        for _ in range(random.randint(max(2, nd - 1), max(4, nd + 1))):
            d_idx = random.randint(0, nd - 1)
            p_idx = random.randint(0, np_ - 1)
            score = round(random.uniform(0.4, 0.95), 2)
            net.add_edge(
                f"D_{d_idx}", f"P_{p_idx}",
                value=score,
                color={"color": "#9966ff", "highlight": "#cc99ff", "hover": "#cc99ff"},
                title=f"Thuốc–Protein · Tương tác: {score}",
                width=max(1, int(score * 3)),
                dashes=True,
            )

    # Bệnh–Protein
    if ndis > 0 and np_ > 0:
        for _ in range(random.randint(max(2, ndis - 1), max(4, ndis + 1))):
            dis_idx = random.randint(0, ndis - 1)
            p_idx   = random.randint(0, np_ - 1)
            score   = round(random.uniform(0.4, 0.95), 2)
            net.add_edge(
                f"Dis_{dis_idx}", f"P_{p_idx}",
                value=score,
                color={"color": "#ff9900", "highlight": "#ffcc33", "hover": "#ffcc33"},
                title=f"Bệnh–Protein · Liên quan: {score}",
                width=max(1, int(score * 3)),
                dashes=True,
            )

    # ── Lưu HTML và render ─────────────────────────────────────────────────────
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".html", delete=False, encoding="utf-8"
    ) as tmp_file:
        net.save_graph(tmp_file.name)
        tmp_path = tmp_file.name

    with open(tmp_path, "r", encoding="utf-8") as f:
        html_content = f.read()

    # Dọn file tạm
    try:
        os.unlink(tmp_path)
    except OSError:
        pass

    # Render đồ thị trong iframe
    st.markdown('<div class="glass-card" style="padding:0.5rem;">', unsafe_allow_html=True)
    components.html(html_content, height=620, scrolling=False)
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
        <div class="metric-value" style="font-size:1.8rem;color:#00f5d4;">15</div>
        <div class="metric-label">Tổng nodes</div>
      </div>
    </div>
    """, unsafe_allow_html=True)


# =============================================================================
# TRANG: DUYỆT LIÊN KẾT (Expert, Admin)
# =============================================================================
def render_review_page() -> None:
    """Giao diện cho Expert/Admin duyệt các liên kết mới được AI tìm ra."""
    if not _can("expert"):
        st.markdown("""
        <div class="access-denied fade-in">
          <div style="font-size:3rem;margin-bottom:0.8rem;">🔒</div>
          <div style="font-size:1.2rem;font-weight:800;margin-bottom:0.5rem;">
            Yêu cầu Chuyên gia trở lên</div>
          <div style="font-size:0.88rem;color:rgba(247,37,133,0.7);">
            Chức năng Duyệt Liên Kết chỉ dành cho vai trò
            <strong>Chuyên gia</strong> và <strong>Admin</strong>.
          </div>
        </div>
        """, unsafe_allow_html=True)
        return

    st.markdown('<div class="page-title fade-in">✅ Duyệt Liên Kết</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-subtitle">Xác nhận hoặc loại bỏ các liên kết mới do AI khám phá</div>',
                unsafe_allow_html=True)

    # Khởi tạo trạng thái duyệt trong session
    if "review_statuses" not in st.session_state:
        st.session_state["review_statuses"] = {
            r["id"]: r["status"] for r in PENDING_LINKS
        }

    # Thống kê nhanh
    statuses = st.session_state["review_statuses"]
    n_pending  = sum(1 for s in statuses.values() if s == "Chờ duyệt")
    n_approved = sum(1 for s in statuses.values() if s == "Đã duyệt ✅")
    n_rejected = sum(1 for s in statuses.values() if s == "Đã từ chối ❌")

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

    for link in PENDING_LINKS:
        lid    = link["id"]
        status = st.session_state["review_statuses"][lid]

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
# TRANG: CẤU HÌNH & METRICS (Admin only)
# =============================================================================
def render_config_page() -> None:
    """Trang cấu hình mô hình và xem metrics chi tiết (chỉ Admin)."""
    if not _can("admin"):
        st.markdown("""
        <div class="access-denied fade-in">
          <div style="font-size:3rem;margin-bottom:0.8rem;">👑</div>
          <div style="font-size:1.2rem;font-weight:800;margin-bottom:0.5rem;">
            Yêu cầu quyền Admin</div>
          <div style="font-size:0.88rem;color:rgba(247,37,133,0.7);">
            Trang Cấu Hình & Metrics chỉ dành cho <strong>Quản trị viên</strong>.
          </div>
        </div>
        """, unsafe_allow_html=True)
        return

    st.markdown('<div class="page-title fade-in">⚙️ Cấu Hình & Metrics</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-subtitle">Xem hiệu suất mô hình và chỉnh sửa siêu tham số huấn luyện</div>',
                unsafe_allow_html=True)

    tab_metrics, tab_train, tab_compare = st.tabs(
        ["📊 Hiệu suất mô hình", "🎛️ Tham số huấn luyện", "🆚 So sánh Dataset"]
    )

    # ── Tab 1: Metrics ───────────────────────────────────────────────────────
    with tab_metrics:
        st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)
        cols = st.columns(4)
        kpis = [
            ("AUC-ROC",  "96.3%", "↑ +2.1%", "#00f5d4"),
            ("AUC-PR",   "91.7%", "↑ +1.8%", "#00b4d8"),
            ("F1 Score", "88.4%", "↑ +0.9%", "#a78bfa"),
            ("Accuracy", "92.1%", "→ 0.0%",  "#fbbf24"),
        ]
        for i, (name, val, delta, color) in enumerate(kpis):
            with cols[i]:
                delta_c = "#4ade80" if "↑" in delta else "#94a3b8"
                st.markdown(f"""
                <div class="metric-card">
                  <div class="metric-value" style="color:{color};
                    text-shadow:0 0 20px {color}55;">{val}</div>
                  <div class="metric-label">{name}</div>
                  <div class="metric-delta" style="color:{delta_c};">{delta}</div>
                </div>
                """, unsafe_allow_html=True)

        st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)

        # Biểu đồ loss mô phỏng
        col_loss, col_auc = st.columns(2)
        with col_loss:
            st.markdown('<div class="glass-card">', unsafe_allow_html=True)
            st.markdown("""<div style="font-size:0.9rem;font-weight:700;color:#00f5d4;
                           margin-bottom:0.6rem;">📉 Loss curve (C-dataset)</div>""",
                        unsafe_allow_html=True)
            epochs = list(range(1, 51))
            train_loss = [1.2 * (0.95 ** e) + random.uniform(-0.01, 0.01) for e in epochs]
            val_loss   = [1.3 * (0.96 ** e) + random.uniform(-0.015, 0.015) for e in epochs]
            df_loss = pd.DataFrame({"Epoch": epochs, "Train Loss": train_loss, "Val Loss": val_loss})
            st.line_chart(df_loss.set_index("Epoch"), color=["#00f5d4", "#f72585"])
            st.markdown("</div>", unsafe_allow_html=True)

        with col_auc:
            st.markdown('<div class="glass-card">', unsafe_allow_html=True)
            st.markdown("""<div style="font-size:0.9rem;font-weight:700;color:#a78bfa;
                           margin-bottom:0.6rem;">📈 AUC-ROC theo epoch (C-dataset)</div>""",
                        unsafe_allow_html=True)
            auc_vals = [0.5 + (0.47 * (1 - 0.97 ** e)) + random.uniform(-0.005, 0.005)
                        for e in epochs]
            df_auc = pd.DataFrame({"Epoch": epochs, "AUC-ROC": auc_vals})
            st.line_chart(df_auc.set_index("Epoch"), color=["#a78bfa"])
            st.markdown("</div>", unsafe_allow_html=True)

    # ── Tab 2: Tham số huấn luyện ──────────────────────────────────────────────
    with tab_train:
        st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)
        col_l, col_r = st.columns(2)

        with col_l:
            st.markdown('<div class="glass-card">', unsafe_allow_html=True)
            st.markdown("""<div style="font-size:0.95rem;font-weight:800;color:#00f5d4;
                           margin-bottom:1rem;">🎛️ Siêu tham số chung</div>""",
                        unsafe_allow_html=True)

            dataset_sel = st.selectbox(
                "📂 Dataset mục tiêu",
                ["B-dataset", "C-dataset", "F-dataset"],
                key="cfg_dataset",
            )
            epochs_val = st.slider(
                "🔄 Số Epoch", 10, 500, 200, 10, key="cfg_epochs",
                help="Số vòng lặp huấn luyện."
            )
            lr_val = st.select_slider(
                "📐 Learning Rate",
                options=[0.0001, 0.0005, 0.001, 0.005, 0.01, 0.05],
                value=0.001,
                key="cfg_lr",
                format_func=lambda x: f"{x:.4f}",
            )
            batch_sz = st.slider(
                "📦 Batch Size", 16, 512, 64, 16, key="cfg_batch",
            )
            dropout = st.slider(
                "💧 Dropout", 0.0, 0.8, 0.3, 0.05, key="cfg_dropout",
            )
            st.markdown("</div>", unsafe_allow_html=True)

        with col_r:
            st.markdown('<div class="glass-card">', unsafe_allow_html=True)
            st.markdown("""<div style="font-size:0.95rem;font-weight:800;color:#a78bfa;
                           margin-bottom:1rem;">🧠 Tham số GCN</div>""",
                        unsafe_allow_html=True)

            hidden_dim = st.select_slider(
                "🔢 Hidden Dim",
                options=[32, 64, 128, 256, 512],
                value=128,
                key="cfg_hidden",
            )
            num_layers = st.slider(
                "🏗️ Số lớp GCN", 1, 6, 3, key="cfg_layers",
            )
            fuzzy_m = st.slider(
                "🌫️ Fuzzy m (fuzzifier)", 1.1, 3.0, 2.0, 0.1, key="cfg_fuzzy_m",
                help="Tham số mờ hóa của Fuzzy C-Means."
            )
            aggregator = st.selectbox(
                "🔀 Aggregator",
                ["mean", "sum", "max", "attention"],
                key="cfg_aggregator",
            )
            use_batch_norm = st.toggle("📏 Batch Normalization", value=True, key="cfg_bn")
            use_residual   = st.toggle("♻️ Residual connections", value=False, key="cfg_res")

            st.markdown("</div>", unsafe_allow_html=True)

        # Nút lưu cấu hình
        col_save, _ = st.columns([1, 2])
        with col_save:
            if st.button("💾 Lưu cấu hình", type="primary",
                         use_container_width=True, key="btn_save_cfg"):
                cfg = {
                    "dataset":     dataset_sel,
                    "epochs":      epochs_val,
                    "lr":          lr_val,
                    "batch_size":  batch_sz,
                    "dropout":     dropout,
                    "hidden_dim":  hidden_dim,
                    "num_layers":  num_layers,
                    "fuzzy_m":     fuzzy_m,
                    "aggregator":  aggregator,
                    "batch_norm":  use_batch_norm,
                    "residual":    use_residual,
                }
                st.session_state["saved_config"] = cfg
                st.success(f"✅ Đã lưu cấu hình cho dataset **{dataset_sel}**.")
                st.json(cfg)

    # ── Tab 3: So sánh dataset ─────────────────────────────────────────────────
    with tab_compare:
        st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)

        # Bảng so sánh kết quả 3 dataset
        compare_data = {
            "Dataset":   ["B-dataset", "C-dataset", "F-dataset"],
            "AUC-ROC":   [0.958, 0.963, 0.941],
            "AUC-PR":    [0.912, 0.917, 0.895],
            "F1":        [0.878, 0.884, 0.861],
            "Accuracy":  [0.919, 0.921, 0.908],
            "Epochs":    [150, 200, 180],
            "Train Time": ["12m 34s", "18m 22s", "15m 05s"],
        }
        df_compare = pd.DataFrame(compare_data)

        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.markdown("""<div style="font-size:0.95rem;font-weight:800;color:#00f5d4;
                       margin-bottom:0.8rem;">🆚 Bảng so sánh hiệu suất</div>""",
                    unsafe_allow_html=True)
        st.dataframe(
            df_compare.style.highlight_max(
                subset=["AUC-ROC", "AUC-PR", "F1", "Accuracy"],
                color="rgba(0,245,212,0.25)"
            ),
            use_container_width=True,
            hide_index=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)

        # Biểu đồ bar so sánh
        st.markdown('<div class="glass-card" style="margin-top:0.8rem;">', unsafe_allow_html=True)
        st.markdown("""<div style="font-size:0.9rem;font-weight:700;color:#fbbf24;
                       margin-bottom:0.6rem;">📊 So sánh AUC-ROC và AUC-PR</div>""",
                    unsafe_allow_html=True)
        df_bar = df_compare[["Dataset", "AUC-ROC", "AUC-PR"]].set_index("Dataset")
        st.bar_chart(df_bar, color=["#00f5d4", "#a78bfa"])
        st.markdown("</div>", unsafe_allow_html=True)


# =============================================================================
# TRANG: SO SÁNH MODEL (User / Expert / Admin)
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
    """Trang So Sánh Model — user/expert/admin đều xem được."""
    if not _can("user"):
        st.markdown("""
        <div class="access-denied fade-in">
          <div style="font-size:3rem;margin-bottom:0.8rem;">📊</div>
          <div style="font-size:1.2rem;font-weight:800;margin-bottom:0.5rem;">
            Yêu cầu đăng nhập</div>
          <div style="font-size:0.88rem;color:rgba(247,37,133,0.7);">
            Vui lòng đăng nhập để xem trang So Sánh Model.
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

    # Nếu là guest và chưa vào workspace → hiện landing page
    if _role() == "guest" and not st.session_state.get("guest_workspace", False):
        render_landing_page()
        return

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

    # Routing theo menu được chọn
    if "Giới thiệu" in selected_menu:
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
