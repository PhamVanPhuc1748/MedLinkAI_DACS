from __future__ import annotations

import streamlit as st


def _get_theme_vars(is_dark: bool) -> str:
    if is_dark:
        return """
        :root {
          --bg:        #0f172a;
          --surface:   #1e293b;
          --border:    #334155;
          --text:      #e2e8f0;
          --muted:     #94a3b8;
          --primary:   #2dd4bf;
          --primary-2: #60a5fa;
          --danger:    #f87171;
          --known-bg:  #14532d;
          --known-fg:  #86efac;
          --pred-bg:   #1e3a5f;
          --pred-fg:   #93c5fd;
          --radius:    12px;
          --shadow:    0 2px 12px rgba(0,0,0,0.3);
          --shadow-lg: 0 8px 32px rgba(0,0,0,0.4);
          --input-bg:  #1e293b;
          --table-head-bg: #1e293b;
          --table-row-hover: #263347;
          --table-row-border: #2d3f55;
          --score-bar-bg: #334155;
          --info-bg:   #1e3a5f;
          --info-fg:   #93c5fd;
          --info-border: #3b82f6;
          --warn-bg:   #422006;
          --warn-fg:   #fcd34d;
          --warn-border: #f59e0b;
        }
        """
    else:
        return """
        :root {
          --bg:        #f0f4f9;
          --surface:   #ffffff;
          --border:    #e2e8f0;
          --text:      #1a202c;
          --muted:     #64748b;
          --primary:   #0d9488;
          --primary-2: #1e40af;
          --danger:    #dc2626;
          --known-bg:  #dcfce7;
          --known-fg:  #15803d;
          --pred-bg:   #eff6ff;
          --pred-fg:   #1d4ed8;
          --radius:    12px;
          --shadow:    0 2px 12px rgba(0,0,0,0.07);
          --shadow-lg: 0 8px 32px rgba(0,0,0,0.10);
          --input-bg:  #ffffff;
          --table-head-bg: #f8fafc;
          --table-row-hover: #f8fafc;
          --table-row-border: #f1f5f9;
          --score-bar-bg: #e2e8f0;
          --info-bg:   #eff6ff;
          --info-fg:   #1e40af;
          --info-border: #3b82f6;
          --warn-bg:   #fffbeb;
          --warn-fg:   #92400e;
          --warn-border: #f59e0b;
        }
        """


def apply_theme() -> None:
    st.set_page_config(
        page_title="MedLink AI — Drug·Disease Intelligence",
        page_icon="💊",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    is_dark = st.session_state.get("dark_mode", False)
    theme_vars = _get_theme_vars(is_dark)

    dark_widget_overrides = ""
    light_widget_overrides = ""
    if is_dark:
        dark_widget_overrides = """
        /* ── Dark mode: Streamlit native widget overrides ── */
        .stApp, .stApp > header, .main .block-container {
          background-color: #0f172a !important;
          color: #e2e8f0 !important;
        }
        section[data-testid="stSidebar"] {
          background-color: #1e293b !important;
        }
        .stTextInput > div > div > input,
        .stTextArea textarea,
        .stSelectbox > div > div,
        .stNumberInput input {
          background-color: #1e293b !important;
          color: #e2e8f0 !important;
          border-color: #334155 !important;
        }
        .stSelectbox > div > div > div,
        .stSelectbox [data-baseweb="select"] div {
          background-color: #1e293b !important;
          color: #e2e8f0 !important;
        }
        div[data-baseweb="popover"] ul,
        div[data-baseweb="popover"] li {
          background-color: #1e293b !important;
          color: #e2e8f0 !important;
        }
        div[data-baseweb="menu"] {
          background-color: #1e293b !important;
          border-color: #334155 !important;
        }
        div[data-baseweb="option"]:hover {
          background-color: #263347 !important;
        }
        p, span, label, div, h1, h2, h3, h4, h5, h6, li {
          color: #e2e8f0;
        }
        .stMarkdown, .stMarkdown p, .stMarkdown span {
          color: #e2e8f0 !important;
        }
        [data-testid="stMetric"] label,
        [data-testid="stMetric"] div {
          color: #e2e8f0 !important;
        }
        .stSlider [data-testid="stSlider"] > div { background: #334155; }
        .stDataFrame, .stDataFrame table {
          background-color: #1e293b !important;
          color: #e2e8f0 !important;
        }
        .stDataFrame thead th {
          background-color: #263347 !important;
          color: #e2e8f0 !important;
        }
        .stDataFrame tbody tr:hover { background-color: #263347 !important; }
        .stTabs [data-baseweb="tab-panel"] { background: transparent !important; }
        .stForm { background-color: #1e293b !important; border-color: #334155 !important; }
        code, pre { background-color: #263347 !important; color: #93c5fd !important; }
        """
    else:
        light_widget_overrides = """
        /* ── Light mode: Streamlit native widget overrides ── */
        .stApp, .stApp > header, .main .block-container {
          background-color: #f0f4f9 !important;
          color: #1a202c !important;
        }
        section[data-testid="stSidebar"] {
          background-color: #ffffff !important;
          color: #1a202c !important;
        }
        .stTextInput > div > div > input,
        .stTextArea textarea,
        .stSelectbox > div > div,
        .stNumberInput input {
          background-color: #ffffff !important;
          color: #1a202c !important;
          border-color: #e2e8f0 !important;
        }
        .stSelectbox > div > div > div,
        .stSelectbox [data-baseweb="select"] div {
          background-color: #ffffff !important;
          color: #1a202c !important;
        }
        div[data-baseweb="popover"] ul,
        div[data-baseweb="popover"] li {
          background-color: #ffffff !important;
          color: #1a202c !important;
        }
        div[data-baseweb="menu"] {
          background-color: #ffffff !important;
          border-color: #e2e8f0 !important;
        }
        div[data-baseweb="option"]:hover {
          background-color: #f8fafc !important;
        }
        p, span, label, div, h1, h2, h3, h4, h5, h6, li {
          color: #1a202c;
        }
        /* Chỉ override Streamlit native markdown text — KHÔNG dùng !important
           để các class CSS cụ thể hơn (hero-banner, lp-hero, v.v.) vẫn giữ màu trắng */
        .stMarkdown, .stMarkdown p, .stMarkdown span {
          color: #1a202c;
        }
        /* Restore white text cho các section có nền tối (hero banner, landing hero,
           CTA banner, footer, contact) — dùng !important để thắng theme */
        .hero-banner, .hero-banner *,
        .hero-banner h1, .hero-banner p, .hero-banner span,
        .hero-chip, .hero-stat,
        .lp-hero-title, .lp-hero-title span, .lp-hero-desc,
        .lp-hero-badge, .lp-hero-stat, .lp-hero-stat-num, .lp-hero-stat-label,
        .lp-cta-banner h2, .lp-cta-banner p,
        .lp-contact-section, .lp-contact-section *,
        .lp-footer, .lp-footer a,
        .lp-navbar .lp-logo, .lp-navbar .lp-logo span,
        .lp-nav-link {
          color: inherit !important;
        }
        .hero-banner h1, .hero-chip, .hero-stat,
        .lp-hero-badge, .lp-hero-stat { color: #fff !important; }
        .lp-cta-banner h2 { color: #fff !important; }
        .lp-cta-banner p { color: rgba(255,255,255,0.85) !important; }
        .lp-hero-title { color: #fff !important; }
        .lp-hero-title span { color: #2dd4bf !important; }
        .lp-hero-desc { color: rgba(255,255,255,0.9) !important; }
        .lp-hero-stat-num { color: #2dd4bf !important; }
        .lp-hero-stat-label { color: rgba(255,255,255,0.72) !important; }
        .lp-logo { color: #2dd4bf !important; }
        .lp-logo span { color: #fff !important; }
        .lp-nav-link { color: rgba(255,255,255,0.75) !important; }
        .lp-contact-item { color: rgba(255,255,255,0.72) !important; }
        .lp-footer { color: rgba(255,255,255,0.45) !important; }
        .lp-footer a { color: #2dd4bf !important; }
        [data-testid="stMetric"] label,
        [data-testid="stMetric"] div {
          color: #1a202c !important;
        }
        [data-testid="stMetricLabel"] { color: #64748b !important; }
        [data-testid="stMetricValue"] { color: #1a202c !important; }
        .stDataFrame, .stDataFrame table {
          background-color: #ffffff !important;
          color: #1a202c !important;
        }
        .stDataFrame thead th {
          background-color: #f8fafc !important;
          color: #1a202c !important;
        }
        .stDataFrame tbody tr:hover { background-color: #f8fafc !important; }
        .stTabs [data-baseweb="tab-panel"] { background: transparent !important; }
        .stForm { background-color: #ffffff !important; border-color: #e2e8f0 !important; }
        code, pre { background-color: #f1f5f9 !important; color: #1e40af !important; }
        /* Radio / checkbox text in sidebar */
        .stRadio label span, .stCheckbox label span {
          color: #1a202c !important;
        }
        /* Info/warning boxes native Streamlit */
        [data-testid="stNotification"] {
          background-color: #eff6ff !important;
          color: #1e40af !important;
        }
        /* Muted section headers in sidebar */
        section[data-testid="stSidebar"] h3,
        section[data-testid="stSidebar"] .stMarkdown h3 {
          color: #64748b !important;
        }
        /* Ensure sidebar nav text visible */
        section[data-testid="stSidebar"] .stRadio label,
        section[data-testid="stSidebar"] p,
        section[data-testid="stSidebar"] span {
          color: #1a202c !important;
        }
        """

    st.markdown(
        f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

        {theme_vars}

        html, body, [class*="css"] {{
          font-family: 'Inter', sans-serif;
          color: var(--text);
        }}

        .stApp {{
          background: var(--bg);
        }}

        /* ── Sidebar ── */
        section[data-testid="stSidebar"] {{
          background: var(--surface);
          border-right: 1px solid var(--border);
        }}
        section[data-testid="stSidebar"] .stMarkdown h3 {{
          font-size: 0.78rem;
          font-weight: 700;
          letter-spacing: 0.08em;
          text-transform: uppercase;
          color: var(--muted);
          margin: 1.2rem 0 0.4rem 0;
        }}

        /* ── Theme toggle button ── */
        .theme-toggle-btn {{
          display: inline-flex;
          align-items: center;
          gap: 0.4rem;
          background: var(--surface);
          border: 1px solid var(--border);
          border-radius: 999px;
          padding: 0.3rem 0.9rem;
          cursor: pointer;
          font-size: 0.82rem;
          font-weight: 600;
          color: var(--text);
          transition: all 0.2s ease;
          box-shadow: var(--shadow);
        }}
        .theme-toggle-btn:hover {{
          border-color: var(--primary);
          color: var(--primary);
        }}

        /* ── Hero banner ── */
        .hero-banner {{
          background: linear-gradient(135deg, #0d9488 0%, #1e40af 100%);
          border-radius: var(--radius);
          padding: 1.4rem 1.8rem;
          margin-bottom: 1.2rem;
          color: #fff;
          box-shadow: var(--shadow-lg);
          position: relative;
          overflow: hidden;
        }}
        .hero-banner::before {{
          content: '';
          position: absolute;
          top: -30%;
          right: -5%;
          width: 260px;
          height: 260px;
          background: rgba(255,255,255,0.06);
          border-radius: 50%;
        }}
        .hero-banner h1 {{
          margin: 0 0 0.25rem 0;
          font-size: 1.65rem;
          font-weight: 800;
          letter-spacing: -0.03em;
          color: #fff;
        }}
        .hero-banner p {{
          margin: 0;
          opacity: 0.88;
          font-size: 0.93rem;
          color: #fff;
        }}
        .hero-chip {{
          display: inline-block;
          background: rgba(255,255,255,0.22);
          border: 1px solid rgba(255,255,255,0.35);
          color: #fff;
          border-radius: 999px;
          padding: 0.18rem 0.7rem;
          font-size: 0.72rem;
          font-weight: 700;
          letter-spacing: 0.04em;
          text-transform: uppercase;
          margin-bottom: 0.5rem;
        }}
        .hero-stats {{
          display: flex;
          gap: 1.2rem;
          margin-top: 0.8rem;
        }}
        .hero-stat {{
          font-size: 0.78rem;
          color: rgba(255,255,255,0.85);
          display: flex;
          align-items: center;
          gap: 0.3rem;
        }}

        /* ── Cards ── */
        .card {{
          background: var(--surface);
          border: 1px solid var(--border);
          border-radius: var(--radius);
          padding: 1.2rem 1.4rem 1.3rem 1.4rem;
          margin-bottom: 1rem;
          box-shadow: var(--shadow);
        }}
        .card-title {{
          font-size: 1rem;
          font-weight: 700;
          color: var(--text);
          margin: 0 0 0.8rem 0;
          display: flex;
          align-items: center;
          gap: 0.4rem;
        }}

        /* ── Buttons — animated ── */
        .stButton > button {{
          border-radius: 8px !important;
          border: none !important;
          background: linear-gradient(90deg, var(--primary), var(--primary-2)) !important;
          color: #ffffff !important;
          font-weight: 600 !important;
          font-size: 0.9rem !important;
          padding: 0.5rem 1.2rem !important;
          transition: transform 0.18s ease, box-shadow 0.18s ease, opacity 0.18s ease !important;
          position: relative !important;
          overflow: hidden !important;
        }}
        /* Shimmer sweep on hover */
        .stButton > button::after {{
          content: '' !important;
          position: absolute !important;
          top: 0 !important; left: -100% !important;
          width: 60% !important; height: 100% !important;
          background: linear-gradient(120deg, transparent 30%, rgba(255,255,255,0.22) 50%, transparent 70%) !important;
          transition: left 0.45s ease !important;
        }}
        .stButton > button:hover::after {{
          left: 160% !important;
        }}
        .stButton > button:hover {{
          transform: translateY(-2px) scale(1.02) !important;
          box-shadow: 0 6px 22px rgba(13,148,136,0.35) !important;
          opacity: 1 !important;
        }}
        .stButton > button:active {{
          transform: translateY(0) scale(0.98) !important;
          box-shadow: 0 2px 8px rgba(13,148,136,0.2) !important;
        }}
        /* Pulse effect trên nút primary */
        .stButton > button[kind="primary"] {{
          animation: btn-pulse 3s ease-in-out infinite !important;
        }}
        @keyframes btn-pulse {{
          0%,100% {{ box-shadow: 0 0 0 0 rgba(13,148,136,0); }}
          50% {{ box-shadow: 0 0 0 5px rgba(13,148,136,0.18); }}
        }}

        /* ── Form submit button — animated ── */
        .stFormSubmitButton > button {{
          border-radius: 8px !important;
          border: none !important;
          background: linear-gradient(90deg, var(--primary), var(--primary-2)) !important;
          color: #ffffff !important;
          font-weight: 700 !important;
          font-size: 0.95rem !important;
          width: 100% !important;
          padding: 0.6rem 1rem !important;
          transition: transform 0.18s ease, box-shadow 0.18s ease !important;
          position: relative !important;
          overflow: hidden !important;
        }}
        .stFormSubmitButton > button:hover {{
          transform: translateY(-2px) !important;
          box-shadow: 0 6px 24px rgba(13,148,136,0.4) !important;
        }}
        .stFormSubmitButton > button:active {{
          transform: translateY(0) !important;
        }}

        /* ── Input fields ── */
        .stTextInput > div > div > input,
        .stSelectbox > div > div {{
          border-radius: 8px !important;
          border: 1px solid var(--border) !important;
          background-color: var(--input-bg) !important;
          color: var(--text) !important;
        }}
        .stTextInput label,
        .stSelectbox label,
        .stSlider label,
        .stNumberInput label,
        .stMultiSelect label,
        .stCheckbox label {{
          color: var(--text) !important;
          font-weight: 500 !important;
        }}

        /* ── Tabs ── */
        .stTabs [data-baseweb="tab-list"] {{
          gap: 0.3rem;
          background: transparent;
          border-bottom: 2px solid var(--border);
          padding-bottom: 0;
        }}
        .stTabs [data-baseweb="tab"] {{
          border-radius: 8px 8px 0 0 !important;
          background: transparent !important;
          border: 1px solid transparent !important;
          color: var(--muted) !important;
          font-weight: 600 !important;
          font-size: 0.88rem !important;
          padding: 0.45rem 1rem !important;
        }}
        .stTabs [aria-selected="true"] {{
          background: var(--surface) !important;
          border-color: var(--border) !important;
          border-bottom-color: var(--surface) !important;
          color: var(--primary) !important;
        }}

        /* ── Metric cards ── */
        [data-testid="stMetric"] {{
          background: var(--surface);
          border: 1px solid var(--border);
          border-radius: var(--radius);
          padding: 0.9rem 1rem;
          box-shadow: var(--shadow);
        }}
        [data-testid="stMetricLabel"] {{
          color: var(--muted) !important;
        }}
        [data-testid="stMetricValue"] {{
          color: var(--text) !important;
        }}

        /* ── Known / Predicted badges ── */
        .badge-known {{
          display: inline-block;
          background: var(--known-bg);
          color: var(--known-fg);
          border: 1px solid var(--known-fg);
          border-radius: 999px;
          padding: 0.15rem 0.65rem;
          font-size: 0.72rem;
          font-weight: 700;
          letter-spacing: 0.03em;
        }}
        .badge-pred {{
          display: inline-block;
          background: var(--pred-bg);
          color: var(--pred-fg);
          border: 1px solid var(--pred-fg);
          border-radius: 999px;
          padding: 0.15rem 0.65rem;
          font-size: 0.72rem;
          font-weight: 700;
          letter-spacing: 0.03em;
        }}

        /* ── Result table ── */
        .result-table {{ width: 100%; border-collapse: collapse; font-size: 0.88rem; }}
        .result-table thead tr {{ background: var(--table-head-bg); }}
        .result-table th {{
          text-align: left;
          padding: 0.5rem 0.7rem;
          font-weight: 700;
          color: var(--muted);
          font-size: 0.74rem;
          letter-spacing: 0.05em;
          text-transform: uppercase;
          border-bottom: 1px solid var(--border);
        }}
        .result-table td {{
          padding: 0.5rem 0.7rem;
          border-bottom: 1px solid var(--table-row-border);
          color: var(--text);
        }}
        .result-table tr:last-child td {{ border-bottom: none; }}
        .result-table tr:hover td {{ background: var(--table-row-hover); }}
        .score-bar-wrap {{ display: flex; align-items: center; gap: 0.5rem; }}
        .score-bar-bg {{ flex: 1; background: var(--score-bar-bg); border-radius: 4px; height: 6px; min-width: 60px; }}
        .score-bar-fill {{ height: 6px; border-radius: 4px; background: linear-gradient(90deg, var(--primary), var(--primary-2)); }}
        .score-val {{ font-weight: 700; font-size: 0.82rem; color: var(--primary-2); white-space: nowrap; }}

        /* ── Alert / info boxes ── */
        .info-box {{
          background: var(--info-bg);
          border-left: 3px solid var(--info-border);
          border-radius: 0 8px 8px 0;
          padding: 0.6rem 0.9rem;
          font-size: 0.85rem;
          color: var(--info-fg);
          margin: 0.5rem 0;
        }}
        .warn-box {{
          background: var(--warn-bg);
          border-left: 3px solid var(--warn-border);
          border-radius: 0 8px 8px 0;
          padding: 0.6rem 0.9rem;
          font-size: 0.85rem;
          color: var(--warn-fg);
          margin: 0.5rem 0;
        }}

        /* ── Drug-Disease connector ── */
        .connector-col {{
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          padding-top: 2.5rem;
          gap: 0.6rem;
        }}
        .connector-arrow {{
          width: 40px;
          height: 8px;
          background: linear-gradient(90deg, var(--primary), var(--primary-2));
          border-radius: 4px;
          position: relative;
          animation: pulse-arrow 1.8s ease-in-out infinite;
          opacity: 0.85;
        }}
        .connector-arrow:nth-child(2) {{ animation-delay: 0.3s; }}
        .connector-arrow:nth-child(3) {{ animation-delay: 0.6s; }}
        .connector-arrow::after {{
          content: '';
          position: absolute;
          right: -6px;
          top: -4px;
          border-left: 10px solid var(--primary-2);
          border-top: 8px solid transparent;
          border-bottom: 8px solid transparent;
        }}
        @keyframes pulse-arrow {{
          0%, 100% {{ opacity: 0.5; transform: scaleX(0.9); }}
          50% {{ opacity: 1.0; transform: scaleX(1.05); }}
        }}
        .connector-label {{
          font-size: 0.65rem;
          font-weight: 700;
          color: var(--primary);
          text-transform: uppercase;
          letter-spacing: 0.06em;
          text-align: center;
          margin-top: 0.3rem;
        }}

        /* ── Drug/Disease panel headers ── */
        .panel-header {{
          display: flex;
          align-items: center;
          gap: 0.5rem;
          padding: 0.6rem 0.9rem;
          border-radius: 8px 8px 0 0;
          font-weight: 700;
          font-size: 0.92rem;
          margin-bottom: 0;
        }}
        .panel-header-drug {{
          background: linear-gradient(90deg, #0d9488 0%, #0f766e 100%);
          color: #fff;
        }}
        .panel-header-disease {{
          background: linear-gradient(90deg, #1e40af 0%, #1d4ed8 100%);
          color: #fff;
        }}
        .panel-body {{
          border: 1px solid var(--border);
          border-top: none;
          border-radius: 0 0 8px 8px;
          padding: 0.8rem;
          background: var(--surface);
        }}

        /* ── Drug info card ── */
        .drug-info-card {{
          background: var(--surface);
          border: 1px solid var(--border);
          border-radius: var(--radius);
          padding: 0.9rem 1rem;
          margin-bottom: 0.6rem;
        }}
        .drug-info-label {{
          font-size: 0.7rem;
          font-weight: 700;
          text-transform: uppercase;
          letter-spacing: 0.06em;
          color: var(--muted);
          margin-bottom: 0.15rem;
        }}
        .drug-info-value {{
          font-size: 0.88rem;
          font-weight: 600;
          color: var(--text);
          word-break: break-all;
        }}

        /* ── Molecule section ── */
        .mol-section-title {{
          font-size: 0.82rem;
          font-weight: 700;
          text-transform: uppercase;
          letter-spacing: 0.06em;
          color: var(--muted);
          margin-bottom: 0.5rem;
          display: flex;
          align-items: center;
          gap: 0.3rem;
        }}

        /* ── Sidebar navigation tabs ── */
        .sidebar-nav-item {{
          display: flex;
          align-items: center;
          gap: 0.65rem;
          padding: 0.6rem 0.9rem;
          border-radius: 10px;
          font-size: 0.9rem;
          font-weight: 600;
          color: var(--muted);
          cursor: pointer;
          transition: all 0.2s ease;
          margin-bottom: 0.2rem;
          border: 1px solid transparent;
          text-decoration: none;
          position: relative;
          overflow: hidden;
        }}
        .sidebar-nav-item::before {{
          content: '';
          position: absolute;
          left: 0; top: 0; bottom: 0;
          width: 3px;
          background: var(--primary);
          border-radius: 0 3px 3px 0;
          opacity: 0;
          transition: opacity 0.2s ease;
        }}
        .sidebar-nav-item:hover {{
          background: var(--pred-bg);
          color: var(--text);
          border-color: var(--border);
        }}
        .sidebar-nav-item.active {{
          background: linear-gradient(90deg, rgba(13,148,136,0.13), rgba(30,64,175,0.08));
          color: var(--primary);
          border-color: var(--primary);
        }}
        .sidebar-nav-item.active::before {{
          opacity: 1;
        }}
        .sidebar-nav-item .nav-icon {{
          font-size: 1.1rem;
          flex-shrink: 0;
        }}
        .sidebar-section-label {{
          font-size: 0.7rem;
          font-weight: 700;
          color: var(--muted);
          text-transform: uppercase;
          letter-spacing: 0.08em;
          padding: 0.8rem 0.9rem 0.3rem 0.9rem;
        }}

        /* ── Sidebar user badge animation ── */
        .sidebar-user-badge {{
          background: var(--known-bg);
          border: 1px solid var(--known-fg);
          border-radius: 10px;
          padding: 0.6rem 0.9rem;
          margin-bottom: 0.8rem;
          animation: badge-in 0.4s ease both;
        }}
        @keyframes badge-in {{
          from {{ opacity:0; transform: scale(0.95); }}
          to {{ opacity:1; transform: scale(1); }}
        }}

        /* ── Page transition fade ── */
        .main .block-container {{
          animation: page-fade 0.35s ease;
        }}
        @keyframes page-fade {{
          from {{ opacity: 0; transform: translateY(8px); }}
          to {{ opacity: 1; transform: translateY(0); }}
        }}

        {dark_widget_overrides}
        {light_widget_overrides}
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_hero(role: str | None) -> None:
    chip = "Admin Console" if role == "admin" else ("Workspace" if role else "Welcome")
    desc = (
        "Quản lý hệ thống, dữ liệu và theo dõi toàn bộ prediction logs."
        if role == "admin"
        else "Nhập tên Thuốc hoặc Bệnh để AI dự đoán liên kết và kiểm tra dữ liệu thực tế."
    )
    st.markdown(
        f"""
        <div class="hero-banner">
          <span class="hero-chip">🧬 {chip}</span>
          <h1>💊 MedLink AI</h1>
          <p>{desc}</p>
          <div class="hero-stats">
            <span class="hero-stat">🔬 FuzzyGCN Model</span>
            <span class="hero-stat">📊 Drug–Disease–Protein Graph</span>
            <span class="hero-stat">⚡ Real-time Inference</span>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
