"""
landing.py — Trang chủ MedLink AI (chưa đăng nhập).
====================================================
Gồm: top navbar, hero section với ảnh nền, các section cuộn hiện dần,
     form đăng nhập/đăng ký inline, liên hệ và footer.
"""
from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

# Đảm bảo src/ trên sys.path để import data.assets_config
_SRC_ROOT = Path(__file__).resolve().parents[3]  # src/frontend/app/pages → src/
if str(_SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(_SRC_ROOT))

try:
    from data.assets_config import (  # type: ignore
        FEATURES,
        HOW_TO_USE,
        SYSTEM_STATS,
        get_bg_css,
    )
except Exception:
    FEATURES = []
    HOW_TO_USE = []
    SYSTEM_STATS = {}
    def get_bg_css() -> str:
        return "linear-gradient(135deg,#0d9488,#1e40af)"

from ..services.api_client import ApiClient


# ─────────────────────────────────────────────────────────────────────────────
# CSS cho landing page
# ─────────────────────────────────────────────────────────────────────────────
def _landing_css(bg_css: str) -> str:
    return f"""
<style>
/* ── Ẩn sidebar trên trang chủ ── */
section[data-testid="stSidebar"] {{ display: none !important; }}

/* ── Cho phép các section HTML full-width ── */
.main .block-container {{
  padding-top: 0 !important;
  padding-left: 0 !important;
  padding-right: 0 !important;
  max-width: 100% !important;
}}

/* ── Navbar cố định ── */
.lp-navbar {{
  position: fixed;
  top: 0; left: 0; right: 0;
  z-index: 9999;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 2.5rem;
  height: 60px;
  background: rgba(15,23,42,0.93);
  backdrop-filter: blur(14px);
  border-bottom: 1px solid rgba(255,255,255,0.08);
  box-shadow: 0 2px 24px rgba(0,0,0,0.3);
}}
.lp-logo {{
  font-size: 1.25rem;
  font-weight: 800;
  color: #2dd4bf !important;
  letter-spacing: -0.02em;
  white-space: nowrap;
}}
.lp-logo span {{ color: #fff !important; }}
.lp-nav-links {{
  display: flex;
  align-items: center;
  gap: 0.2rem;
  flex: 1;
  justify-content: center;
}}
.lp-nav-link {{
  padding: 0.35rem 0.9rem;
  color: rgba(255,255,255,0.75) !important;
  font-size: 0.88rem;
  font-weight: 500;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s ease;
  text-decoration: none;
  white-space: nowrap;
}}
.lp-nav-link:hover {{
  color: #2dd4bf !important;
  background: rgba(45,212,191,0.12);
}}
.lp-nav-actions {{
  display: flex;
  gap: 0.6rem;
  align-items: center;
}}
.lp-btn-login {{
  padding: 0.38rem 1.1rem;
  background: transparent;
  border: 1.5px solid rgba(255,255,255,0.35);
  color: #fff;
  border-radius: 8px;
  font-size: 0.86rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
  white-space: nowrap;
  text-decoration: none;
}}
.lp-btn-login:hover {{
  border-color: #2dd4bf;
  color: #2dd4bf;
  background: rgba(45,212,191,0.08);
}}
.lp-btn-register {{
  padding: 0.38rem 1.1rem;
  background: linear-gradient(90deg, #0d9488, #1e40af);
  color: #fff !important;
  border: none;
  border-radius: 8px;
  font-size: 0.86rem;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.22s ease;
  white-space: nowrap;
  text-decoration: none;
  animation: shimmer-btn 3s ease-in-out infinite;
}}
.lp-btn-register:hover {{
  transform: translateY(-1px);
  box-shadow: 0 4px 18px rgba(13,148,136,0.5);
}}

/* ── Hero ── */
.lp-hero {{
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background-image: {bg_css};
  background-size: cover;
  background-position: center;
  background-attachment: fixed;
  position: relative;
  overflow: hidden;
  padding: 80px 2rem 4rem;
}}
.lp-hero::before {{
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(135deg, rgba(13,148,136,0.86) 0%, rgba(30,64,175,0.82) 100%);
}}
.lp-circle {{
  position: absolute;
  border-radius: 50%;
  background: rgba(255,255,255,0.04);
  border: 1px solid rgba(255,255,255,0.08);
  animation: float-circle 8s ease-in-out infinite;
}}
.lp-circle:nth-child(1) {{ width: 380px; height: 380px; top: -90px; right: -70px; }}
.lp-circle:nth-child(2) {{ width: 240px; height: 240px; bottom: 60px; left: -50px; animation-delay: 2.5s; }}
.lp-circle:nth-child(3) {{ width: 150px; height: 150px; top: 35%; right: 18%; animation-delay: 4.5s; }}
@keyframes float-circle {{
  0%,100% {{ transform: translate(0,0) scale(1); }}
  50% {{ transform: translate(12px,-18px) scale(1.04); }}
}}
.lp-hero-content {{
  position: relative;
  z-index: 2;
  text-align: center;
  max-width: 800px;
}}
.lp-hero-badge {{
  display: inline-block;
  background: rgba(255,255,255,0.18);
  border: 1px solid rgba(255,255,255,0.32);
  color: #fff !important;
  border-radius: 999px;
  padding: 0.3rem 1.1rem;
  font-size: 0.78rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  margin-bottom: 1.2rem;
  animation: fade-down 0.7s ease both;
}}
.lp-hero-title {{
  font-size: clamp(2.2rem, 5vw, 3.5rem);
  font-weight: 900;
  color: #fff !important;
  line-height: 1.15;
  margin: 0 0 1rem 0;
  letter-spacing: -0.03em;
  animation: fade-down 0.7s 0.1s ease both;
}}
.lp-hero-title span {{ color: #2dd4bf !important; }}
.lp-hero-desc {{
  font-size: 1.08rem;
  color: rgba(255,255,255,0.9) !important;
  line-height: 1.75;
  margin: 0 0 2.2rem 0;
  animation: fade-down 0.7s 0.2s ease both;
}}
.lp-hero-stats {{
  display: flex;
  gap: 2.5rem;
  justify-content: center;
  margin-top: 2.5rem;
  flex-wrap: wrap;
  animation: fade-down 0.7s 0.35s ease both;
}}
.lp-hero-stat {{ text-align: center; color: #fff !important; }}
.lp-hero-stat-num {{
  font-size: 2.1rem;
  font-weight: 900;
  color: #2dd4bf !important;
  line-height: 1;
}}
.lp-hero-stat-label {{
  font-size: 0.78rem;
  color: rgba(255,255,255,0.72) !important;
  margin-top: 0.25rem;
  letter-spacing: 0.03em;
}}

/* ── Content sections ── */
.lp-section {{
  padding: 5rem 2rem;
  max-width: 1100px;
  margin: 0 auto;
}}
.lp-section-fullbg {{
  padding: 5rem 2rem;
  background: #f8fafc;
}}
.lp-section-title {{
  text-align: center;
  font-size: clamp(1.5rem, 3vw, 2.2rem);
  font-weight: 800;
  color: #1a202c;
  margin-bottom: 0.5rem;
  letter-spacing: -0.02em;
}}
.lp-section-sub {{
  text-align: center;
  color: #64748b;
  font-size: 0.96rem;
  margin-bottom: 3rem;
  line-height: 1.6;
}}
.lp-section-accent {{ color: #0d9488; }}

/* ── Feature cards ── */
.lp-features-grid {{
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(230px, 1fr));
  gap: 1.5rem;
}}
.lp-feature-card {{
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 20px;
  padding: 2rem 1.6rem;
  box-shadow: 0 2px 16px rgba(0,0,0,0.05);
  transition: all 0.3s ease;
  opacity: 0;
  transform: translateY(30px);
}}
.lp-feature-card.visible {{
  opacity: 1;
  transform: translateY(0);
}}
.lp-feature-card:hover {{
  transform: translateY(-6px);
  box-shadow: 0 16px 48px rgba(13,148,136,0.14);
  border-color: #0d9488;
}}
.lp-feature-icon {{
  font-size: 2.4rem;
  margin-bottom: 1rem;
  display: block;
}}
.lp-feature-title {{
  font-size: 1.05rem;
  font-weight: 700;
  color: #1a202c;
  margin-bottom: 0.5rem;
}}
.lp-feature-desc {{
  font-size: 0.88rem;
  color: #64748b;
  line-height: 1.65;
}}

/* ── Steps ── */
.lp-steps-grid {{
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 2rem;
  max-width: 1100px;
  margin: 0 auto;
}}
.lp-step {{
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 20px;
  padding: 1.8rem 1.4rem;
  text-align: center;
  box-shadow: 0 2px 12px rgba(0,0,0,0.04);
  opacity: 0;
  transform: translateY(24px);
  transition: all 0.4s ease;
}}
.lp-step.visible {{ opacity: 1; transform: translateY(0); }}
.lp-step:hover {{
  transform: translateY(-4px);
  box-shadow: 0 8px 32px rgba(13,148,136,0.12);
  border-color: #0d9488;
}}
.lp-step-num {{
  width: 52px;
  height: 52px;
  border-radius: 50%;
  background: linear-gradient(135deg, #0d9488, #1e40af);
  color: #fff;
  font-size: 1.1rem;
  font-weight: 900;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 1rem auto;
  box-shadow: 0 4px 16px rgba(13,148,136,0.4);
}}
.lp-step-title {{
  font-size: 1rem;
  font-weight: 700;
  color: #1a202c;
  margin-bottom: 0.5rem;
}}
.lp-step-desc {{
  font-size: 0.86rem;
  color: #64748b;
  line-height: 1.6;
}}

/* ── Auth card ── */
.lp-auth-wrapper {{
  padding: 4rem 2rem 5rem;
  background: linear-gradient(180deg, #f0f4f9 0%, #fff 100%);
}}
.lp-auth-card {{
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 24px;
  padding: 2.5rem 2rem;
  box-shadow: 0 8px 40px rgba(0,0,0,0.08);
  max-width: 460px;
  margin: 0 auto;
}}
.lp-auth-logo {{
  text-align: center;
  margin-bottom: 1.5rem;
}}
.lp-auth-logo-icon {{ font-size: 3rem; line-height: 1; }}
.lp-auth-logo-title {{
  font-size: 1.6rem;
  font-weight: 800;
  color: #0d9488;
  margin-top: 0.3rem;
}}
.lp-auth-logo-sub {{
  font-size: 0.8rem;
  color: #64748b;
  margin-top: 0.2rem;
}}
.lp-auth-tabs {{
  display: flex;
  gap: 0.5rem;
  margin-bottom: 1.5rem;
  background: #f1f5f9;
  border-radius: 12px;
  padding: 0.3rem;
}}
.lp-auth-tab {{
  flex: 1;
  padding: 0.5rem 0.5rem;
  text-align: center;
  border-radius: 10px;
  font-size: 0.88rem;
  font-weight: 600;
  color: #64748b;
  cursor: pointer;
  transition: all 0.2s ease;
  border: none;
  background: transparent;
}}
.lp-auth-tab.active {{
  background: #fff;
  color: #0d9488;
  box-shadow: 0 1px 8px rgba(0,0,0,0.08);
}}

/* Navbar: ẩn placeholder span (chỉ giữ layout) */
.lp-btn-nav-placeholder {{
  visibility: hidden !important;
  pointer-events: none !important;
}}

/* CTA button row trong hero — bo tròn, nền mờ */
div[data-testid="stHorizontalBlock"]:has(button[kind="primaryFormSubmit"]),
div[data-testid="stHorizontalBlock"]:has([data-testid="baseButton-primary"]) {{
  background: rgba(255,255,255,0.08) !important;
  border: 1px solid rgba(255,255,255,0.18) !important;
  border-radius: 20px !important;
  padding: 0.9rem 1.2rem !important;
  backdrop-filter: blur(10px) !important;
  max-width: 700px !important;
  margin: 0 auto !important;
}}

/* Input rounded */
.stTextArea textarea,
.stSelectbox > div > div,
.stNumberInput input {{
  border-radius: 12px !important;
  border: 1.5px solid #e2e8f0 !important;
  padding: 0.55rem 0.9rem !important;
  font-size: 0.92rem !important;
  transition: border-color 0.2s ease, box-shadow 0.2s ease !important;
}}
.stTextInput > div > div > input:focus,
.stTextArea textarea:focus {{
  border-color: #0d9488 !important;
  box-shadow: 0 0 0 3px rgba(13,148,136,0.12) !important;
  outline: none !important;
}}
.stTextInput label,
.stTextArea label,
.stSelectbox label {{
  font-size: 0.83rem !important;
  font-weight: 600 !important;
  color: #374151 !important;
  margin-bottom: 0.25rem !important;
}}
.stFormSubmitButton > button {{
  border-radius: 12px !important;
  padding: 0.65rem 1rem !important;
  font-size: 0.95rem !important;
}}

/* ── Contact section ── */
.lp-contact-section {{
  background: #0f172a;
  padding: 4rem 2rem;
  color: #fff;
}}
.lp-contact-grid {{
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 2.5rem;
  max-width: 1100px;
  margin: 0 auto;
}}
.lp-contact-block h3 {{
  font-size: 1rem;
  font-weight: 700;
  color: #2dd4bf;
  margin-bottom: 1rem;
  text-transform: uppercase;
  letter-spacing: 0.06em;
}}
.lp-contact-item {{
  display: flex;
  align-items: center;
  gap: 0.7rem;
  margin-bottom: 0.8rem;
  font-size: 0.88rem;
  color: rgba(255,255,255,0.72) !important;
  text-decoration: none;
  transition: color 0.2s ease;
}}
.lp-contact-item:hover {{ color: #2dd4bf !important; }}
.lp-contact-icon {{
  width: 36px; height: 36px;
  border-radius: 10px;
  display: flex; align-items: center; justify-content: center;
  font-size: 1.1rem;
  flex-shrink: 0;
}}
.lp-fb-icon {{ background: #1877f2; }}
.lp-gmail-icon {{ background: #ea4335; }}
.lp-phone-icon {{ background: #0d9488; }}
.lp-addr-icon {{ background: #7c3aed; }}

/* ── Footer ── */
.lp-footer {{
  background: #0a0f1e;
  color: rgba(255,255,255,0.45) !important;
  padding: 1.5rem 2rem;
  text-align: center;
  font-size: 0.82rem;
  border-top: 1px solid rgba(255,255,255,0.06);
}}
.lp-footer a {{ color: #2dd4bf !important; text-decoration: none; }}

/* ── CTA banner ── */
.lp-cta-banner {{
  background: linear-gradient(135deg, #0d9488 0%, #1e40af 100%);
  padding: 3.5rem 2rem;
  text-align: center;
  position: relative;
  overflow: hidden;
}}
.lp-cta-banner::before {{
  content: '';
  position: absolute;
  top: -40%; left: -15%;
  width: 500px; height: 500px;
  border-radius: 50%;
  background: rgba(255,255,255,0.04);
}}
.lp-cta-banner h2 {{
  font-size: 2rem;
  font-weight: 800;
  color: #fff !important;
  margin-bottom: 0.7rem;
  position: relative;
}}
.lp-cta-banner p {{
  color: rgba(255,255,255,0.85) !important;
  font-size: 1rem;
  position: relative;
  max-width: 600px;
  margin: 0 auto;
  line-height: 1.65;
}}

/* ── Animations ── */
@keyframes fade-down {{
  from {{ opacity: 0; transform: translateY(-18px); }}
  to {{ opacity: 1; transform: translateY(0); }}
}}
@keyframes shimmer-btn {{
  0%,100% {{ box-shadow: 0 0 0 0 rgba(13,148,136,0); }}
  50% {{ box-shadow: 0 0 20px 4px rgba(13,148,136,0.4); }}
}}
.scroll-reveal {{
  opacity: 0;
  transform: translateY(32px);
  transition: opacity 0.65s ease, transform 0.65s ease;
}}
.scroll-reveal.visible {{
  opacity: 1;
  transform: translateY(0);
}}
</style>

<script>
(function() {{
  function initObs() {{
    var els = document.querySelectorAll('.lp-feature-card, .lp-step, .scroll-reveal');
    if (!els.length) return;
    var obs = new IntersectionObserver(function(entries) {{
      entries.forEach(function(e) {{
        if (e.isIntersecting) e.target.classList.add('visible');
      }});
    }}, {{ threshold: 0.1 }});
    els.forEach(function(el) {{ obs.observe(el); }});
  }}
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', initObs);
  else {{ initObs(); setTimeout(initObs, 400); setTimeout(initObs, 1000); }}
}})();
</script>
"""


def _retrigger_js() -> str:
    return """
<script>
setTimeout(function(){
  // Scroll reveal observer
  var els=document.querySelectorAll('.lp-feature-card,.lp-step,.scroll-reveal');
  var obs=new IntersectionObserver(function(es){es.forEach(function(e){if(e.isIntersecting)e.target.classList.add('visible');});},{threshold:0.08});
  els.forEach(function(el){obs.observe(el);});

  // Gán id cho hidden Streamlit buttons để navbar có thể click vào
  function tagHiddenBtns() {
    // Tìm button có title/aria-label = "open login" / "open register" (Streamlit dùng help= làm title)
    var loginBtn = document.querySelector('button[title="open login"]');
    var regBtn   = document.querySelector('button[title="open register"]');
    if (loginBtn) loginBtn.id = 'lp_open_login';
    if (regBtn)   regBtn.id   = 'lp_open_register';
    return !!(loginBtn && regBtn);
  }
  if (!tagHiddenBtns()) { setTimeout(tagHiddenBtns, 600); setTimeout(tagHiddenBtns, 1500); }
},350);
</script>"""


# ─────────────────────────────────────────────────────────────────────────────
# Render helpers
# ─────────────────────────────────────────────────────────────────────────────

def _render_navbar() -> None:
    st.markdown(
        """
        <div class="lp-navbar">
          <div class="lp-logo">💊 Med<span>Link AI</span></div>
          <nav class="lp-nav-links">
            <a class="lp-nav-link" href="#gioi-thieu">🏠 Trang chủ</a>
            <a class="lp-nav-link" href="#tinh-nang">✨ Tính năng</a>
            <a class="lp-nav-link" href="#huong-dan">📖 Hướng dẫn</a>
            <a class="lp-nav-link" href="#gop-y">💬 Góp ý</a>
            <a class="lp-nav-link" href="#lien-he">📞 Liên hệ</a>
          </nav>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Hero section căn giữa — thay thế hero split bị lỗi CSS variable
# ─────────────────────────────────────────────────────────────────────────────

def _render_hero_centered(stats: dict) -> None:
    """Hero section căn giữa với title, mô tả, stats và CTA buttons trong hero."""
    drugs    = stats.get("drugs",    "1,400+")
    diseases = stats.get("diseases", "400+")
    proteins = stats.get("proteins", "900+")
    links    = stats.get("links",    "5,000+")
    st.markdown(
        f"""
        <div class="lp-hero" id="gioi-thieu">
          <div class="lp-circle"></div>
          <div class="lp-circle"></div>
          <div class="lp-circle"></div>
          <div class="lp-hero-content">
            <div class="lp-hero-badge">🧬 AI Drug-Disease Intelligence</div>
            <h1 class="lp-hero-title">
              Khám phá liên kết<br>
              <span>Thuốc &ndash; Bệnh</span><br>
              bằng AI
            </h1>
            <p class="lp-hero-desc">
              FuzzyGCN kết hợp Fuzzy Logic + Residual GCN để dự đoán liên kết<br>
              thuốc&ndash;bệnh&ndash;protein với <strong>AUC &gt; 0.95</strong> trên dữ liệu chuẩn quốc tế.
            </p>
            <div class="lp-hero-stats">
              <div class="lp-hero-stat">
                <div class="lp-hero-stat-num">{drugs}</div>
                <div class="lp-hero-stat-label">Loại thuốc</div>
              </div>
              <div class="lp-hero-stat">
                <div class="lp-hero-stat-num">{diseases}</div>
                <div class="lp-hero-stat-label">Loại bệnh</div>
              </div>
              <div class="lp-hero-stat">
                <div class="lp-hero-stat-num">{proteins}</div>
                <div class="lp-hero-stat-label">Protein</div>
              </div>
              <div class="lp-hero-stat">
                <div class="lp-hero-stat-num">{links}</div>
                <div class="lp-hero-stat-label">Liên kết xác nhận</div>
              </div>
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# CSS bổ sung cho hero split (giữ lại để tham khảo)
_HERO_SPLIT_CSS = """
<style>
.lp-hero-split {
  background-image: var(--lp-bg);
  background-size: cover;
  background-position: center;
  background-attachment: fixed;
  position: relative;
  min-height: 100vh;
  overflow: hidden;
}
.lp-hero-split::before {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(135deg, rgba(13,148,136,0.9) 0%, rgba(30,64,175,0.88) 100%);
  pointer-events: none;
  z-index: 0;
}
.lp-hero-cols {
  position: relative;
  z-index: 1;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 2.5rem;
  max-width: 1200px;
  margin: 0 auto;
  padding: 5rem 2.5rem 4rem;
}
@media (max-width: 900px) {
  .lp-hero-cols { grid-template-columns: 1fr; }
}
/* --- Auth card inside hero --- */
.hero-auth-card {
  background: rgba(255,255,255,0.97);
  border-radius: 24px;
  padding: 2.2rem 1.8rem;
  box-shadow: 0 16px 64px rgba(0,0,0,0.22);
  align-self: start;
  position: sticky;
  top: 80px;
}
.hero-auth-logo { text-align: center; margin-bottom: 1.2rem; }
.hero-auth-logo-title { font-size: 1.4rem; font-weight: 800; color: #0d9488; margin-top: 0.2rem; }
.hero-auth-logo-sub { font-size: 0.76rem; color: #64748b; }
/* tab row in auth card */
.hero-auth-tabs { display: flex; gap: 0.4rem; background: #f1f5f9; border-radius: 12px; padding: 0.25rem; margin-bottom: 1.2rem; }
.hero-auth-tab { flex: 1; text-align: center; padding: 0.45rem 0.3rem; border-radius: 10px; font-size: 0.82rem; font-weight: 600; color: #64748b; cursor: pointer; border: none; background: transparent; transition: all 0.2s; }
.hero-auth-tab.active { background: #fff; color: #0d9488; box-shadow: 0 1px 6px rgba(0,0,0,0.1); }
/* --- Right features column --- */
.hero-right { color: #fff; }
.hero-right-title { font-size: clamp(1.8rem,3.5vw,2.8rem); font-weight: 900; line-height: 1.15; margin-bottom: 0.8rem; letter-spacing: -0.02em; }
.hero-right-title span { color: #2dd4bf; }
.hero-right-desc { font-size: 0.97rem; color: rgba(255,255,255,0.88); line-height: 1.7; margin-bottom: 2rem; }
.hero-feat-list { display: flex; flex-direction: column; gap: 0.9rem; }
.hero-feat-item { display: flex; align-items: flex-start; gap: 0.9rem; background: rgba(255,255,255,0.1); border: 1px solid rgba(255,255,255,0.18); border-radius: 14px; padding: 0.9rem 1rem; backdrop-filter: blur(6px); transition: all 0.2s ease; cursor: pointer; }
.hero-feat-item:hover { background: rgba(255,255,255,0.18); transform: translateX(4px); }
.hero-feat-icon { font-size: 1.6rem; flex-shrink: 0; line-height: 1; }
.hero-feat-body {}
.hero-feat-title { font-size: 0.92rem; font-weight: 700; color: #fff; margin-bottom: 0.2rem; }
.hero-feat-desc { font-size: 0.8rem; color: rgba(255,255,255,0.72); line-height: 1.5; }
.hero-feat-badge { display: inline-block; font-size: 0.67rem; font-weight: 700; padding: 0.15rem 0.5rem; border-radius: 999px; margin-left: 0.4rem; vertical-align: middle; }
.badge-free { background: rgba(45,212,191,0.25); color: #2dd4bf; border: 1px solid rgba(45,212,191,0.4); }
.badge-login { background: rgba(251,191,36,0.2); color: #fbbf24; border: 1px solid rgba(251,191,36,0.35); }
/* stats bar */
.hero-stats-bar { display: flex; gap: 1.5rem; flex-wrap: wrap; margin-top: 2rem; }
.hero-stat { text-align: center; }
.hero-stat-num { font-size: 1.8rem; font-weight: 900; color: #2dd4bf; line-height: 1; }
.hero-stat-label { font-size: 0.73rem; color: rgba(255,255,255,0.65); margin-top: 0.2rem; }
/* guest divider */
.guest-divider { display: flex; align-items: center; gap: 0.6rem; margin: 1rem 0; color: #94a3b8; font-size: 0.78rem; }
.guest-divider::before, .guest-divider::after { content: ''; flex: 1; border-top: 1px solid #e2e8f0; }
</style>
"""

_FEATURES_RIGHT = [
    {"icon": "🔬", "title": "Tra cứu bệnh theo thuốc", "desc": "Nhập tên thuốc, AI trả về danh sách bệnh có liên quan kèm xác suất.", "free": True},
    {"icon": "🦠", "title": "Tra cứu thuốc theo bệnh", "desc": "Nhập tên bệnh, AI gợi ý các thuốc tiềm năng đã xác nhận và dự đoán mới.", "free": True},
    {"icon": "📊", "title": "Lưu lịch sử & xuất báo cáo", "desc": "Lưu toàn bộ kết quả tra cứu, xuất CSV để phân tích ngoài hệ thống.", "free": False},
    {"icon": "🛡️", "title": "Quản lý tài khoản & phân quyền", "desc": "Quản trị viên có thể thêm, sửa, phân quyền người dùng.", "free": False},
]


def _render_hero_split(stats: dict, api_base_url: str) -> None:
    """Hero 2 cột: trái = auth card, phải = mô tả tính năng."""
    drugs    = stats.get("drugs",    "1,400+")
    diseases = stats.get("diseases", "400+")
    proteins = stats.get("proteins", "900+")
    links    = stats.get("links",    "5,000+")

    # CSS bổ sung
    st.markdown(_HERO_SPLIT_CSS, unsafe_allow_html=True)

    # Background wrapper (HTML) — mở div
    st.markdown(
        '<div class="lp-hero-split" id="gioi-thieu"><div class="lp-circle"></div>'
        '<div class="lp-circle"></div><div class="lp-circle"></div>',
        unsafe_allow_html=True,
    )

    # Nội dung 2 cột bằng CSS grid — sử dụng columns Streamlit
    # Spacer cho navbar
    st.markdown('<div style="height:60px"></div>', unsafe_allow_html=True)
    col_auth, col_feat = st.columns([1, 1.15], gap="large")

    # ─── CỘT TRÁI: Auth card ──────────────────────────────────────────────
    with col_auth:
        st.markdown(
            '<div style="background:rgba(255,255,255,0.97);border-radius:24px;'
            'padding:1.8rem 1.6rem;box-shadow:0 16px 64px rgba(0,0,0,0.22);">',
            unsafe_allow_html=True,
        )
        # Logo
        st.markdown(
            '<div style="text-align:center;margin-bottom:1rem">'
            '<div style="font-size:2.4rem;line-height:1">💊</div>'
            '<div style="font-size:1.3rem;font-weight:800;color:#0d9488;margin-top:0.2rem">MedLink AI</div>'
            '<div style="font-size:0.74rem;color:#64748b;margin-top:0.15rem">'
            'Drug–Disease Intelligence Platform</div></div>',
            unsafe_allow_html=True,
        )

        mode = st.session_state.get("auth_mode", "login")
        t1, t2, t3 = st.columns(3)
        with t1:
            if st.button("🔑 Đăng nhập", use_container_width=True,
                         type="primary" if mode == "login" else "secondary",
                         key="hero_tab_login"):
                st.session_state["auth_mode"] = "login"; st.rerun()
        with t2:
            if st.button("📝 Đăng ký", use_container_width=True,
                         type="primary" if mode == "register" else "secondary",
                         key="hero_tab_reg"):
                st.session_state["auth_mode"] = "register"; st.rerun()
        with t3:
            if st.button("🔓 Quên MK", use_container_width=True,
                         type="primary" if mode == "forgot" else "secondary",
                         key="hero_tab_forgot"):
                st.session_state["auth_mode"] = "forgot"
                st.session_state.pop("forgot_otp_sent", None); st.rerun()

        st.markdown('<div style="height:0.6rem"></div>', unsafe_allow_html=True)

        if mode == "login":
            with st.form("hero_form_login", clear_on_submit=False):
                u = st.text_input("👤 Tên đăng nhập", placeholder="Nhập tên đăng nhập", key="h_li_u")
                p = st.text_input("🔒 Mật khẩu", type="password", placeholder="Nhập mật khẩu", key="h_li_p")
                ok = st.form_submit_button("🔑 Đăng nhập", use_container_width=True)
            st.markdown(
                '<div style="font-size:0.72rem;color:#94a3b8;text-align:center;margin:0.3rem 0">'
                'Demo: <code>admin/admin123</code> · <code>user/user123</code></div>',
                unsafe_allow_html=True,
            )
            if ok:
                if not u or not p:
                    st.warning("⚠️ Vui lòng nhập đầy đủ thông tin.")
                else:
                    try:
                        data = ApiClient(api_base_url).login(username=u, password=p)
                        st.session_state.update({"token": data["token"], "username": data["username"], "role": data["role"]})
                        st.rerun()
                    except Exception as exc:
                        st.error(f"❌ {exc}")

        elif mode == "register":
            with st.form("hero_form_reg", clear_on_submit=False):
                ru = st.text_input("👤 Tên đăng nhập", placeholder="Tối thiểu 3 ký tự", key="h_r_u")
                re_ = st.text_input("📧 Email", placeholder="example@gmail.com", key="h_r_e")
                rp = st.text_input("🔒 Mật khẩu", type="password", placeholder="Tối thiểu 6 ký tự", key="h_r_p")
                rp2 = st.text_input("🔒 Xác nhận", type="password", placeholder="Nhập lại", key="h_r_p2")
                sok = st.form_submit_button("📝 Tạo tài khoản", use_container_width=True)
            if sok:
                if not ru or not re_ or not rp or not rp2:
                    st.warning("⚠️ Vui lòng điền đầy đủ các trường.")
                elif len(ru.strip()) < 3:
                    st.warning("⚠️ Tên đăng nhập tối thiểu 3 ký tự.")
                elif "@" not in re_:
                    st.warning("⚠️ Email không hợp lệ.")
                elif len(rp) < 6:
                    st.warning("⚠️ Mật khẩu tối thiểu 6 ký tự.")
                elif rp != rp2:
                    st.warning("⚠️ Mật khẩu không khớp.")
                else:
                    try:
                        ApiClient(api_base_url).register(username=ru.strip(), email=re_.strip().lower(), password=rp)
                        st.success("✅ Đăng ký thành công! Hãy đăng nhập.")
                        st.session_state["auth_mode"] = "login"; st.rerun()
                    except Exception as exc:
                        st.error(f"❌ {exc}")

        elif mode == "forgot":
            _render_forgot_password(api_base_url)

        # Guest divider
        st.markdown(
            '<div style="display:flex;align-items:center;gap:0.6rem;margin:0.8rem 0;'
            'color:#94a3b8;font-size:0.78rem">'
            '<span style="flex:1;border-top:1px solid #e2e8f0"></span>'
            '<span>hoặc</span>'
            '<span style="flex:1;border-top:1px solid #e2e8f0"></span></div>',
            unsafe_allow_html=True,
        )
        if st.button(
            "👤 Tiếp tục không cần đăng nhập (Khách)",
            use_container_width=True,
            key="hero_guest_btn",
            help="Chỉ được tra cứu thuốc/bệnh. Không lưu lịch sử, không xuất báo cáo.",
        ):
            st.session_state["role"] = "guest"
            st.session_state["username"] = "Khách"
            st.session_state["token"] = None  # Guest: không có token, không gửi Authorization header
            st.rerun()

        st.markdown('</div>', unsafe_allow_html=True)

    # ─── CỘT PHẢI: Tính năng ──────────────────────────────────────────────
    with col_feat:
        feat_html = (
            '<div style="color:#fff;padding-top:0.5rem">'
            '<span style="display:inline-block;background:rgba(255,255,255,0.18);'
            'border:1px solid rgba(255,255,255,0.32);color:#fff;border-radius:999px;'
            'padding:0.25rem 1rem;font-size:0.74rem;font-weight:700;letter-spacing:0.08em;'
            'text-transform:uppercase;margin-bottom:1rem">🧬 AI Drug-Disease Intelligence</span>'
            '<h1 style="font-size:clamp(1.8rem,3.5vw,2.8rem);font-weight:900;line-height:1.15;'
            'margin:0 0 0.8rem;letter-spacing:-0.02em">'
            'Khám phá liên kết<br><span style="color:#2dd4bf">Thuốc – Bệnh</span><br>bằng AI</h1>'
            '<p style="font-size:0.95rem;color:rgba(255,255,255,0.85);line-height:1.7;margin-bottom:1.5rem">'
            'FuzzyGCN kết hợp Fuzzy Logic + Residual GCN để dự đoán '
            'liên kết thuốc–bệnh–protein với <strong>AUC &gt; 0.95</strong>.</p>'
            '<div style="display:flex;flex-direction:column;gap:0.7rem">'
        )
        for f in _FEATURES_RIGHT:
            badge = (
                '<span style="display:inline-block;font-size:0.67rem;font-weight:700;'
                'padding:0.12rem 0.5rem;border-radius:999px;margin-left:0.4rem;'
                'background:rgba(45,212,191,0.25);color:#2dd4bf;border:1px solid rgba(45,212,191,0.4)">'
                'Miễn phí</span>'
            ) if f["free"] else (
                '<span style="display:inline-block;font-size:0.67rem;font-weight:700;'
                'padding:0.12rem 0.5rem;border-radius:999px;margin-left:0.4rem;'
                'background:rgba(251,191,36,0.2);color:#fbbf24;border:1px solid rgba(251,191,36,0.35)">'
                'Cần đăng nhập</span>'
            )
            feat_html += (
                '<div style="display:flex;align-items:flex-start;gap:0.8rem;'
                'background:rgba(255,255,255,0.1);border:1px solid rgba(255,255,255,0.18);'
                'border-radius:14px;padding:0.85rem 1rem;backdrop-filter:blur(6px)">'
                '<span style="font-size:1.5rem;flex-shrink:0;line-height:1">' + f["icon"] + '</span>'
                '<div><div style="font-size:0.9rem;font-weight:700;color:#fff">' + f["title"] + badge + '</div>'
                '<div style="font-size:0.78rem;color:rgba(255,255,255,0.72);line-height:1.5;margin-top:0.2rem">' + f["desc"] + '</div></div></div>'
            )
        feat_html += '</div>'
        # Stats bar
        feat_html += (
            '<div style="display:flex;gap:1.5rem;flex-wrap:wrap;margin-top:1.8rem">'
            '<div style="text-align:center"><div style="font-size:1.7rem;font-weight:900;color:#2dd4bf">' + drugs + '</div>'
            '<div style="font-size:0.72rem;color:rgba(255,255,255,0.65)">Loại thuốc</div></div>'
            '<div style="text-align:center"><div style="font-size:1.7rem;font-weight:900;color:#2dd4bf">' + diseases + '</div>'
            '<div style="font-size:0.72rem;color:rgba(255,255,255,0.65)">Loại bệnh</div></div>'
            '<div style="text-align:center"><div style="font-size:1.7rem;font-weight:900;color:#2dd4bf">' + proteins + '</div>'
            '<div style="font-size:0.72rem;color:rgba(255,255,255,0.65)">Protein</div></div>'
            '<div style="text-align:center"><div style="font-size:1.7rem;font-weight:900;color:#2dd4bf">' + links + '</div>'
            '<div style="font-size:0.72rem;color:rgba(255,255,255,0.65)">Liên kết xác nhận</div></div>'
            '</div></div>'
        )
        st.markdown(feat_html, unsafe_allow_html=True)

    # Đóng div background
    st.markdown('</div>', unsafe_allow_html=True)


def _render_features(features: list) -> None:
    if not features:
        features = [
            {
                "icon": "🔬",
                "title": "Dự đoán AI chính xác cao",
                "desc": "Mô hình FuzzyGCN kết hợp Fuzzy Logic + Residual GCN học trên đồ thị đa chiều thuốc–bệnh–protein, đạt AUC > 0.95 trên các tập dữ liệu chuẩn quốc tế.",
            },
            {
                "icon": "⚡",
                "title": "Tra cứu tức thì, không chờ đợi",
                "desc": "Chỉ cần nhập tên thuốc hoặc bệnh, hệ thống trả về danh sách dự đoán đầy đủ trong vòng vài giây nhờ inference engine được tối ưu hoá.",
            },
            {
                "icon": "📊",
                "title": "Dữ liệu minh bạch & có nguồn gốc",
                "desc": "Mỗi kết quả đều được phân loại rõ: liên kết ✅ đã xác nhận thực nghiệm (từ OMIM, DrugBank) hay 🔬 AI dự đoán mới, kèm điểm xác suất cụ thể.",
            },
            {
                "icon": "🛡️",
                "title": "Bảo mật & phân quyền đa cấp",
                "desc": "Hệ thống xác thực JWT, phân quyền Admin/User rõ ràng. Toàn bộ dữ liệu người dùng và lịch sử tra cứu được bảo vệ an toàn.",
            },
            {
                "icon": "🗂️",
                "title": "Đa tập dữ liệu chuẩn quốc tế",
                "desc": "Hỗ trợ 3 tập dữ liệu chuẩn: B-dataset, C-dataset và F-dataset — cho phép so sánh kết quả dự đoán trên các cơ sở dữ liệu khác nhau.",
            },
            {
                "icon": "📈",
                "title": "Theo dõi & xuất báo cáo",
                "desc": "Lưu toàn bộ lịch sử tra cứu, hỗ trợ xuất file CSV để phân tích ngoài hệ thống. Admin có thể xem thống kê tổng quan hoạt động.",
            },
        ]
    cards_html = ""
    for i, f in enumerate(features):
        delay = i * 0.1
        cards_html += f"""
        <div class="lp-feature-card" style="transition-delay:{delay}s">
          <span class="lp-feature-icon">{f['icon']}</span>
          <div class="lp-feature-title">{f['title']}</div>
          <div class="lp-feature-desc">{f['desc']}</div>
        </div>"""

    st.markdown(
        f"""
        <div style="padding:5rem 2rem;background:#f8fafc" id="tinh-nang">
          <div style="max-width:1100px;margin:0 auto">
            <h2 class="lp-section-title">Tại sao chọn <span class="lp-section-accent">MedLink AI</span>?</h2>
            <p class="lp-section-sub">
              Hệ thống tích hợp trí tuệ nhân tạo tiên tiến, dữ liệu y sinh học chuẩn quốc tế<br>
              và giao diện trực quan — giúp nghiên cứu dược phẩm nhanh hơn, chính xác hơn.
            </p>
            <div class="lp-features-grid">{cards_html}</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_how_to_use(steps: list) -> None:
    if not steps:
        steps = [
            {
                "step": "1",
                "title": "Tạo tài khoản",
                "desc": "Đăng ký tài khoản miễn phí chỉ trong 30 giây. Chỉ cần tên đăng nhập, email và mật khẩu — không cần xác minh phức tạp.",
            },
            {
                "step": "2",
                "title": "Chọn dataset & chức năng",
                "desc": "Chọn tập dữ liệu phù hợp (B/C/F-dataset) và loại tra cứu: dự đoán bệnh theo thuốc hay dự đoán thuốc theo bệnh.",
            },
            {
                "step": "3",
                "title": "Nhập từ khoá tìm kiếm",
                "desc": "Nhập tên thuốc hoặc bệnh vào ô tìm kiếm. Hệ thống hỗ trợ tìm kiếm gần đúng và gợi ý tự động từ danh sách có sẵn.",
            },
            {
                "step": "4",
                "title": "Xem kết quả AI & xuất báo cáo",
                "desc": "AI trả về danh sách liên kết kèm điểm xác suất. Xem chi tiết thông tin từng thuốc/bệnh, hoặc xuất toàn bộ kết quả ra file CSV.",
            },
        ]
    steps_html = ""
    for i, s in enumerate(steps):
        delay = i * 0.14
        steps_html += f"""
        <div class="lp-step" style="transition-delay:{delay}s">
          <div class="lp-step-num">{s['step']}</div>
          <div class="lp-step-title">{s['title']}</div>
          <div class="lp-step-desc">{s['desc']}</div>
        </div>"""

    st.markdown(
        f"""
        <div style="padding:5rem 2rem" id="huong-dan">
          <h2 class="lp-section-title">Cách sử dụng hệ thống</h2>
          <p class="lp-section-sub">
            Giao diện đơn giản, thân thiện — không yêu cầu kiến thức kỹ thuật chuyên sâu.<br>
            Chỉ cần 4 bước là bắt đầu khám phá ngay.
          </p>
          <div class="lp-steps-grid">{steps_html}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_cta_banner() -> None:
    st.markdown(
        """
        <div class="lp-cta-banner">
          <h2>🚀 Bắt đầu khám phá ngay hôm nay</h2>
          <p>
            Đăng ký hoàn toàn miễn phí — trải nghiệm sức mạnh của AI đồ thị
            trong việc khám phá các liên kết thuốc–bệnh tiềm năng.
            Phù hợp cho nghiên cứu sinh, dược sĩ và các nhà khoa học y sinh học.
          </p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_feedback_section() -> None:
    st.markdown(
        """
        <div style="padding:5rem 2rem 3rem;background:#f8fafc" id="gop-y">
          <h2 class="lp-section-title">💬 Góp ý & Phản hồi</h2>
          <p class="lp-section-sub">
            Ý kiến của bạn giúp chúng tôi cải thiện hệ thống mỗi ngày.<br>
            Hãy chia sẻ trải nghiệm, báo lỗi, hoặc đề xuất tính năng mới — chúng tôi đọc từng phản hồi.
          </p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    col1, col2, col3 = st.columns([1, 2.2, 1])
    with col2:
        with st.form("feedback_form_landing", clear_on_submit=True):
            name_val  = st.text_input("👤 Họ tên của bạn", placeholder="Nguyễn Văn A")
            email_val = st.text_input("📧 Địa chỉ email", placeholder="example@gmail.com")
            subject_val = st.selectbox(
                "📂 Loại góp ý",
                ["Báo lỗi hệ thống", "Đề xuất tính năng mới", "Hỏi về kết quả dự đoán", "Góp ý giao diện", "Khác"],
            )
            feedback_val = st.text_area(
                "✍️ Nội dung chi tiết",
                placeholder="Mô tả chi tiết góp ý của bạn, bao gồm các bước tái hiện lỗi (nếu có)...",
                height=140,
            )
            submitted = st.form_submit_button("📨 Gửi góp ý", use_container_width=True)
            if submitted:
                if feedback_val.strip():
                    st.success("✅ Cảm ơn bạn đã góp ý! Chúng tôi sẽ xem xét và phản hồi trong vòng 24–48 giờ.")
                else:
                    st.warning("⚠️ Vui lòng nhập nội dung góp ý trước khi gửi.")


def _render_contact_section() -> None:
    col_style = "background:#162032;border-radius:16px;padding:1.8rem 1.6rem"
    h3_style  = "font-size:0.9rem;font-weight:700;color:#2dd4bf;margin:0 0 1rem 0;text-transform:uppercase;letter-spacing:0.07em"
    row_style = "display:flex;align-items:center;gap:0.7rem;margin-bottom:0.9rem;font-size:0.88rem;color:rgba(255,255,255,0.75);text-decoration:none"
    icon_base = "width:38px;height:38px;border-radius:10px;display:flex;align-items:center;justify-content:center;font-size:1.1rem;flex-shrink:0"

    html = (
        '<div id="lien-he" style="background:#0f172a;padding:4rem 2rem">'
        '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));'
        'gap:1.5rem;max-width:1100px;margin:0 auto">'

        # Cột 1: giới thiệu
        + '<div style="' + col_style + '">'
        + '<h3 style="' + h3_style + '">💊 MedLink AI</h3>'
        + '<p style="font-size:0.87rem;color:rgba(255,255,255,0.62);line-height:1.7;margin-bottom:1rem">'
        + 'Hệ thống dự đoán liên kết thuốc–bệnh sử dụng mô hình đồ thị thần kinh '
        + '<strong style="color:#2dd4bf">FuzzyGCN</strong>. '
        + 'Hỗ trợ nghiên cứu dược phẩm &amp; y sinh học tại Việt Nam.</p>'
        + '<div style="font-size:0.77rem;color:rgba(255,255,255,0.35);letter-spacing:0.04em">'
        + 'v1.0 · FuzzyGCN · Drug–Disease Intelligence</div></div>'

        # Cột 2: liên hệ
        + '<div style="' + col_style + '">'
        + '<h3 style="' + h3_style + '">📞 Liên hệ với chúng tôi</h3>'

        + '<a href="https://www.facebook.com/medlinkai" target="_blank" style="' + row_style + '">'
        + '<div style="' + icon_base + ';background:#1877f2">📘</div>'
        + '<div><div style="font-weight:700;color:#fff;font-size:0.9rem">Facebook</div>'
        + '<div style="font-size:0.82rem">facebook.com/medlinkai</div></div></a>'

        + '<a href="mailto:medlinkai@gmail.com" style="' + row_style + '">'
        + '<div style="' + icon_base + ';background:#ea4335">✉️</div>'
        + '<div><div style="font-weight:700;color:#fff;font-size:0.9rem">Gmail</div>'
        + '<div style="font-size:0.82rem">medlinkai@gmail.com</div></div></a>'

        + '<a href="tel:+84909000000" style="' + row_style + '">'
        + '<div style="' + icon_base + ';background:#0d9488">📱</div>'
        + '<div><div style="font-weight:700;color:#fff;font-size:0.9rem">Điện thoại</div>'
        + '<div style="font-size:0.82rem">+84 909 000 000</div></div></a>'
        + '</div>'

        # Cột 3: giờ hỗ trợ
        + '<div style="' + col_style + '">'
        + '<h3 style="' + h3_style + '">🕐 Hỗ trợ &amp; Giờ làm việc</h3>'
        + '<div style="' + row_style + ';cursor:default">'
        + '<div style="' + icon_base + ';background:#7c3aed">🏢</div>'
        + '<div><div style="font-weight:700;color:#fff;font-size:0.9rem">Địa chỉ</div>'
        + '<div style="font-size:0.82rem">Việt Nam</div></div></div>'
        + '<div style="font-size:0.86rem;color:rgba(255,255,255,0.58);line-height:1.8;margin-top:0.6rem">'
        + '📅 Thứ 2 – Thứ 6: 8:00 – 17:00<br>'
        + '🌐 Hỗ trợ online 24/7 qua Gmail &amp; Facebook<br>'
        + '⚡ Phản hồi trong vòng 24 giờ làm việc</div></div>'

        + '</div></div>'
    )
    st.markdown(html, unsafe_allow_html=True)


def _render_footer() -> None:
    st.markdown(
        """
        <div class="lp-footer">
          © 2026 💊 MedLink AI &nbsp;·&nbsp; FuzzyGCN Drug–Disease Link Prediction
          &nbsp;·&nbsp;
          <a href="mailto:medlinkai@gmail.com">✉️ medlinkai@gmail.com</a>
          &nbsp;·&nbsp;
          <a href="https://www.facebook.com/medlinkai" target="_blank">📘 Facebook</a>
          &nbsp;·&nbsp;
          <a href="#gioi-thieu">↑ Về đầu trang</a>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Modal đăng nhập / đăng ký (st.dialog — hiện ra khi bấm nút navbar)
# ─────────────────────────────────────────────────────────────────────────────

@st.dialog("🔐 Đăng nhập / Đăng ký", width="large")
def _auth_modal(api_base_url: str) -> None:
    """Cửa sổ popup đăng nhập / đăng ký (mở từ navbar)."""
    mode = st.session_state.get("auth_mode", "login")

    t1, t2, t3 = st.columns(3)
    with t1:
        if st.button("🔑 Đăng nhập", use_container_width=True,
                     type="primary" if mode=="login" else "secondary", key="mdl_tab_login"):
            st.session_state["auth_mode"] = "login"
    with t2:
        if st.button("📝 Đăng ký", use_container_width=True,
                     type="primary" if mode=="register" else "secondary", key="mdl_tab_reg"):
            st.session_state["auth_mode"] = "register"
    with t3:
        if st.button("🔓 Quên MK", use_container_width=True,
                     type="primary" if mode=="forgot" else "secondary", key="mdl_tab_forgot"):
            st.session_state["auth_mode"] = "forgot"
            st.session_state.pop("forgot_otp_sent", None)

    st.divider()

    if mode == "login":
        with st.form("mdl_form_login", clear_on_submit=False):
            username = st.text_input("👤 Tên đăng nhập", key="mdl_li_user")
            password = st.text_input("🔒 Mật khẩu", type="password", key="mdl_li_pass")
            submitted = st.form_submit_button("🔑 Đăng nhập", use_container_width=True)
        st.caption("Demo: admin/admin123 · user/user123")
        if submitted:
            if not username or not password:
                st.warning("⚠️ Nhập đầy đủ thông tin.")
            else:
                try:
                    data = ApiClient(api_base_url).login(username=username, password=password)
                    st.session_state.update({"token": data["token"], "username": data["username"], "role": data["role"]})
                    st.rerun()
                except Exception as exc:
                    st.error(f"❌ {exc}")

    elif mode == "register":
        with st.form("mdl_form_register", clear_on_submit=False):
            reg_user  = st.text_input("👤 Tên đăng nhập", key="mdl_reg_user")
            reg_email = st.text_input("📧 Email", key="mdl_reg_email")
            reg_pass  = st.text_input("🔒 Mật khẩu", type="password", key="mdl_reg_pass")
            reg_pass2 = st.text_input("🔒 Xác nhận", type="password", key="mdl_reg_pass2")
            submitted_r = st.form_submit_button("📝 Tạo tài khoản", use_container_width=True)
        if submitted_r:
            if not reg_user or not reg_email or not reg_pass or not reg_pass2:
                st.warning("⚠️ Điền đầy đủ các trường.")
            elif len(reg_user.strip()) < 3:
                st.warning("⚠️ Tên tối thiểu 3 ký tự.")
            elif "@" not in reg_email:
                st.warning("⚠️ Email không hợp lệ.")
            elif len(reg_pass) < 6:
                st.warning("⚠️ Mật khẩu tối thiểu 6 ký tự.")
            elif reg_pass != reg_pass2:
                st.warning("⚠️ Mật khẩu không khớp.")
            else:
                try:
                    ApiClient(api_base_url).register(username=reg_user.strip(), email=reg_email.strip().lower(), password=reg_pass)
                    st.success("✅ Đăng ký thành công! Hãy đăng nhập.")
                    st.session_state["auth_mode"] = "login"; st.rerun()
                except Exception as exc:
                    st.error(f"❌ {exc}")

    elif mode == "forgot":
        _render_forgot_password(api_base_url)

    st.divider()
    st.markdown("**👤 Không muốn đăng nhập?**")
    st.caption("Được sử dụng tra cứu thuốc/bệnh. Không lưu lịch sử, không xuất báo cáo.")
    if st.button("👤 Tiếp tục không cần đăng nhập (Khách)", use_container_width=True, key="mdl_guest_btn"):
        st.session_state["role"] = "guest"
        st.session_state["username"] = "Khách"
        st.session_state["token"] = None  # Guest: không có token, không gửi Authorization header
        st.rerun()


def _render_forgot_password(api_base_url: str) -> None:
    """Form quên mật khẩu — OTP qua email."""
    otp_sent = st.session_state.get("forgot_otp_sent", False)
    st.markdown(
        """
        <div style="background:#fffbeb;border-left:4px solid #f59e0b;border-radius:0 10px 10px 0;
                    padding:0.7rem 1rem;font-size:0.84rem;color:#78350f;margin-bottom:1rem">
          🔑 Nhập thông tin tài khoản để nhận mã OTP đặt lại mật khẩu qua email.
        </div>
        """,
        unsafe_allow_html=True,
    )
    if not otp_sent:
        with st.form("lp_form_forgot1", clear_on_submit=False):
            fp_user  = st.text_input("👤 Tên đăng nhập", placeholder="Tên đăng nhập của bạn", key="lp_fp_user")
            fp_email = st.text_input("📧 Email đã đăng ký", placeholder="example@gmail.com", key="lp_fp_email")
            send_btn = st.form_submit_button("📨 Gửi mã OTP", use_container_width=True)
        st.markdown(
            '<div style="font-size:0.76rem;color:#94a3b8;text-align:center;margin-top:0.5rem">'
            '📬 Mã OTP 6 chữ số sẽ được gửi đến email của bạn — có hiệu lực trong 10 phút.'
            '</div>',
            unsafe_allow_html=True,
        )
        if send_btn:
            if not fp_user or not fp_email:
                st.warning("⚠️ Vui lòng nhập tên đăng nhập và email.")
            else:
                try:
                    client = ApiClient(api_base_url)
                    client.forgot_password(username=fp_user.strip(), email=fp_email.strip().lower())
                    st.session_state["forgot_otp_sent"] = True
                    st.session_state["fp_username"] = fp_user.strip()
                    st.rerun()
                except Exception as exc:
                    st.error(f"❌ {exc}")
    else:
        fp_username = st.session_state.get("fp_username", "")
        with st.form("lp_form_forgot2", clear_on_submit=False):
            otp_val   = st.text_input("🔢 Mã OTP (6 chữ số)", placeholder="123456", max_chars=6, key="lp_fp_otp")
            new_pass  = st.text_input("🔒 Mật khẩu mới", type="password", placeholder="Tối thiểu 6 ký tự", key="lp_fp_np")
            new_pass2 = st.text_input("🔒 Xác nhận mật khẩu mới", type="password", placeholder="Nhập lại", key="lp_fp_np2")
            reset_btn = st.form_submit_button("✅ Đặt lại mật khẩu", use_container_width=True)
        if reset_btn:
            if not otp_val or not new_pass or not new_pass2:
                st.warning("⚠️ Vui lòng điền đầy đủ các trường.")
            elif new_pass != new_pass2:
                st.warning("⚠️ Mật khẩu xác nhận không khớp.")
            elif len(new_pass) < 6:
                st.warning("⚠️ Mật khẩu mới phải có ít nhất 6 ký tự.")
            else:
                try:
                    client = ApiClient(api_base_url)
                    client.reset_password(username=fp_username, otp=otp_val.strip(), new_password=new_pass)
                    st.success("✅ Đặt lại mật khẩu thành công! Hãy đăng nhập lại.")
                    st.session_state.pop("forgot_otp_sent", None)
                    st.session_state.pop("fp_username", None)
                    st.session_state["auth_mode"] = "login"
                    st.rerun()
                except Exception as exc:
                    st.error(f"❌ {exc}")


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────

def render_landing(api_base_url: str) -> None:
    """Render toàn bộ trang chủ public (chưa đăng nhập)."""
    bg_css = get_bg_css()

    # CSS + animations
    st.markdown(_landing_css(bg_css), unsafe_allow_html=True)

    # Navbar cố định
    _render_navbar()

    # Hero section — title + stats
    _render_hero_centered(SYSTEM_STATS)

    # CTA buttons trong hero — Streamlit native, nằm trong khung hero
    st.markdown(
        '<div style="background:linear-gradient(180deg,rgba(15,23,42,0.72) 0%,rgba(15,23,42,0) 100%);'
        'padding:0.2rem 2rem 2.5rem;margin-top:-4px">',
        unsafe_allow_html=True,
    )
    _, ca, cb, _ = st.columns([2, 2.5, 2.5, 2])
    with ca:
        if st.button("🚀 Bắt đầu miễn phí", key="hero_cta_reg", type="primary", use_container_width=True):
            st.session_state["auth_mode"] = "register"
            _auth_modal(api_base_url)
    with cb:
        if st.button("👤 Dùng thử (Khách)", key="hero_cta_guest", use_container_width=True):
            st.session_state["role"] = "guest"
            st.session_state["username"] = "Khách"
            st.session_state["token"] = None  # Guest: không có token, không gửi Authorization header
            st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)

    # Tính năng
    _render_features(FEATURES)

    # Hướng dẫn sử dụng
    _render_how_to_use(HOW_TO_USE)

    # CTA banner
    _render_cta_banner()

    # Góp ý
    _render_feedback_section()

    # Liên hệ (FB, Gmail, SĐT)
    _render_contact_section()

    # Footer
    _render_footer()

    # Re-trigger scroll observer
    st.markdown(_retrigger_js(), unsafe_allow_html=True)

