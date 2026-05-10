from __future__ import annotations

import streamlit as st


SESSION_KEYS = [
    "token",
    "username",
    "role",
    "history_rows",
    "admin_predictions",
    "nav_selection",
]


def clear_auth_state() -> None:
    for key in SESSION_KEYS:
        st.session_state.pop(key, None)


def is_authenticated() -> bool:
    """Trả về True nếu đã đăng nhập (có token thật) hoặc đang ở chế độ khách (role=guest)."""
    has_real_token = bool(st.session_state.get("token"))  # None hoặc "" → False
    is_guest_mode  = st.session_state.get("role") == "guest"
    return has_real_token or is_guest_mode


def is_guest() -> bool:
    return st.session_state.get("role") == "guest"


def current_role() -> str:
    return str(st.session_state.get("role", ""))
