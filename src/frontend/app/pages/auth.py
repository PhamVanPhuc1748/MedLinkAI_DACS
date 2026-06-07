from __future__ import annotations

import streamlit as st

from ..services.api_client import ApiClient


# ── Shared CSS injected once ───────────────────────────────────────────────────
_AUTH_CSS = """
<style>
.auth-step-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background: var(--primary);
  color: #fff;
  font-size: 0.72rem;
  font-weight: 700;
  margin-right: 6px;
  flex-shrink: 0;
}
.auth-step-label {
  display: flex;
  align-items: center;
  font-size: 0.78rem;
  font-weight: 700;
  color: var(--muted);
  text-transform: uppercase;
  letter-spacing: 0.06em;
  margin-bottom: 0.5rem;
}
</style>
"""


def render_login(api_base_url: str) -> None:
    st.markdown(_AUTH_CSS, unsafe_allow_html=True)

    mode = st.session_state.get("auth_mode", "login")

    _, col, _ = st.columns([1, 2.2, 1])
    with col:
        # ── Branding ───────────────────────────────────────────────────
        st.markdown(
            """
            <div style="text-align:center;margin-bottom:1.2rem">
              <div style="font-size:2.8rem;line-height:1">💊</div>
              <div style="font-size:1.5rem;font-weight:800;color:#0d9488;margin-top:0.3rem">MedLink AI</div>
              <div style="font-size:0.78rem;color:var(--muted);margin-top:0.1rem">Drug · Disease Intelligence Platform</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # ── Mode tabs ──────────────────────────────────────────────────
        t1, t2, t3 = st.columns(3)
        with t1:
            if st.button("🔑 Đăng nhập", use_container_width=True,
                         type="primary" if mode == "login" else "secondary",
                         key="btn_mode_login"):
                st.session_state["auth_mode"] = "login"
                st.rerun()
        with t2:
            if st.button("📝 Đăng ký", use_container_width=True,
                         type="primary" if mode == "register" else "secondary",
                         key="btn_mode_register"):
                st.session_state["auth_mode"] = "register"
                st.rerun()
        with t3:
            if st.button("🔓 Quên MK", use_container_width=True,
                         type="primary" if mode == "forgot" else "secondary",
                         key="btn_mode_forgot"):
                st.session_state["auth_mode"] = "forgot"
                st.session_state.pop("forgot_otp_sent", None)
                st.rerun()

        st.markdown("<div style='height:0.6rem'></div>", unsafe_allow_html=True)

        # ── LOGIN ──────────────────────────────────────────────────────
        if mode == "login":
            with st.form("form_login", clear_on_submit=False):
                st.markdown(
                    '<div class="auth-step-label"><span class="auth-step-badge">1</span>Tài khoản</div>',
                    unsafe_allow_html=True,
                )
                username = st.text_input("👤 Tên đăng nhập", placeholder="Nhập tên đăng nhập", key="li_user")
                st.markdown(
                    '<div class="auth-step-label" style="margin-top:0.5rem">'
                    '<span class="auth-step-badge">2</span>Mật khẩu</div>',
                    unsafe_allow_html=True,
                )
                password = st.text_input("🔒 Mật khẩu", type="password", placeholder="••••••••", key="li_pass")
                st.markdown("<div style='height:0.3rem'></div>", unsafe_allow_html=True)
                submitted = st.form_submit_button("🔑 Đăng nhập", use_container_width=True)

            st.markdown(
                '<div style="font-size:0.76rem;color:var(--muted);text-align:center;margin-top:0.6rem">'
                'Tài khoản mặc định: <code>admin / admin123</code> · <code>user / user123</code>'
                '</div>',
                unsafe_allow_html=True,
            )

            if submitted:
                if not username or not password:
                    st.warning("⚠️ Vui lòng nhập đầy đủ tên đăng nhập và mật khẩu.")
                else:
                    try:
                        client = ApiClient(api_base_url)
                        data = client.login(username=username, password=password)
                        st.session_state["token"]    = data["token"]
                        st.session_state["username"] = data["username"]
                        st.session_state["role"]     = data["role"]
                        st.success("✅ Đăng nhập thành công!")
                        st.rerun()
                    except Exception as exc:  # noqa: BLE001
                        st.error(f"❌ Đăng nhập thất bại: {exc}")

        # ── REGISTER ───────────────────────────────────────────────────
        elif mode == "register":
            with st.form("form_register", clear_on_submit=False):
                st.markdown(
                    '<div class="auth-step-label"><span class="auth-step-badge">1</span>'
                    'Thông tin tài khoản</div>',
                    unsafe_allow_html=True,
                )
                reg_user  = st.text_input("👤 Tên đăng nhập", placeholder="Tối thiểu 3 ký tự", key="reg_user")
                reg_email = st.text_input("📧 Email", placeholder="example@gmail.com", key="reg_email")
                st.markdown(
                    '<div class="auth-step-label" style="margin-top:0.5rem">'
                    '<span class="auth-step-badge">2</span>Mật khẩu</div>',
                    unsafe_allow_html=True,
                )
                reg_pass  = st.text_input("🔒 Mật khẩu", type="password", placeholder="Tối thiểu 6 ký tự", key="reg_pass")
                reg_pass2 = st.text_input("🔒 Xác nhận mật khẩu", type="password", placeholder="Nhập lại mật khẩu", key="reg_pass2")
                st.markdown("<div style='height:0.3rem'></div>", unsafe_allow_html=True)
                submitted_r = st.form_submit_button("📝 Tạo tài khoản", use_container_width=True)

            if submitted_r:
                if not reg_user or not reg_email or not reg_pass or not reg_pass2:
                    st.warning("⚠️ Vui lòng điền đầy đủ tất cả các trường.")
                elif len(reg_user.strip()) < 3:
                    st.warning("⚠️ Tên đăng nhập phải có ít nhất 3 ký tự.")
                elif "@" not in reg_email or "." not in reg_email.split("@")[-1]:
                    st.warning("⚠️ Địa chỉ email không hợp lệ.")
                elif len(reg_pass) < 6:
                    st.warning("⚠️ Mật khẩu phải có ít nhất 6 ký tự.")
                elif reg_pass != reg_pass2:
                    st.warning("⚠️ Mật khẩu xác nhận không khớp.")
                else:
                    try:
                        client = ApiClient(api_base_url)
                        client.register(
                            username=reg_user.strip(),
                            email=reg_email.strip().lower(),
                            password=reg_pass,
                        )
                        st.success("✅ Đăng ký thành công! Bạn có thể đăng nhập ngay.")
                        st.session_state["auth_mode"] = "login"
                        st.rerun()
                    except Exception as exc:  # noqa: BLE001
                        st.error(f"❌ Đăng ký thất bại: {exc}")

        # ── FORGOT PASSWORD ────────────────────────────────────────────
        elif mode == "forgot":
            otp_sent = st.session_state.get("forgot_otp_sent", False)

            if not otp_sent:
                # Step 1: request OTP
                st.markdown(
                    '<div class="auth-step-label"><span class="auth-step-badge">1</span>'
                    'Nhập thông tin tài khoản</div>',
                    unsafe_allow_html=True,
                )
                with st.form("form_forgot_step1", clear_on_submit=False):
                    fp_user  = st.text_input("👤 Tên đăng nhập", placeholder="Tên đăng nhập của bạn", key="fp_user")
                    fp_email = st.text_input("📧 Email đã đăng ký", placeholder="example@gmail.com", key="fp_email")
                    st.markdown("<div style='height:0.3rem'></div>", unsafe_allow_html=True)
                    send_btn = st.form_submit_button("📨 Gửi mã OTP", use_container_width=True)

                st.markdown(
                    '<div style="font-size:0.76rem;color:var(--muted);text-align:center;margin-top:0.6rem">'
                    '📬 Hệ thống sẽ gửi mã OTP 6 chữ số đến email. Mã có hiệu lực 10 phút.'
                    '</div>',
                    unsafe_allow_html=True,
                )

                if send_btn:
                    if not fp_user or not fp_email:
                        st.warning("⚠️ Vui lòng nhập tên đăng nhập và email.")
                    else:
                        try:
                            client = ApiClient(api_base_url)
                            result = client.forgot_password(
                                username=fp_user.strip(),
                                email=fp_email.strip().lower(),
                            )
                            st.session_state["forgot_otp_sent"] = True
                            st.session_state["forgot_username"]  = fp_user.strip()
                            st.success(f"✅ {result.get('message', 'Đã gửi OTP!')}")
                            st.rerun()
                        except Exception as exc:  # noqa: BLE001
                            st.error(f"❌ {exc}")
            else:
                # Step 2: enter OTP + new password
                st.markdown(
                    '<div style="background:var(--info-bg,#eff6ff);border:1px solid #93c5fd;'
                    'border-radius:8px;padding:0.6rem 0.9rem;font-size:0.82rem;margin-bottom:0.8rem;'
                    'color:var(--text)">'
                    '📨 Mã OTP đã được gửi đến email. Vui lòng kiểm tra hộp thư (kể cả thư mục spam).'
                    '</div>',
                    unsafe_allow_html=True,
                )
                st.markdown(
                    '<div class="auth-step-label"><span class="auth-step-badge">2</span>'
                    'Nhập mã OTP và mật khẩu mới</div>',
                    unsafe_allow_html=True,
                )
                with st.form("form_forgot_step2", clear_on_submit=False):
                    fp_otp   = st.text_input("🔢 Mã OTP (6 chữ số)", placeholder="123456", max_chars=6, key="fp_otp")
                    fp_newpw = st.text_input("🔒 Mật khẩu mới", type="password",
                                             placeholder="Tối thiểu 6 ký tự", key="fp_newpw")
                    fp_conf  = st.text_input("🔒 Xác nhận mật khẩu mới", type="password",
                                             placeholder="Nhập lại", key="fp_conf")
                    st.markdown("<div style='height:0.3rem'></div>", unsafe_allow_html=True)
                    reset_btn = st.form_submit_button("🔓 Đặt lại mật khẩu", use_container_width=True)

                if st.button("← Gửi lại OTP", key="btn_resend_otp"):
                    st.session_state.pop("forgot_otp_sent", None)
                    st.rerun()

                if reset_btn:
                    if not fp_otp or not fp_newpw or not fp_conf:
                        st.warning("⚠️ Vui lòng điền đầy đủ tất cả các trường.")
                    elif len(fp_otp.strip()) != 6 or not fp_otp.strip().isdigit():
                        st.warning("⚠️ Mã OTP phải gồm đúng 6 chữ số.")
                    elif len(fp_newpw) < 6:
                        st.warning("⚠️ Mật khẩu mới phải có ít nhất 6 ký tự.")
                    elif fp_newpw != fp_conf:
                        st.warning("⚠️ Mật khẩu xác nhận không khớp.")
                    else:
                        try:
                            client   = ApiClient(api_base_url)
                            username = st.session_state.get("forgot_username", "")
                            result   = client.reset_password(
                                username=username,
                                otp=fp_otp.strip(),
                                new_password=fp_newpw,
                            )
                            st.success(f"✅ {result.get('message', 'Đặt lại mật khẩu thành công!')}")
                            st.session_state.pop("forgot_otp_sent", None)
                            st.session_state.pop("forgot_username", None)
                            st.session_state["auth_mode"] = "login"
                            st.rerun()
                        except Exception as exc:  # noqa: BLE001
                            st.error(f"❌ {exc}")

