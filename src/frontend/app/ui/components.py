from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st


def _translate_omim(name: str) -> str:
    """Dịch mã OMIM (D102100) sang tên Tiếng Việt để hiển thị trong bảng kết quả."""
    n = str(name).strip()
    if n.upper().startswith("D") and n[1:].isdigit() and 5 <= len(n) <= 8:
        try:
            _src_root = Path(__file__).resolve().parents[4]  # src/
            if str(_src_root) not in sys.path:
                sys.path.insert(0, str(_src_root))
            from data.omim_viet_dict import get_viet_name
            viet = get_viet_name(n.upper())
            if viet != n:
                return f"{viet} ({n})"
        except Exception:
            pass
    return n


def card_open(title: str, icon: str = "") -> None:
    icon_html = f"<span style='margin-right:0.35rem'>{icon}</span>" if icon else ""
    st.markdown(
        f'<div class="card"><div class="card-title">{icon_html}{title}</div>',
        unsafe_allow_html=True,
    )


def card_close() -> None:
    st.markdown("</div>", unsafe_allow_html=True)


def show_result_table(results: list[dict], entity_label: str = "Tên") -> None:
    if not results:
        st.markdown(
            '<div class="info-box">Không có kết quả phù hợp với điều kiện hiện tại.</div>',
            unsafe_allow_html=True,
        )
        return

    known_count = sum(1 for r in results if r.get("known", False))
    pred_count = len(results) - known_count

    st.markdown(
        f"""
        <div style="display:flex;gap:0.8rem;margin-bottom:1rem">
          <div style="flex:1;background:var(--surface);border:1px solid var(--border);border-radius:10px;
                      padding:0.8rem 1rem;box-shadow:0 2px 8px rgba(0,0,0,0.06)">
            <div style="font-size:0.73rem;font-weight:700;color:var(--muted);
                        text-transform:uppercase;letter-spacing:0.05em;margin-bottom:0.25rem">
              📊 Tổng kết quả
            </div>
            <div style="font-size:1.8rem;font-weight:800;color:var(--text);line-height:1">{len(results)}</div>
          </div>
          <div style="flex:1;background:var(--known-bg);border:1px solid var(--known-fg);border-radius:10px;
                      padding:0.8rem 1rem;box-shadow:0 2px 8px rgba(0,0,0,0.06)">
            <div style="font-size:0.73rem;font-weight:700;color:var(--known-fg);
                        text-transform:uppercase;letter-spacing:0.05em;margin-bottom:0.25rem">
              ✅ Liên kết đã biết
            </div>
            <div style="font-size:1.8rem;font-weight:800;color:var(--known-fg);line-height:1">{known_count}</div>
          </div>
          <div style="flex:1;background:var(--pred-bg);border:1px solid var(--pred-fg);border-radius:10px;
                      padding:0.8rem 1rem;box-shadow:0 2px 8px rgba(0,0,0,0.06)">
            <div style="font-size:0.73rem;font-weight:700;color:var(--pred-fg);
                        text-transform:uppercase;letter-spacing:0.05em;margin-bottom:0.25rem">
              🔬 AI dự đoán mới
            </div>
            <div style="font-size:1.8rem;font-weight:800;color:var(--pred-fg);line-height:1">{pred_count}</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("<br>", unsafe_allow_html=True)

    rows_html = ""
    for i, r in enumerate(results, 1):
        score = float(r.get("score", 0.0))
        score_pct = score * 100
        bar_w = max(2, int(score_pct))
        is_known = bool(r.get("known", False))
        badge = (
            '<span class="badge-known">✅ Đã biết</span>'
            if is_known
            else '<span class="badge-pred">🔬 Dự đoán</span>'
        )
        display_name = _translate_omim(r.get("name", ""))
        rows_html += f"""
        <tr>
          <td style="color:var(--muted);font-size:0.8rem">{i}</td>
          <td><strong>{display_name}</strong></td>
          <td>{badge}</td>
          <td>
            <div class="score-bar-wrap">
              <div class="score-bar-bg">
                <div class="score-bar-fill" style="width:{bar_w}%"></div>
              </div>
              <span class="score-val">{score_pct:.2f}%</span>
            </div>
          </td>
        </tr>"""

    st.markdown(
        f"""
        <table class="result-table">
          <thead>
            <tr>
              <th>#</th>
              <th>{entity_label}</th>
              <th>Trạng thái</th>
              <th>Điểm dự đoán</th>
            </tr>
          </thead>
          <tbody>{rows_html}</tbody>
        </table>
        """,
        unsafe_allow_html=True,
    )


def _render_group_table(group: list[dict], entity_label: str) -> None:
    """Render một nhóm kết quả (điều trị hoặc cảnh báo) vào bảng HTML."""
    if not group:
        st.info("Không tìm thấy kết quả thuộc nhóm này.")
        return

    rows_html = ""
    for i, r in enumerate(group, 1):
        score = float(r.get("score", 0.0))
        score_pct = score * 100
        bar_w = max(2, int(score_pct))
        is_known = bool(r.get("known", False))
        badge = (
            '<span class="badge-known">✅ Đã biết</span>'
            if is_known
            else '<span class="badge-pred">🔬 Dự đoán</span>'
        )
        display_name = _translate_omim(r.get("name", ""))
        rows_html += f"""
        <tr>
          <td style="color:var(--muted);font-size:0.8rem">{i}</td>
          <td><strong>{display_name}</strong></td>
          <td>{badge}</td>
          <td>
            <div class="score-bar-wrap">
              <div class="score-bar-bg">
                <div class="score-bar-fill" style="width:{bar_w}%"></div>
              </div>
              <span class="score-val">{score_pct:.2f}%</span>
            </div>
          </td>
        </tr>"""

    st.markdown(
        f"""
        <table class="result-table">
          <thead>
            <tr>
              <th>#</th>
              <th>{entity_label}</th>
              <th>Trạng thái</th>
              <th>Điểm dự đoán</th>
            </tr>
          </thead>
          <tbody>{rows_html}</tbody>
        </table>
        """,
        unsafe_allow_html=True,
    )


def show_split_result_table(results: list[dict], entity_label: str = "Tên") -> None:
    """
    Hiển thị kết quả dự đoán dưới dạng 2 cột song song:
    - Cột trái  (✅ Nhóm Điều Trị)  : known=True  — liên kết đã xác nhận trong dataset
    - Cột phải (⚠️ Nguy Cơ / Cảnh Báo): known=False — AI dự đoán mới, chưa kiểm chứng
    """
    if not results:
        st.markdown(
            '<div class="info-box">Không có kết quả phù hợp với điều kiện hiện tại.</div>',
            unsafe_allow_html=True,
        )
        return

    # ── Phân loại ──────────────────────────────────────────────────────
    df_tri_benh = [r for r in results if r.get("known", False)]
    df_canh_bao = [r for r in results if not r.get("known", False)]

    known_count = len(df_tri_benh)
    pred_count = len(df_canh_bao)

    # ── Metric row tổng quan ───────────────────────────────────────────
    st.markdown(
        f"""
        <div style="display:flex;gap:0.8rem;margin-bottom:1rem">
          <div style="flex:1;background:var(--surface);border:1px solid var(--border);border-radius:10px;
                      padding:0.8rem 1rem;box-shadow:0 2px 8px rgba(0,0,0,0.06)">
            <div style="font-size:0.73rem;font-weight:700;color:var(--muted);
                        text-transform:uppercase;letter-spacing:0.05em;margin-bottom:0.25rem">
              📊 Tổng kết quả
            </div>
            <div style="font-size:1.8rem;font-weight:800;color:var(--text);line-height:1">{len(results)}</div>
          </div>
          <div style="flex:1;background:var(--known-bg);border:1px solid var(--known-fg);border-radius:10px;
                      padding:0.8rem 1rem;box-shadow:0 2px 8px rgba(0,0,0,0.06)">
            <div style="font-size:0.73rem;font-weight:700;color:var(--known-fg);
                        text-transform:uppercase;letter-spacing:0.05em;margin-bottom:0.25rem">
              ✅ Nhóm Điều Trị
            </div>
            <div style="font-size:1.8rem;font-weight:800;color:var(--known-fg);line-height:1">{known_count}</div>
          </div>
          <div style="flex:1;background:var(--warn-bg);border:1px solid var(--warn-border);border-radius:10px;
                      padding:0.8rem 1rem;box-shadow:0 2px 8px rgba(0,0,0,0.06)">
            <div style="font-size:0.73rem;font-weight:700;color:var(--warn-fg);
                        text-transform:uppercase;letter-spacing:0.05em;margin-bottom:0.25rem">
              ⚠️ Ngụy Cơ / Cần Kiểm Chứng
            </div>
            <div style="font-size:1.8rem;font-weight:800;color:var(--warn-fg);line-height:1">{pred_count}</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── 2 cột song song ────────────────────────────────────────────────
    col1, col2 = st.columns(2)

    with col1:
        st.markdown('<h3 style="color:var(--known-fg);margin:0 0 0.2rem 0">✅ Nhóm Thuốc Điều Trị</h3>', unsafe_allow_html=True)
        st.caption(f"{known_count} liên kết đã được xác nhận trong dữ liệu huấn luyện")
        _render_group_table(df_tri_benh, entity_label)

    with col2:
        st.markdown('<h3 style="color:var(--warn-fg);margin:0 0 0.2rem 0">⚠️ Nhóm Nguy Cơ / Tác Dụng Phụ</h3>', unsafe_allow_html=True)
        st.caption(f"{pred_count} kết quả do AI dự đoán — cần kiểm chứng lâm sàng")
        _render_group_table(df_canh_bao, entity_label)

    # ── Chú thích cuối ─────────────────────────────────────────────────
    st.markdown(
        '<div class="info-box" style="margin-top:0.8rem">'
        '<strong>Hướng dẫn đọc kết quả:</strong> '
        '✅ <strong>Nhóm Điều Trị</strong> — liên kết có trong dataset, đã được xác nhận qua nghiên cứu. '
        '⚠️ <strong>Nhóm Nguy Cơ</strong> — AI suy luận từ cấu trúc đồ thị, '
        '<em>không phải khuyến cáo y tế</em>, chỉ dùng để nghiên cứu thêm.'
        '</div>',
        unsafe_allow_html=True,
    )


def show_history_table(rows: list[dict]) -> None:
    if not rows:
        st.markdown(
            '<div class="info-box">Chưa có lịch sử tra cứu.</div>',
            unsafe_allow_html=True,
        )
        return
    df = pd.DataFrame(rows)
    if "score" in df.columns:
        df["score"] = pd.to_numeric(df["score"], errors="coerce")
        df["score (%)"] = (df["score"] * 100).map(lambda x: f"{x:.2f}%")
    if "direction" in df.columns:
        df["direction"] = df["direction"].map(
            {"drug_to_disease": "💊→🦠 Thuốc→Bệnh", "disease_to_drug": "🦠→💊 Bệnh→Thuốc"}
        ).fillna(df["direction"])
    if "known" in df.columns:
        df["phân loại"] = df["known"].map(lambda v: "✅ Điều trị" if v else "⚠️ Dự đoán/Tác dụng phụ")
    display_cols = [c for c in ["direction", "input_name", "target_name", "phân loại", "score (%)", "timestamp"] if c in df.columns]
    st.dataframe(df[display_cols] if display_cols else df, use_container_width=True, hide_index=True)


def show_metric_row(stats: dict) -> None:
    items = [
        ("total_users",       "👤 Users",       "#f0fdf4", "#4ade80", "#14532d"),
        ("total_drugs",       "💊 Thuốc",        "#dbeafe", "#60a5fa", "#1e3a8a"),
        ("total_diseases",    "🦠 Bệnh",         "#fef9c3", "#fbbf24", "#713f12"),
        ("total_links",       "🔗 Liên kết",     "#fae8ff", "#c084fc", "#581c87"),
        ("total_predictions", "🔬 Predictions",  "#ffedd5", "#fb923c", "#7c2d12"),
    ]
    cols_html = ""
    for key, label, bg, border, fg in items:
        val = int(stats.get(key, 0))
        cols_html += f"""
        <div style="flex:1;background:{bg};border:1px solid {border};border-radius:10px;
                    padding:0.8rem 1rem;box-shadow:0 2px 8px rgba(0,0,0,0.06);min-width:0">
          <div style="font-size:0.73rem;font-weight:700;color:{fg};
                      text-transform:uppercase;letter-spacing:0.05em;margin-bottom:0.25rem;
                      white-space:nowrap;overflow:hidden;text-overflow:ellipsis">
            {label}
          </div>
          <div style="font-size:1.8rem;font-weight:800;color:{fg};line-height:1">{val}</div>
        </div>"""
    st.markdown(
        f'<div style="display:flex;gap:0.8rem;margin-bottom:0.5rem">{cols_html}</div>',
        unsafe_allow_html=True,
    )
