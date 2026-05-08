from __future__ import annotations

import pandas as pd
import streamlit as st

from ..services.api_client import ApiClient
from ..ui.components import card_close, card_open, show_metric_row

_METRIC_KEYS = ["AUC", "AUPR", "Accuracy", "Precision", "Recall", "F1", "MCC"]
_METRIC_COLORS = {
    "AUC":       "#0d9488",
    "AUPR":      "#1e40af",
    "Accuracy":  "#9333ea",
    "Precision": "#d97706",
    "Recall":    "#dc2626",
    "F1":        "#16a34a",
    "MCC":       "#0ea5e9",
}


def _flat_mean(m: dict) -> dict:
    out = {}
    for k, v in m.items():
        if isinstance(v, dict):
            out[k] = float(v.get("mean") or 0)
        elif isinstance(v, (int, float)):
            out[k] = float(v)
    return out


def _flat_std(m: dict) -> dict:
    out = {}
    for k, v in m.items():
        if isinstance(v, dict):
            out[k] = v.get("std")
        else:
            out[k] = None
    return out

def render_admin_console(api_base_url: str, token: str) -> None:
    client = ApiClient(api_base_url, token=token)

    # ── System Overview ──────────────────────────────────────────────
    card_open("Tổng quan hệ thống", "📊")
    try:
        stats = client.admin_stats()
        by_dir = client.admin_prediction_direction_stats()
        show_metric_row(stats)
        st.markdown("<br>", unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**Phân bổ Predictions theo hướng**")
            if by_dir:
                df_dir = pd.DataFrame(by_dir)
                df_dir["direction"] = df_dir["direction"].map(
                    {"drug_to_disease": "💊→🦠 Thuốc→Bệnh", "disease_to_drug": "🦠→💊 Bệnh→Thuốc"}
                ).fillna(df_dir["direction"])
                st.dataframe(df_dir, use_container_width=True, hide_index=True)
            else:
                st.info("Chưa có dữ liệu.")
    except Exception as exc:  # noqa: BLE001
        st.error(f"Không tải được thống kê: {exc}")
    card_close()

    # ── Management Tabs ──────────────────────────────────────────────
    tab_drugs, tab_diseases, tab_links, tab_logs, tab_model, tab_seed = st.tabs(
        ["💊 Quản lý Thuốc", "🦠 Quản lý Bệnh", "🔗 Liên kết", "📋 Prediction Logs", "📊 Model", "🗄️ Nhập từ Dataset"]
    )

    # -- Drugs --
    with tab_drugs:
        card_open("Thêm / Cập nhật thuốc", "💊")
        with st.form("admin_save_drug"):
            c1, c2 = st.columns(2)
            drug_id = c1.number_input("Drug ID", min_value=0, step=1)
            drug_name = c2.text_input("Tên thuốc")
            c3, c4 = st.columns(2)
            external_id = c3.text_input("External ID (tùy chọn)")
            smiles = c4.text_input("SMILES (tùy chọn)")
            if st.form_submit_button("💾 Lưu thuốc", use_container_width=True):
                try:
                    client.admin_save_drug(
                        drug_id=int(drug_id),
                        name=str(drug_name),
                        external_id=str(external_id) if external_id else None,
                        smiles=str(smiles) if smiles else None,
                    )
                    st.success("✅ Đã lưu thuốc.")
                except Exception as exc:  # noqa: BLE001
                    st.error(f"❌ {exc}")
        card_close()

        card_open("Danh sách thuốc", "📋")
        if st.button("🔄 Tải danh sách thuốc", use_container_width=True, key="load_drugs"):
            try:
                rows = client.list_drugs(limit=500)
                st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
            except Exception as exc:  # noqa: BLE001
                st.error(f"❌ {exc}")
        card_close()

    # -- Diseases --
    with tab_diseases:
        card_open("Thêm / Cập nhật bệnh", "🦠")
        with st.form("admin_save_disease"):
            c1, c2 = st.columns(2)
            disease_id = c1.number_input("Disease ID", min_value=0, step=1)
            disease_name = c2.text_input("Tên bệnh")
            if st.form_submit_button("💾 Lưu bệnh", use_container_width=True):
                try:
                    client.admin_save_disease(disease_id=int(disease_id), name=str(disease_name))
                    st.success("✅ Đã lưu bệnh.")
                except Exception as exc:  # noqa: BLE001
                    st.error(f"❌ {exc}")
        card_close()

        card_open("Danh sách bệnh", "📋")
        if st.button("🔄 Tải danh sách bệnh", use_container_width=True, key="load_diseases"):
            try:
                rows = client.list_diseases(limit=500)
                st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
            except Exception as exc:  # noqa: BLE001
                st.error(f"❌ {exc}")
        card_close()

    # -- Links --
    with tab_links:
        card_open("Thêm liên kết Thuốc–Bệnh", "🔗")
        with st.form("admin_save_link"):
            c1, c2 = st.columns(2)
            drug_id_l = c1.number_input("Drug ID", min_value=0, step=1, key="lid_drug")
            disease_id_l = c2.number_input("Disease ID", min_value=0, step=1, key="lid_disease")
            if st.form_submit_button("➕ Thêm liên kết", use_container_width=True):
                try:
                    client.admin_save_link(drug_id=int(drug_id_l), disease_id=int(disease_id_l))
                    st.success("✅ Đã thêm liên kết.")
                except Exception as exc:  # noqa: BLE001
                    st.error(f"❌ {exc}")
        card_close()

        card_open("Danh sách liên kết", "📋")
        if st.button("🔄 Tải danh sách liên kết", use_container_width=True, key="load_links"):
            try:
                rows = client.list_links(limit=1000)
                st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
            except Exception as exc:  # noqa: BLE001
                st.error(f"❌ {exc}")
        card_close()

    # -- Prediction Logs --
    with tab_logs:
        card_open("Lịch sử dự đoán toàn hệ thống", "📋")
        c1, c2 = st.columns([1, 4])
        with c1:
            if st.button("🔄 Tải logs", use_container_width=True, key="load_logs"):
                st.session_state.pop("admin_predictions", None)
        with c2:
            st.markdown(
                '<div class="info-box" style="font-size:0.83rem">'
                '📊 Hiển thị tối đa 400 bản ghi prediction gần nhất.</div>',
                unsafe_allow_html=True,
            )

        if st.session_state.get("admin_predictions") is None:
            try:
                st.session_state["admin_predictions"] = client.admin_predictions(limit=400)
            except Exception as exc:  # noqa: BLE001
                st.error(f"❌ {exc}")
                st.session_state["admin_predictions"] = []

        rows = st.session_state.get("admin_predictions", [])
        if rows:
            df = pd.DataFrame(rows)
            if "score" in df.columns:
                df["score (%)"] = (pd.to_numeric(df["score"], errors="coerce") * 100).map(
                    lambda x: f"{x:.2f}%"
                )
            if "direction" in df.columns:
                df["direction"] = df["direction"].map(
                    {"drug_to_disease": "💊→🦠 Thuốc→Bệnh", "disease_to_drug": "🦠→💊 Bệnh→Thuốc"}
                ).fillna(df["direction"])
            display_cols = [c for c in ["user_id", "direction", "input_name", "target_name", "score (%)", "timestamp"] if c in df.columns]
            st.dataframe(df[display_cols] if display_cols else df, use_container_width=True, hide_index=True)
        else:
            st.markdown('<div class="info-box">Chưa có dữ liệu.</div>', unsafe_allow_html=True)
        card_close()

    # -- Model Metrics & Comparison --
    with tab_model:
        card_open("Chỉ số đánh giá mô hình (AUC, AUPR, …)", "📊")
        st.markdown(
            '<div class="info-box">'
            'Xem và tính lại chỉ số K-Fold của các mô hình AI. '
            'Nút <b>🔁 Tính lại từ weights</b> sẽ đọc từng file '
            '<code>best_fold_n.pth</code> để tính mean & std chính xác.</div>',
            unsafe_allow_html=True,
        )

        # ── Dataset selector + reload ──────────────────────────────────
        c_ds, c_reload, c_recalc = st.columns([2, 1, 1])
        with c_ds:
            _avail = ["B-dataset", "C-dataset", "F-dataset"]
            _sel_admin_ds = st.selectbox("📊 Chọn dataset", options=_avail, index=0, key="admin_sel_ds")
        with c_reload:
            if st.button("🔄 Tải lại", use_container_width=True, key="admin_btn_reload"):
                st.session_state.pop("admin_raw_metrics", None)
                st.rerun()
        with c_recalc:
            if st.button("🔁 Tính lại từ weights", use_container_width=True, key="admin_btn_recalc"):
                with st.spinner(f"Đang tính lại metrics từ .pth cho {_sel_admin_ds}…"):
                    try:
                        res = client.admin_recalculate_metrics(_sel_admin_ds)
                        st.session_state.pop("admin_raw_metrics", None)
                        st.success(f"✅ Đã tính lại: {res.get('message', 'OK')}")
                    except Exception as exc:  # noqa: BLE001
                        st.error(f"❌ {exc}")

        # ── Load and display metrics ───────────────────────────────────
        if st.session_state.get("admin_raw_metrics") is None:
            try:
                st.session_state["admin_raw_metrics"] = client.model_metrics()
            except Exception as exc:  # noqa: BLE001
                st.error(f"Không tải được metrics: {exc}")
                st.session_state["admin_raw_metrics"] = {}

        _raw: dict = st.session_state.get("admin_raw_metrics", {})
        if "datasets" in _raw:
            _ds_data = _raw["datasets"].get(_sel_admin_ds, {})
            _cur_raw = _ds_data.get("metrics", {})
        elif "metrics" in _raw:
            _cur_raw = _raw.get("metrics", {})
        else:
            _cur_raw = {}

        cur_m = _flat_mean(_cur_raw)
        cur_s = _flat_std(_cur_raw)

        if cur_m:
            cards_html = '<div style="display:grid;grid-template-columns:repeat(7,1fr);gap:0.5rem;margin:0.6rem 0">'
            for k in _METRIC_KEYS:
                v = cur_m.get(k)
                s = cur_s.get(k)
                val_str = f"{v:.4f}" if v is not None else "—"
                std_str = f"±{s:.4f}" if s is not None else "std: —"
                c = _METRIC_COLORS.get(k, "#0d9488")
                cards_html += (
                    f'<div style="background:var(--surface);border:1px solid var(--border);'
                    f'border-radius:8px;padding:0.6rem 0.5rem;text-align:center;'
                    f'border-top:3px solid {c}">'
                    f'<div style="font-size:1.05rem;font-weight:800;color:{c}">{val_str}</div>'
                    f'<div style="font-size:0.65rem;color:var(--muted);margin-top:0.1rem">{std_str}</div>'
                    f'<div style="font-size:0.7rem;color:var(--muted);font-weight:600;'
                    f'text-transform:uppercase;margin-top:0.15rem">{k}</div>'
                    f'</div>'
                )
            cards_html += '</div>'
            st.markdown(cards_html, unsafe_allow_html=True)
        else:
            st.info("ℹ️ Chưa có metrics. Nhấn 🔁 Tính lại từ weights để tạo.")

        card_close()

        # ── Model Comparison ───────────────────────────────────────────
        card_open("So sánh với mô hình khác", "📂")
        st.markdown(
            '<div class="info-box" style="font-size:0.83rem">'
            'Nhấn <b>📂 Chọn file JSON…</b> để chọn trực tiếp file '
            '<code>kfold_metrics.json</code> của mô hình muốn so sánh.</div>',
            unsafe_allow_html=True,
        )

        _col_browse, _col_clear = st.columns([3, 1])
        with _col_browse:
            if st.button("📂 Chọn file JSON…", use_container_width=True, key="admin_btn_browse"):
                try:
                    import tkinter as _tk
                    from tkinter import filedialog as _fd
                    _root = _tk.Tk()
                    _root.withdraw()
                    _root.wm_attributes("-topmost", True)
                    _chosen = _fd.askopenfilename(
                        title="Chọn file kfold_metrics.json",
                        filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
                        parent=_root,
                    )
                    _root.destroy()
                    if _chosen:
                        st.session_state["admin_cmp_path"] = _chosen
                        st.session_state.pop("admin_cmp_result", None)
                except Exception:  # noqa: BLE001
                    st.warning("⚠️ Không thể mở hộp thoại chọn file.")
        with _col_clear:
            if st.button("🗑️ Xoá", use_container_width=True, key="admin_btn_clear_cmp"):
                st.session_state["admin_cmp_path"] = ""
                st.session_state.pop("admin_cmp_result", None)

        cmp_path: str = st.session_state.get("admin_cmp_path", "")

        # Hiển thị file đã chọn
        if cmp_path:
            st.markdown(
                f'<div style="font-size:0.83rem;padding:0.4rem 0.7rem;background:var(--surface);'
                f'border:1px solid var(--border);border-radius:6px;margin-bottom:0.5rem;'
                f'color:var(--text);word-break:break-all">📄 {cmp_path}</div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                '<div style="font-size:0.83rem;padding:0.4rem 0.7rem;background:var(--surface);'
                'border:1px dashed var(--border);border-radius:6px;margin-bottom:0.5rem;'
                'color:var(--muted)">Chưa chọn file…</div>',
                unsafe_allow_html=True,
            )

        cmp_name = st.text_input(
            "🏷️ Tên mô hình so sánh",
            value=st.session_state.get("admin_cmp_name", "Mô hình so sánh"),
            key="admin_cmp_name_input",
        )
        st.session_state["admin_cmp_name"] = cmp_name

        if st.button("📊 So sánh ngay", use_container_width=True, key="admin_btn_do_compare"):
            if not cmp_path.strip():
                st.warning("⚠️ Vui lòng chọn file JSON trước.")
            else:
                with st.spinner("Đang đọc metrics mô hình so sánh…"):
                    try:
                        res = client.model_compare(cmp_path.strip())
                        st.session_state["admin_cmp_result"] = res
                        st.session_state["admin_cmp_label"] = cmp_name.strip() or "Mô hình so sánh"
                        st.success(f"✅ Đã đọc: {res.get('path', cmp_path)}")
                    except Exception as exc:  # noqa: BLE001
                        st.error(f"❌ {exc}")
                        st.session_state.pop("admin_cmp_result", None)

        cmp_result = st.session_state.get("admin_cmp_result")
        cmp_label = st.session_state.get("admin_cmp_label", "Mô hình so sánh")

        if cmp_result and cur_m:
            _cmp_raw = cmp_result.get("metrics", {})
            cmp_m = _flat_mean(_cmp_raw)
            cmp_s = _flat_std(_cmp_raw)

            # ── Thông số 2 mô hình song song ───────────────────────────
            st.markdown(
                '<div style="font-size:0.82rem;font-weight:700;color:var(--text);'
                'margin:0.8rem 0 0.4rem 0">🗂️ Thông tin mô hình</div>',
                unsafe_allow_html=True,
            )

            # Lấy thông tin mô hình hiện tại từ raw response
            _cur_ds_info = {}
            if "datasets" in _raw and _sel_admin_ds in _raw["datasets"]:
                _cur_ds_info = _raw["datasets"][_sel_admin_ds]

            # Thông tin mô hình so sánh từ JSON gốc
            _cmp_full: dict = {}
            try:
                import json as _json
                _cmp_full = _json.loads(__import__("pathlib").Path(cmp_result.get("path", "")).read_text(encoding="utf-8")) if cmp_result.get("path") else {}
            except Exception:  # noqa: BLE001
                pass

            def _info_row(label: str, val1: str, val2: str, accent1: str = "#0d9488", accent2: str = "#1e40af") -> str:
                return (
                    f'<div style="display:flex;gap:0.5rem;margin-bottom:0.25rem">'
                    f'<div style="flex:1.4;font-size:0.78rem;font-weight:600;color:var(--muted);'
                    f'padding:0.3rem 0.5rem">{label}</div>'
                    f'<div style="flex:2;font-size:0.82rem;color:{accent1};padding:0.3rem 0.5rem;'
                    f'background:var(--surface);border-radius:4px;border-left:3px solid {accent1}">{val1}</div>'
                    f'<div style="flex:2;font-size:0.82rem;color:{accent2};padding:0.3rem 0.5rem;'
                    f'background:var(--surface);border-radius:4px;border-left:3px solid {accent2}">{val2}</div>'
                    f'</div>'
                )

            cur_dataset_name = _cur_ds_info.get("path", "").replace("\\", "/").split("/")[-2] if _cur_ds_info.get("path") else _sel_admin_ds
            cur_so_fold = str(len([k for k in _cur_ds_info if k == "folds"])) if False else "—"
            cmp_dataset_name = _cmp_full.get("dataset", "—")
            cmp_so_fold = str(_cmp_full.get("so_fold", "—"))
            cmp_path_short = cmp_result.get("path", "—").replace("\\", "/").split("/")[-3:]
            cmp_path_str = "/".join(cmp_path_short) if cmp_path_short else "—"

            cur_auc_best = f"{cur_m.get('AUC', 0):.4f}" if cur_m.get("AUC") else "—"
            cmp_auc_best = f"{cmp_m.get('AUC', 0):.4f}" if cmp_m.get("AUC") else "—"

            info_html = (
                '<div style="background:var(--surface);border:1px solid var(--border);'
                'border-radius:8px;padding:0.7rem 0.5rem;margin-bottom:0.8rem">'
                # Header
                f'<div style="display:flex;gap:0.5rem;margin-bottom:0.4rem">'
                f'<div style="flex:1.4"></div>'
                f'<div style="flex:2;font-size:0.75rem;font-weight:800;color:#0d9488;'
                f'text-transform:uppercase;padding:0 0.5rem">🧠 {_sel_admin_ds}</div>'
                f'<div style="flex:2;font-size:0.75rem;font-weight:800;color:#1e40af;'
                f'text-transform:uppercase;padding:0 0.5rem">📂 {cmp_label}</div>'
                f'</div>'
            )
            info_html += _info_row("Dataset", cur_dataset_name, cmp_dataset_name)
            info_html += _info_row("K-Fold", f"{len(cur_m)} chỉ số / fold", f"{cmp_so_fold} folds")
            info_html += _info_row("AUC (mean)", cur_auc_best, cmp_auc_best)
            info_html += _info_row("Nguồn", f"weights/{_sel_admin_ds}/kfold_metrics.json", cmp_path_str)
            info_html += '</div>'
            st.markdown(info_html, unsafe_allow_html=True)

            # ── Bảng so sánh chi tiết ──────────────────────────────────
            st.markdown(
                '<div style="font-size:0.82rem;font-weight:700;color:var(--text);'
                'margin:0.4rem 0 0.4rem 0">📋 So sánh chi tiết</div>',
                unsafe_allow_html=True,
            )
            tbl = (
                '<div style="display:grid;grid-template-columns:1.6fr 1.4fr 0.9fr 1.4fr 0.9fr;gap:0;'
                'background:var(--surface);border:1px solid var(--border);border-radius:8px;overflow:hidden">'
                # Sub-header row: model names spanning 2 cols each
                '<div style="background:var(--table-head-bg);padding:0.4rem 0.7rem;font-size:0.7rem;'
                'font-weight:700;color:var(--muted);text-transform:uppercase;border-bottom:2px solid var(--border)">Chỉ số</div>'
                f'<div style="background:#0d948815;padding:0.4rem 0.7rem;font-size:0.72rem;font-weight:800;'
                f'color:#0d9488;text-transform:uppercase;border-bottom:2px solid #0d9488;grid-column:span 2">'
                f'🧠 {_sel_admin_ds}</div>'
                f'<div style="background:#1e40af15;padding:0.4rem 0.7rem;font-size:0.72rem;font-weight:800;'
                f'color:#1e40af;text-transform:uppercase;border-bottom:2px solid #1e40af;grid-column:span 2">'
                f'📂 {cmp_label}</div>'
                # Column headers
                '<div style="background:var(--table-head-bg);padding:0.35rem 0.7rem;font-size:0.68rem;'
                'font-weight:600;color:var(--muted)"></div>'
                '<div style="background:#0d948810;padding:0.35rem 0.7rem;font-size:0.68rem;'
                'font-weight:600;color:#0d9488">Mean</div>'
                '<div style="background:#0d948810;padding:0.35rem 0.7rem;font-size:0.68rem;'
                'font-weight:600;color:#0d9488">± Std</div>'
                '<div style="background:#1e40af10;padding:0.35rem 0.7rem;font-size:0.68rem;'
                'font-weight:600;color:#1e40af">Mean</div>'
                '<div style="background:#1e40af10;padding:0.35rem 0.7rem;font-size:0.68rem;'
                'font-weight:600;color:#1e40af">± Std</div>'
            )
            for i, k in enumerate(_METRIC_KEYS):
                v1 = cur_m.get(k)
                v2 = cmp_m.get(k)
                sd1 = cur_s.get(k)
                sd2 = cmp_s.get(k)
                s1 = f"{v1:.4f}" if v1 is not None else "—"
                s2 = f"{v2:.4f}" if v2 is not None else "—"
                ss1 = f"±{sd1:.4f}" if sd1 is not None else "—"
                ss2 = f"±{sd2:.4f}" if sd2 is not None else "—"
                win1 = win2 = False
                if v1 is not None and v2 is not None:
                    if v1 > v2:
                        win1 = True
                    elif v2 > v1:
                        win2 = True
                row_bg = "var(--surface)" if i % 2 == 0 else "var(--table-row-hover)"
                _border = "border-top:1px solid var(--table-row-border)"
                _c_base = f"background:{row_bg};padding:0.4rem 0.7rem;font-size:0.82rem;{_border}"
                _c1_bg = f"background:{'#0d94880d' if win1 else row_bg}"
                _c2_bg = f"background:{'#1e40af0d' if win2 else row_bg}"
                s1_html = f'<strong style="color:#0d9488">{s1} ▲</strong>' if win1 else s1
                s2_html = f'<strong style="color:#1e40af">{s2} ▲</strong>' if win2 else s2
                tbl += (
                    f'<div style="{_c_base};font-weight:600;color:var(--text)">{k}</div>'
                    f'<div style="{_c_base};{_c1_bg};color:{"#0d9488" if win1 else "var(--text)"}">{s1_html}</div>'
                    f'<div style="{_c_base};{_c1_bg};color:var(--muted);font-size:0.74rem">{ss1}</div>'
                    f'<div style="{_c_base};{_c2_bg};color:{"#1e40af" if win2 else "var(--text)"}">{s2_html}</div>'
                    f'<div style="{_c_base};{_c2_bg};color:var(--muted);font-size:0.74rem">{ss2}</div>'
                )
            tbl += '</div>'
            st.markdown(tbl, unsafe_allow_html=True)

            # ── Chú thích thắng/thua ──────────────────────────────────
            wins1 = sum(1 for k in _METRIC_KEYS if (cur_m.get(k) or 0) > (cmp_m.get(k) or 0))
            wins2 = sum(1 for k in _METRIC_KEYS if (cmp_m.get(k) or 0) > (cur_m.get(k) or 0))
            ties  = len(_METRIC_KEYS) - wins1 - wins2
            verdict_color = "#0d9488" if wins1 > wins2 else ("#1e40af" if wins2 > wins1 else "#6b7280")
            verdict = (
                f"🧠 {_sel_admin_ds} tốt hơn ({wins1}/{len(_METRIC_KEYS)} chỉ số)"
                if wins1 > wins2 else (
                    f"📂 {cmp_label} tốt hơn ({wins2}/{len(_METRIC_KEYS)} chỉ số)"
                    if wins2 > wins1 else f"Hai mô hình tương đương ({ties} hoà)"
                )
            )
            st.markdown(
                f'<div style="margin-top:0.5rem;padding:0.4rem 0.8rem;background:{verdict_color}18;'
                f'border-left:3px solid {verdict_color};border-radius:4px;'
                f'font-size:0.82rem;font-weight:700;color:{verdict_color}">{verdict}</div>',
                unsafe_allow_html=True,
            )

            # ── Biểu đồ so sánh ───────────────────────────────────────
            st.markdown(
                '<div style="font-size:0.82rem;font-weight:700;color:var(--text);'
                'margin:1rem 0 0.4rem 0">📈 Biểu đồ so sánh (mean)</div>',
                unsafe_allow_html=True,
            )
            chart_data = pd.DataFrame(
                {
                    f"🧠 {_sel_admin_ds}": [cur_m.get(k, 0) for k in _METRIC_KEYS],
                    cmp_label: [cmp_m.get(k, 0) for k in _METRIC_KEYS],
                },
                index=_METRIC_KEYS,
            )
            st.bar_chart(chart_data, use_container_width=True, height=300)
        elif cmp_result and not cur_m:
            st.info("ℹ️ Chưa có metrics mô hình hiện tại. Nhấn 🔁 Tính lại từ weights trước.")

        card_close()

    # ── Tab: Nhập từ Dataset ─────────────────────────────────────────
    with tab_seed:
        card_open("Nhập dữ liệu từ Dataset vào CSDL", "🗄️")
        st.markdown(
            '<div class="info-box">'
            'Chọn dataset để xem danh sách <b>Thuốc / Bệnh / Protein / Liên kết</b> có trong file CSV, '
            'sau đó nhấn <b>⬇️ Cập nhật vào DB</b> để lưu vào bảng riêng của dataset đó trong CSDL. '
            'Thao tác này <b>không ảnh hưởng</b> đến bảng chính (drugs/diseases/…) và '
            'sẽ <b>xóa rồi nạp lại</b> dữ liệu dataset đó trong CSDL.</div>',
            unsafe_allow_html=True,
        )

        _SEED_DATASETS = ["B-dataset", "C-dataset", "F-dataset"]
        col_ds, col_load, col_seed = st.columns([2, 1, 1])
        with col_ds:
            _sel_seed_ds = st.selectbox("📊 Chọn dataset", options=_SEED_DATASETS, index=0, key="seed_sel_ds")
        with col_load:
            _load_preview = st.button("👁️ Xem trước", use_container_width=True, key="seed_btn_preview")
        with col_seed:
            _do_seed = st.button("⬇️ Cập nhật vào DB", use_container_width=True, key="seed_btn_do", type="primary")

        if _load_preview:
            with st.spinner(f"Đang tải dữ liệu {_sel_seed_ds} từ DB…"):
                try:
                    preview = client.admin_dataset_preview(_sel_seed_ds)
                    st.session_state["seed_preview"] = preview
                    st.session_state["seed_preview_ds"] = _sel_seed_ds
                except Exception as exc:  # noqa: BLE001
                    st.error(f"❌ {exc}")
                    st.session_state.pop("seed_preview", None)

        if _do_seed:
            with st.spinner(f"Đang cập nhật {_sel_seed_ds} vào DB…"):
                try:
                    result = client.admin_seed_dataset(_sel_seed_ds)
                    counts = {
                        "Thuốc": result.get("drugs", 0),
                        "Bệnh": result.get("diseases", 0),
                        "Protein": result.get("proteins", 0),
                        "Liên kết": result.get("links", 0),
                    }
                    msg_parts = " · ".join(f"**{k}**: {v}" for k, v in counts.items())
                    st.success(f"✅ {result.get('message', 'Xong')} — {msg_parts}")
                    # Reload preview after seed
                    st.session_state.pop("seed_preview", None)
                    try:
                        preview = client.admin_dataset_preview(_sel_seed_ds)
                        st.session_state["seed_preview"] = preview
                        st.session_state["seed_preview_ds"] = _sel_seed_ds
                    except Exception:  # noqa: BLE001
                        pass
                except Exception as exc:  # noqa: BLE001
                    st.error(f"❌ {exc}")

        # ── Hiển thị preview ──────────────────────────────────────────
        preview_data = st.session_state.get("seed_preview")
        preview_ds = st.session_state.get("seed_preview_ds", "")
        if preview_data and preview_ds == _sel_seed_ds:
            counts = preview_data.get("counts", {})
            # Count cards
            cnt_html = '<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:0.6rem;margin:0.8rem 0">'
            for icon, lbl, key, color in [
                ("💊", "Thuốc", "drugs", "#0d9488"),
                ("🦠", "Bệnh", "diseases", "#1e40af"),
                ("🧬", "Protein", "proteins", "#9333ea"),
                ("🔗", "Liên kết", "links", "#d97706"),
            ]:
                n = counts.get(key, 0)
                cnt_html += (
                    f'<div style="background:var(--surface);border:1px solid var(--border);'
                    f'border-radius:8px;padding:0.7rem;text-align:center;border-top:3px solid {color}">'
                    f'<div style="font-size:1.4rem">{icon}</div>'
                    f'<div style="font-size:1.3rem;font-weight:800;color:{color}">{n:,}</div>'
                    f'<div style="font-size:0.72rem;color:var(--muted);font-weight:600;'
                    f'text-transform:uppercase">{lbl}</div></div>'
                )
            cnt_html += '</div>'
            st.markdown(cnt_html, unsafe_allow_html=True)

            # Data tables in sub-tabs
            sub_d, sub_dis, sub_p, sub_l = st.tabs(["💊 Thuốc", "🦠 Bệnh", "🧬 Protein", "🔗 Liên kết"])
            with sub_d:
                drugs_data = preview_data.get("drugs", [])
                if drugs_data:
                    df_d = pd.DataFrame(drugs_data)
                    st.dataframe(df_d, use_container_width=True, hide_index=True, height=400)
                else:
                    st.info("Chưa có dữ liệu thuốc cho dataset này. Nhấn ⬇️ Cập nhật vào DB trước.")
            with sub_dis:
                diseases_data = preview_data.get("diseases", [])
                if diseases_data:
                    df_dis = pd.DataFrame(diseases_data)
                    st.dataframe(df_dis, use_container_width=True, hide_index=True, height=400)
                else:
                    st.info("Chưa có dữ liệu bệnh cho dataset này.")
            with sub_p:
                proteins_data = preview_data.get("proteins", [])
                if proteins_data:
                    df_p = pd.DataFrame(proteins_data)
                    st.dataframe(df_p, use_container_width=True, hide_index=True, height=400)
                else:
                    st.info("Chưa có dữ liệu protein cho dataset này.")
            with sub_l:
                links_data = preview_data.get("links", [])
                if links_data:
                    df_l = pd.DataFrame(links_data)
                    st.dataframe(df_l, use_container_width=True, hide_index=True, height=400)
                else:
                    st.info("Chưa có dữ liệu liên kết cho dataset này.")
        elif not preview_data:
            st.markdown(
                '<div class="warn-box" style="margin-top:0.8rem">👆 Nhấn <strong>👁️ Xem trước</strong> '
                'để xem dữ liệu đã lưu trong DB, hoặc nhấn <strong>⬇️ Cập nhật vào DB</strong> '
                'để nạp dữ liệu từ file CSV.</div>',
                unsafe_allow_html=True,
            )

        card_close()
