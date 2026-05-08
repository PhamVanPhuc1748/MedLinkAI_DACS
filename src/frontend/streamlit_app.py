from __future__ import annotations

from pathlib import Path
import sys

import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
# Also ensure project root is on path for cross-package imports
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from frontend.app.config import API_DEFAULT  # noqa: E402
from frontend.app.pages.admin import render_admin_console  # noqa: E402
from frontend.app.pages.landing import render_landing  # noqa: E402
from frontend.app.pages.user import render_user_workspace  # noqa: E402
from frontend.app.state import clear_auth_state, current_role, is_authenticated, is_guest  # noqa: E402
from frontend.app.ui.theme import apply_theme, render_hero  # noqa: E402


# ─────────────────────────────────────────────────────────────────────────────
# Giao diện khách (guest) — chỉ dùng tra cứu, không lưu lịch sử
# ─────────────────────────────────────────────────────────────────────────────

def _render_guest_workspace(api_base_url: str) -> None:
    """Workspace cho khách — chỉ cho tra cứu thuốc/bệnh, không lưu lịch sử."""
    apply_theme()
    with st.sidebar:
        st.markdown(
            """
            <div style="padding:0.5rem 0 0.8rem">
              <div style="font-size:1.3rem;font-weight:800;color:#0d9488">💊 MedLink AI</div>
              <div style="font-size:0.72rem;color:#94a3b8;margin-top:0.1rem">Chế độ khách</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown(
            """
            <div style="background:#fef3c7;border:1px solid #f59e0b;border-radius:12px;
                        padding:0.8rem 1rem;font-size:0.82rem;color:#78350f;margin-bottom:0.8rem">
              👤 Bạn đang dùng chế độ <strong>Khách</strong>.<br>
              Chức năng: tra cứu thuốc/bệnh.<br>
              Không lưu lịch sử, không xuất báo cáo.
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("🔑 Đăng nhập / Đăng ký", use_container_width=True, key="guest_login_btn"):
            clear_auth_state()
            st.rerun()
        if st.button("🚪 Thoát chế độ khách", use_container_width=True, key="guest_exit_btn"):
            clear_auth_state()
            st.rerun()

    render_hero("user")
    st.info("👤 **Chế độ khách** — Chỉ tra cứu thuốc/bệnh. Đăng nhập để dùng đầy đủ tính năng.", icon="ℹ️")
    render_user_workspace(api_base_url, token="")


# ─────────────────────────────────────────────────────────────────────────────
# Sidebar cho người dùng đã đăng nhập — các tab điều hướng bên trái
# ─────────────────────────────────────────────────────────────────────────────

def _render_authenticated_sidebar(api_base_url: str) -> str:
    """Vẽ sidebar với các tab điều hướng. Trả về tên menu được chọn."""
    with st.sidebar:
        is_dark = st.session_state.get("dark_mode", False)

        # ── Logo + toggle ──────────────────────────────────────────────
        col_logo, col_toggle = st.columns([3, 2])
        with col_logo:
            st.markdown(
                """
                <div style="padding:0.5rem 0 0.3rem 0">
                  <div style="font-size:1.3rem;font-weight:800;color:#0d9488">💊 MedLink AI</div>
                  <div style="font-size:0.72rem;color:var(--muted);margin-top:0.1rem">Drug · Disease AI</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with col_toggle:
            toggle_label = "🌙" if not is_dark else "☀️"
            if st.button(toggle_label, key="btn_dark_toggle", use_container_width=True,
                         help="Chuyển giao diện sáng/tối"):
                st.session_state["dark_mode"] = not is_dark
                st.rerun()

        # ── User badge ─────────────────────────────────────────────────
        username = str(st.session_state.get("username", ""))
        role = current_role()
        role_icon = "👑" if role == "admin" else "👤"
        role_label = "Quản trị viên" if role == "admin" else "Người dùng"

        st.markdown(
            f"""
            <div class="sidebar-user-badge">
              <div style="font-weight:700;color:var(--known-fg);font-size:0.95rem">{role_icon} {username}</div>
              <div style="font-size:0.73rem;color:var(--muted);margin-top:0.1rem">{role_label}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown(
            "<hr style='border:none;border-top:1px solid var(--border);margin:0.4rem 0 0.8rem 0'>",
            unsafe_allow_html=True,
        )

        # ── Navigation tabs ────────────────────────────────────────────
        st.markdown(
            '<div class="sidebar-section-label">📌 Điều hướng</div>',
            unsafe_allow_html=True,
        )

        # Định nghĩa các tab theo vai trò
        nav_tabs: list[tuple[str, str]] = [
            ("🔬 Dự đoán", "Tra cứu & dự đoán thuốc–bệnh"),
        ]
        if role == "admin":
            nav_tabs += [
                ("🛠️ Admin Console", "Quản lý hệ thống"),
                ("📊 Thống kê", "Xem báo cáo tổng quan"),
            ]
        nav_tabs += [
            ("📖 Hướng dẫn", "Cách sử dụng hệ thống"),
        ]

        _saved_nav = st.session_state.get("nav_selection", nav_tabs[0][0])
        _valid_labels = [t[0] for t in nav_tabs]
        if _saved_nav not in _valid_labels:
            _saved_nav = nav_tabs[0][0]

        selected_menu = _saved_nav

        for label, desc in nav_tabs:
            is_active = (label == _saved_nav)
            active_cls = "active" if is_active else ""
            # Dùng button ẩn Streamlit để xử lý click, HTML div để hiển thị đẹp
            btn_col, _ = st.columns([1, 0.001])
            with btn_col:
                if st.button(
                    label,
                    key=f"nav_{label}",
                    use_container_width=True,
                    help=desc,
                    type="primary" if is_active else "secondary",
                ):
                    st.session_state["nav_selection"] = label
                    st.rerun()

        st.markdown(
            "<hr style='border:none;border-top:1px solid var(--border);margin:0.8rem 0'>",
            unsafe_allow_html=True,
        )

        # ── Logout ────────────────────────────────────────────────────
        if st.button("🚪 Đăng xuất", use_container_width=True, key="btn_logout"):
            clear_auth_state()
            st.rerun()

        # ── Footer ────────────────────────────────────────────────────
        st.markdown(
            """
            <div style="font-size:0.7rem;color:#94a3b8;text-align:center;margin-top:1.5rem">
              MedLink AI v1.0 · FuzzyGCN<br>Drug–Disease Link Prediction
            </div>
            """,
            unsafe_allow_html=True,
        )

    return str(st.session_state.get("nav_selection", nav_tabs[0][0]))


# ─────────────────────────────────────────────────────────────────────────────
# Render trang hướng dẫn nội bộ
# ─────────────────────────────────────────────────────────────────────────────

def _render_help_page() -> None:
    render_hero("user")
    st.markdown(
        """
        <div class="card">
          <div class="card-title">📖 Hướng dẫn sử dụng MedLink AI</div>
          <ol style="line-height:2;color:var(--text);font-size:0.92rem">
            <li><strong>Chọn tab "🔬 Dự đoán"</strong> từ menu bên trái.</li>
            <li>Chọn dataset (B, C hoặc F) và loại tra cứu (theo thuốc hoặc theo bệnh).</li>
            <li>Nhập tên thuốc hoặc bệnh vào ô tìm kiếm.</li>
            <li>Nhấn <em>Tìm kiếm</em> — AI sẽ trả về danh sách liên kết kèm xác suất.</li>
            <li>Các kết quả <span class="badge-known">✅ Đã biết</span> là liên kết xác nhận thực nghiệm;
                <span class="badge-pred">🔬 Dự đoán</span> là kết quả mới từ AI.</li>
          </ol>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    apply_theme()

    api_base_url = API_DEFAULT

    # ── Chưa đăng nhập → Trang chủ public ────────────────────────────
    if not is_authenticated():
        render_landing(api_base_url)
        return

    # ── Chế độ khách (guest) ───────────────────────────────────────
    if is_guest():
        _render_guest_workspace(api_base_url)
        return
    # ── Đã đăng nhập → Sidebar + nội dung ────────────────────────────
    menu = _render_authenticated_sidebar(api_base_url)
    token = str(st.session_state.get("token", ""))

    if not token:
        # Token mất → về landing
        clear_auth_state()
        st.rerun()
        return

    role = current_role()

    if "Dự đoán" in menu:
        render_hero(role)
        render_user_workspace(api_base_url, token)

    elif "Admin Console" in menu:
        if role != "admin":
            st.error("❌ Bạn không có quyền Admin.")
            return
        render_hero(role)
        render_admin_console(api_base_url, token)

    elif "Thống kê" in menu:
        render_hero(role)
        st.info("📊 Chức năng thống kê đang được phát triển.")

    elif "Hướng dẫn" in menu:
        _render_help_page()

    else:
        render_hero(role)
        render_user_workspace(api_base_url, token)


if __name__ == "__main__":
    main()

