from __future__ import annotations

import io
import re

import streamlit as st

from ..config import DATASET_OPTIONS
from ..services.api_client import ApiClient
from ..ui.components import card_open, card_close, show_history_table, show_split_result_table


def _load_dropdown_values(key: str, fetcher):
    if st.session_state.get(key) is None:
        try:
            st.session_state[key] = fetcher()
        except Exception as exc:
            st.error(f"Không tải được dữ liệu dropdown: {exc}")
            st.session_state[key] = []
    return st.session_state[key]


def _clean_filename(value: str) -> str:
    filename = re.sub(r"[^A-Za-z0-9_.-]+", "_", str(value).strip())
    return filename.strip("_.-") or "molecule"


def _render_molecule_preview(smiles: str | None, name: str) -> bytes | None:
    if not smiles:
        st.info("Không có SMILES để hiển thị cấu trúc phân tử.")
        return None

    try:
        from rdkit import Chem
        from rdkit.Chem import Draw
        from PIL import Image as PILImage

        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            st.error("SMILES không hợp lệ, không thể vẽ cấu trúc phân tử.")
            return None

        image = Draw.MolToImage(mol, size=(320, 320))
    except ImportError as exc:
        st.error(f"Không thể vẽ cấu trúc phân tử. RDKit chưa được cài đặt hoặc không khả dụng: {exc}")
        return None

    try:
        st.image(image, caption=f"Cấu trúc phân tử của {name}", width=320)

        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        buffer.seek(0)
        return buffer.getvalue()
    except Exception as exc:  # noqa: BLE001
        st.error(f"Không thể tạo ảnh phân tử: {exc}")
        return None


def _render_molecule_download(image_bytes: bytes | None, name: str) -> None:
    if not image_bytes:
        return

    st.download_button(
        "Tải ảnh PNG",
        data=image_bytes,
        file_name=f"{_clean_filename(name)}.png",
        mime="image/png",
    )


# ── Drug network layout constants ────────────────────────────────────────
_DRUG_COLORS = ["#0d9488", "#1e40af", "#9333ea", "#dc2626", "#d97706"]
_CARD_H = 60   # pixel height per card row in network view
_HDR_H  = 38   # pixel height for column headers


def _build_network_html(
    drug_names: list[str],
    drug_info_map: dict,
    drug_results: dict,
    top_diseases: int = 20,
) -> str:
    """Return HTML: drug cards | SVG bezier connectors | disease cards."""
    colors = _DRUG_COLORS

    # Aggregate diseases across all drugs
    disease_map: dict[str, dict] = {}
    for dname in drug_names:
        for r in drug_results.get(dname, []):
            nm = r["name"]
            if nm not in disease_map:
                disease_map[nm] = {"score": r["score"], "known": r["known"], "drugs": set()}
            disease_map[nm]["drugs"].add(dname)
            disease_map[nm]["score"] = max(disease_map[nm]["score"], r["score"])
            if r["known"]:
                disease_map[nm]["known"] = True

    diseases = sorted(disease_map.items(), key=lambda x: -x[1]["score"])[:top_diseases]

    n_d   = len(drug_names)
    n_dis = len(diseases)
    if not n_dis:
        return '<div class="warn-box">⚠️ Không có kết quả bệnh nào từ các thuốc đã chọn.</div>'

    svg_h = _HDR_H + max(n_d, n_dis) * _CARD_H

    # ── Drug column ────────────────────────────────────────────────────
    drug_col = (
        f'<div style="font-size:0.68rem;font-weight:700;text-transform:uppercase;'
        f'color:var(--muted);letter-spacing:0.06em;height:{_HDR_H}px;'
        f'display:flex;align-items:flex-end;padding-bottom:6px">💊 Thuốc đã chọn</div>'
    )
    for i, nm in enumerate(drug_names):
        c    = colors[i % len(colors)]
        info = drug_info_map.get(nm, {})
        did  = info.get("id", "—")
        drug_col += (
            f'<div style="height:{_CARD_H}px;display:flex;align-items:center;padding-right:6px">'
            f'<div style="border:2px solid {c};border-radius:8px;padding:6px 10px;width:100%;'
            f'box-sizing:border-box;background:var(--surface)">'
            f'<div style="font-size:0.6rem;font-weight:700;color:{c};text-transform:uppercase">'
            f'💊 Thuốc {i + 1} · ID {did}</div>'
            f'<div style="font-size:0.82rem;font-weight:700;color:var(--text);'
            f'white-space:nowrap;overflow:hidden;text-overflow:ellipsis" title="{nm}">{nm}</div>'
            f'</div></div>'
        )

    # ── Disease column ─────────────────────────────────────────────────
    dis_col = (
        f'<div style="font-size:0.68rem;font-weight:700;text-transform:uppercase;'
        f'color:var(--muted);letter-spacing:0.06em;height:{_HDR_H}px;'
        f'display:flex;align-items:flex-end;padding-bottom:6px;padding-left:8px">🧫 Bệnh liên quan</div>'
    )
    for j, (nm, info) in enumerate(diseases):
        drug_indices = [k for k, dn in enumerate(drug_names) if dn in info["drugs"]]
        dots = "".join(
            f'<span style="display:inline-block;width:8px;height:8px;border-radius:50%;'
            f'background:{colors[k % len(colors)]};margin-right:2px;flex-shrink:0"></span>'
            for k in drug_indices
        )
        if info["known"]:
            badge = (
                '<span style="background:var(--known-bg);color:var(--known-fg);'
                'border:1px solid var(--known-fg);border-radius:999px;'
                'padding:1px 6px;font-size:0.62rem;font-weight:700">✅ Đã biết</span>'
            )
        else:
            badge = (
                '<span style="background:var(--warn-bg);color:var(--warn-fg);'
                'border:1px solid var(--warn-border);border-radius:999px;'
                'padding:1px 6px;font-size:0.62rem;font-weight:700">🔬 Dự đoán</span>'
            )
        bar_w = int(info["score"] * 100)
        dis_col += (
            f'<div style="height:{_CARD_H}px;display:flex;align-items:center;padding-left:8px">'
            f'<div style="border:1px solid var(--border);border-radius:8px;padding:5px 8px;'
            f'width:100%;box-sizing:border-box;background:var(--surface)">'
            f'<div style="display:flex;align-items:center;gap:3px">{dots}{badge}</div>'
            f'<div style="font-size:0.8rem;font-weight:700;color:var(--text);'
            f'white-space:nowrap;overflow:hidden;text-overflow:ellipsis;margin-top:2px" title="{nm}">{nm}</div>'
            f'<div style="background:var(--score-bar-bg);border-radius:3px;height:3px;width:100%;margin-top:3px">'
            f'<div style="background:var(--primary);border-radius:3px;height:3px;width:{bar_w}%"></div>'
            f'</div></div></div>'
        )

    # ── SVG bezier lines ───────────────────────────────────────────────
    paths = []
    for i, dn in enumerate(drug_names):
        c  = colors[i % len(colors)]
        dy = _HDR_H + i * _CARD_H + _CARD_H // 2
        for j, (dis_nm, dis_info) in enumerate(diseases):
            if dn in dis_info["drugs"]:
                disy = _HDR_H + j * _CARD_H + _CARD_H // 2
                paths.append(
                    f'<path d="M 0,{dy} C 40,{dy} 60,{disy} 100,{disy}" '
                    f'stroke="{c}" stroke-width="1.8" fill="none" opacity="0.72"/>'
                )

    svg = (
        f'<svg viewBox="0 0 100 {svg_h}" preserveAspectRatio="none" '
        f'style="width:100%;height:{svg_h}px;overflow:visible;display:block">'
        + "".join(paths) + "</svg>"
    )

    return (
        f'<div style="display:flex;align-items:flex-start;gap:0;margin-top:0.8rem">'
        f'<div style="flex:2.2;min-width:0;min-height:{svg_h}px">{drug_col}</div>'
        f'<div style="flex:0.7;min-width:60px;height:{svg_h}px">{svg}</div>'
        f'<div style="flex:3.1;min-width:0;min-height:{svg_h}px">{dis_col}</div>'
        f'</div>'
    )


def _build_dis_network_html(
    disease_names: list[str],
    disease_results: dict,
    top_drugs: int = 20,
) -> str:
    """Return HTML: disease cards | SVG bezier connectors | drug cards. (Disease → Drug)"""
    colors = _DRUG_COLORS

    # Aggregate drugs across all diseases
    drug_map: dict[str, dict] = {}
    for dname in disease_names:
        for r in disease_results.get(dname, []):
            nm = r["name"]
            if nm not in drug_map:
                drug_map[nm] = {"score": r["score"], "known": r["known"], "diseases": set()}
            drug_map[nm]["diseases"].add(dname)
            drug_map[nm]["score"] = max(drug_map[nm]["score"], r["score"])
            if r["known"]:
                drug_map[nm]["known"] = True

    drugs_sorted = sorted(drug_map.items(), key=lambda x: -x[1]["score"])[:top_drugs]

    n_dis  = len(disease_names)
    n_drug = len(drugs_sorted)
    if not n_drug:
        return '<div class="warn-box">⚠️ Không có kết quả thuốc nào từ các bệnh đã chọn.</div>'

    svg_h = _HDR_H + max(n_dis, n_drug) * _CARD_H

    # ── Disease column (left) ──────────────────────────────────────────
    dis_col = (
        f'<div style="font-size:0.68rem;font-weight:700;text-transform:uppercase;'
        f'color:var(--muted);letter-spacing:0.06em;height:{_HDR_H}px;'
        f'display:flex;align-items:flex-end;padding-bottom:6px">🦠 Bệnh đã chọn</div>'
    )
    for i, nm in enumerate(disease_names):
        c = colors[i % len(colors)]
        dis_col += (
            f'<div style="height:{_CARD_H}px;display:flex;align-items:center;padding-right:6px">'
            f'<div style="border:2px solid {c};border-radius:8px;padding:6px 10px;width:100%;'
            f'box-sizing:border-box;background:var(--surface)">'
            f'<div style="font-size:0.6rem;font-weight:700;color:{c};text-transform:uppercase">'
            f'🦠 Bệnh {i + 1}</div>'
            f'<div style="font-size:0.82rem;font-weight:700;color:var(--text);'
            f'white-space:nowrap;overflow:hidden;text-overflow:ellipsis" title="{nm}">{nm}</div>'
            f'</div></div>'
        )

    # ── Drug column (right) ────────────────────────────────────────────
    drug_col = (
        f'<div style="font-size:0.68rem;font-weight:700;text-transform:uppercase;'
        f'color:var(--muted);letter-spacing:0.06em;height:{_HDR_H}px;'
        f'display:flex;align-items:flex-end;padding-bottom:6px;padding-left:8px">💊 Thuốc liên quan</div>'
    )
    for j, (nm, info) in enumerate(drugs_sorted):
        dis_indices = [k for k, dn in enumerate(disease_names) if dn in info["diseases"]]
        dots = "".join(
            f'<span style="display:inline-block;width:8px;height:8px;border-radius:50%;'
            f'background:{colors[k % len(colors)]};margin-right:2px;flex-shrink:0"></span>'
            for k in dis_indices
        )
        if info["known"]:
            badge = (
                '<span style="background:var(--known-bg);color:var(--known-fg);'
                'border:1px solid var(--known-fg);border-radius:999px;'
                'padding:1px 6px;font-size:0.62rem;font-weight:700">✅ Đã biết</span>'
            )
        else:
            badge = (
                '<span style="background:var(--warn-bg);color:var(--warn-fg);'
                'border:1px solid var(--warn-border);border-radius:999px;'
                'padding:1px 6px;font-size:0.62rem;font-weight:700">🔬 Dự đoán</span>'
            )
        bar_w = int(info["score"] * 100)
        drug_col += (
            f'<div style="height:{_CARD_H}px;display:flex;align-items:center;padding-left:8px">'
            f'<div style="border:1px solid var(--border);border-radius:8px;padding:5px 8px;'
            f'width:100%;box-sizing:border-box;background:var(--surface)">'
            f'<div style="display:flex;align-items:center;gap:3px">{dots}{badge}</div>'
            f'<div style="font-size:0.8rem;font-weight:700;color:var(--text);'
            f'white-space:nowrap;overflow:hidden;text-overflow:ellipsis;margin-top:2px" title="{nm}">{nm}</div>'
            f'<div style="background:var(--score-bar-bg);border-radius:3px;height:3px;width:100%;margin-top:3px">'
            f'<div style="background:var(--primary);border-radius:3px;height:3px;width:{bar_w}%"></div>'
            f'</div></div></div>'
        )

    # ── SVG bezier lines ───────────────────────────────────────────────
    paths = []
    for i, dn in enumerate(disease_names):
        c  = colors[i % len(colors)]
        dy = _HDR_H + i * _CARD_H + _CARD_H // 2
        for j, (drug_nm, drug_info) in enumerate(drugs_sorted):
            if dn in drug_info["diseases"]:
                disy = _HDR_H + j * _CARD_H + _CARD_H // 2
                paths.append(
                    f'<path d="M 0,{dy} C 40,{dy} 60,{disy} 100,{disy}" '
                    f'stroke="{c}" stroke-width="1.8" fill="none" opacity="0.72"/>'
                )

    svg = (
        f'<svg viewBox="0 0 100 {svg_h}" preserveAspectRatio="none" '
        f'style="width:100%;height:{svg_h}px;overflow:visible;display:block">'
        + "".join(paths) + "</svg>"
    )

    return (
        f'<div style="display:flex;align-items:flex-start;gap:0;margin-top:0.8rem">'
        f'<div style="flex:2.2;min-width:0;min-height:{svg_h}px">{dis_col}</div>'
        f'<div style="flex:0.7;min-width:60px;height:{svg_h}px">{svg}</div>'
        f'<div style="flex:3.1;min-width:0;min-height:{svg_h}px">{drug_col}</div>'
        f'</div>'
    )


def _build_protein_network_html(
    protein_names: list[str],
    protein_results: dict,
    target_key: str = "drugs",
    top_n: int = 20,
) -> str:
    """Return HTML: protein cards | SVG bezier | drug or disease cards."""
    colors = _DRUG_COLORS

    # Aggregate targets across all proteins
    target_map: dict[str, dict] = {}
    for pname in protein_names:
        for r in protein_results.get(pname, {}).get(target_key, []):
            nm = r["name"]
            if nm not in target_map:
                target_map[nm] = {"proteins": set()}
            target_map[nm]["proteins"].add(pname)

    targets = list(target_map.items())[:top_n]
    n_p = len(protein_names)
    n_t = len(targets)
    if not n_t:
        label = "thuốc" if target_key == "drugs" else "bệnh"
        return f'<div class="warn-box">⚠️ Không có {label} nào liên quan.</div>'

    svg_h = _HDR_H + max(n_p, n_t) * _CARD_H

    # ── Protein column (left) ──────────────────────────────────────────
    prot_col = (
        f'<div style="font-size:0.68rem;font-weight:700;text-transform:uppercase;'
        f'color:var(--muted);letter-spacing:0.06em;height:{_HDR_H}px;'
        f'display:flex;align-items:flex-end;padding-bottom:6px">🧬 Protein đã chọn</div>'
    )
    for i, pname in enumerate(protein_names):
        c         = colors[i % len(colors)]
        accession = protein_results.get(pname, {}).get("accession", pname)
        prot_col += (
            f'<div style="height:{_CARD_H}px;display:flex;align-items:center;padding-right:6px">'
            f'<div style="border:2px solid {c};border-radius:8px;padding:6px 10px;width:100%;'
            f'box-sizing:border-box;background:var(--surface)">'
            f'<div style="font-size:0.6rem;font-weight:700;color:{c};text-transform:uppercase">'
            f'🧬 Protein {i + 1}</div>'
            f'<div style="font-size:0.82rem;font-weight:700;color:var(--text);'
            f'white-space:nowrap;overflow:hidden;text-overflow:ellipsis" title="{accession}">{accession}</div>'
            f'</div></div>'
        )

    # ── Target column (right) ──────────────────────────────────────────
    right_icon  = "💊" if target_key == "drugs" else "🦠"
    right_label = "Thuốc liên quan" if target_key == "drugs" else "Bệnh liên quan"
    tgt_col = (
        f'<div style="font-size:0.68rem;font-weight:700;text-transform:uppercase;'
        f'color:var(--muted);letter-spacing:0.06em;height:{_HDR_H}px;'
        f'display:flex;align-items:flex-end;padding-bottom:6px;padding-left:8px">'
        f'{right_icon} {right_label}</div>'
    )
    for j, (nm, info) in enumerate(targets):
        p_indices = [k for k, pn in enumerate(protein_names) if pn in info["proteins"]]
        dots = "".join(
            f'<span style="display:inline-block;width:8px;height:8px;border-radius:50%;'
            f'background:{colors[k % len(colors)]};margin-right:2px;flex-shrink:0"></span>'
            for k in p_indices
        )
        tgt_col += (
            f'<div style="height:{_CARD_H}px;display:flex;align-items:center;padding-left:8px">'
            f'<div style="border:1px solid var(--border);border-radius:8px;padding:5px 8px;'
            f'width:100%;box-sizing:border-box;background:var(--surface)">'
            f'<div style="display:flex;align-items:center;gap:3px">{dots}</div>'
            f'<div style="font-size:0.8rem;font-weight:700;color:var(--text);'
            f'white-space:nowrap;overflow:hidden;text-overflow:ellipsis;margin-top:2px" title="{nm}">{nm}</div>'
            f'</div></div>'
        )

    # ── SVG bezier lines ───────────────────────────────────────────────
    paths = []
    for i, pn in enumerate(protein_names):
        c  = colors[i % len(colors)]
        dy = _HDR_H + i * _CARD_H + _CARD_H // 2
        for j, (t_nm, t_info) in enumerate(targets):
            if pn in t_info["proteins"]:
                disy = _HDR_H + j * _CARD_H + _CARD_H // 2
                paths.append(
                    f'<path d="M 0,{dy} C 40,{dy} 60,{disy} 100,{disy}" '
                    f'stroke="{c}" stroke-width="1.8" fill="none" opacity="0.72"/>'
                )

    svg = (
        f'<svg viewBox="0 0 100 {svg_h}" preserveAspectRatio="none" '
        f'style="width:100%;height:{svg_h}px;overflow:visible;display:block">'
        + "".join(paths) + "</svg>"
    )

    return (
        f'<div style="display:flex;align-items:flex-start;gap:0;margin-top:0.8rem">'
        f'<div style="flex:2.2;min-width:0;min-height:{svg_h}px">{prot_col}</div>'
        f'<div style="flex:0.7;min-width:60px;height:{svg_h}px">{svg}</div>'
        f'<div style="flex:3.1;min-width:0;min-height:{svg_h}px">{tgt_col}</div>'
        f'</div>'
    )


def _render_stats_group(client: "ApiClient") -> None:
    """Hiển thị nhóm thống kê: Thuốc / Bệnh / Protein / Liên kết trong database."""
    try:
        data = client.stats()
    except Exception:  # noqa: BLE001
        return  # Silent fail — không cản giao diện chính

    n_drug    = data.get("total_drugs", "—")
    n_disease = data.get("total_diseases", "—")
    n_protein = data.get("total_proteins", "—")
    n_links   = data.get("total_links", "—")

    def _stat_card(icon: str, label: str, value, color: str) -> str:
        return (
            f'<div style="background:var(--surface);border:1px solid var(--border);'
            f'border-radius:var(--radius);padding:0.9rem 1.1rem;text-align:center;'
            f'box-shadow:var(--shadow);border-top:3px solid {color}">'
            f'<div style="font-size:1.7rem;line-height:1">{icon}</div>'
            f'<div style="font-size:1.55rem;font-weight:800;color:{color};margin:0.3rem 0">'
            f'{value:,}</div>'
            f'<div style="font-size:0.78rem;color:var(--muted);font-weight:600;'
            f'text-transform:uppercase;letter-spacing:0.05em">{label}</div>'
            f'</div>'
        ) if isinstance(value, int) else (
            f'<div style="background:var(--surface);border:1px solid var(--border);'
            f'border-radius:var(--radius);padding:0.9rem 1.1rem;text-align:center;'
            f'box-shadow:var(--shadow);border-top:3px solid {color}">'
            f'<div style="font-size:1.7rem;line-height:1">{icon}</div>'
            f'<div style="font-size:1.55rem;font-weight:800;color:{color};margin:0.3rem 0">'
            f'{value}</div>'
            f'<div style="font-size:0.78rem;color:var(--muted);font-weight:600;'
            f'text-transform:uppercase;letter-spacing:0.05em">{label}</div>'
            f'</div>'
        )

    cards_html = (
        '<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:0.8rem;margin-bottom:1.2rem">'
        + _stat_card("💊", "Thuốc", n_drug,    "#0d9488")
        + _stat_card("🦠", "Bệnh",  n_disease, "#1e40af")
        + _stat_card("🧬", "Protein", n_protein, "#9333ea")
        + _stat_card("🔗", "Liên kết Drug–Disease", n_links, "#d97706")
        + '</div>'
    )
    st.markdown(cards_html, unsafe_allow_html=True)


def render_user_workspace(api_base_url: str, token: str) -> None:
    client = ApiClient(api_base_url, token=token)

    # ── Stats group ────────────────────────────────────────────────────
    _render_stats_group(client)

    tab_a, tab_b, tab_c, tab_d = st.tabs([
        "💊 Thuốc → Bệnh",
        "🦠 Bệnh → Thuốc",
        "🧬 Protein",
        "📋 Lịch sử",
    ])

    # ── Tab A: Drug → Disease ──────────────────────────────────────────
    with tab_a:
        card_open("Tìm bệnh tiềm năng từ tên thuốc", "💊")
        st.markdown(
            '<div class="info-box">'
            'Chọn số lượng thuốc muốn so sánh, sau đó chọn từng thuốc. '
            'AI sẽ dự đoán các bệnh liên quan và vẽ sơ đồ kết nối có màu phân biệt. '
            '<span class="badge-known" style="font-size:0.78rem">✅ Đã biết</span> '
            '= liên kết trong dataset huấn luyện; '
            '<span class="badge-pred" style="font-size:0.78rem">🔬 Dự đoán</span> '
            '= phát hiện mới từ AI.</div>',
            unsafe_allow_html=True,
        )

        selected_dataset_a = st.selectbox(
            "📊 Dataset",
            DATASET_OPTIONS,
            index=0,
            key="ds_d2d_outer",
            help="Chọn dataset — danh sách thuốc và kết quả dự đoán sẽ tải lại theo dataset này",
        )

        drugs = _load_dropdown_values(
            f"drug_options_{selected_dataset_a}",
            lambda ds=selected_dataset_a: client.list_drugs(limit=1000, dataset=ds),
        )
        drug_name_list = [item["name"] for item in drugs]
        drug_info_map  = {item["name"]: item for item in drugs}

        # ── Bước 1: số thuốc ─────────────────────────────────────────
        st.markdown(
            '<div style="font-size:0.78rem;font-weight:700;color:var(--muted);'
            'text-transform:uppercase;letter-spacing:0.06em;margin-bottom:0.3rem">'
            '🔢 Bước 1 — Chọn số lượng thuốc muốn so sánh (tối đa 5)</div>',
            unsafe_allow_html=True,
        )
        n_drugs = int(st.number_input(
            "Số thuốc muốn so sánh", min_value=1, max_value=5, value=1, step=1,
            key="n_drugs_d2d",
            help="Nhập 1–5. Mỗi thuốc sẽ có màu dây nối riêng trong sơ đồ.",
            label_visibility="collapsed",
        ))

        # ── Bước 2: chọn từng thuốc ──────────────────────────────────
        st.markdown(
            '<div style="font-size:0.78rem;font-weight:700;color:var(--muted);'
            'text-transform:uppercase;letter-spacing:0.06em;margin:0.6rem 0 0.3rem 0">'
            '💊 Bước 2 — Chọn tên từng thuốc</div>',
            unsafe_allow_html=True,
        )
        drug_sel_cols  = st.columns(n_drugs)
        selected_drugs: list[str] = []
        for i, col in enumerate(drug_sel_cols):
            c = _DRUG_COLORS[i % len(_DRUG_COLORS)]
            col.markdown(
                f'<div style="height:4px;background:{c};border-radius:4px;margin-bottom:4px"></div>',
                unsafe_allow_html=True,
            )
            default_idx = min(i, len(drug_name_list) - 1) if drug_name_list else 0
            nm = col.selectbox(
                f"💊 Thuốc {i + 1}",
                options=drug_name_list,
                index=default_idx,
                key=f"drug_d2d_{selected_dataset_a}_{i}",
            )
            selected_drugs.append(nm)

        # ── Bước 3: thông số + submit ─────────────────────────────────
        st.markdown(
            '<div style="font-size:0.78rem;font-weight:700;color:var(--muted);'
            'text-transform:uppercase;letter-spacing:0.06em;margin:0.6rem 0 0.3rem 0">'
            '⚙️ Bước 3 — Cấu hình tìm kiếm</div>',
            unsafe_allow_html=True,
        )
        with st.form("form_drug_to_disease"):
            fc2, fc3 = st.columns([2, 2])
            top_k     = fc2.slider(
                "🔢 Số kết quả mỗi thuốc (Top-K)",
                min_value=1, max_value=50, value=10, step=1, key="topk_d2d",
            )
            threshold = fc3.slider(
                "📏 Ngưỡng tối thiểu", min_value=0.0, max_value=1.0, value=0.0, step=0.01,
                key="thr_d2d", help="Chỉ hiển thị kết quả có điểm ≥ ngưỡng này",
            )
            submitted = st.form_submit_button("🔍 Dự đoán ngay", use_container_width=True)

        if submitted:
            unique_drugs = list(dict.fromkeys(d for d in selected_drugs if d))
            if not unique_drugs:
                st.warning("⚠️ Vui lòng chọn ít nhất một thuốc.")
            else:
                with st.spinner(f"🤖 AI đang phân tích {len(unique_drugs)} thuốc..."):
                    dr: dict[str, list] = {}
                    errors: list[str]   = []
                    for dname in unique_drugs:
                        try:
                            data = client.predict_drug_to_disease(
                                name=dname, top_k=top_k, threshold=threshold, dataset=selected_dataset_a
                            )
                            dr[dname] = data.get("results", [])
                        except Exception as exc:  # noqa: BLE001
                            errors.append(f"{dname}: {exc}")
                    if errors:
                        st.error("❌ Lỗi dự đoán: " + "; ".join(errors))
                    st.session_state["d2d_drug_results"]   = dr
                    st.session_state["d2d_selected_drugs"] = unique_drugs
                    st.session_state["d2d_drug_info_map"]  = {
                        d: drug_info_map.get(d, {}) for d in unique_drugs
                    }
                    st.session_state.pop("history_rows", None)

        # ── Kết quả ───────────────────────────────────────────────────
        dr_stored: dict | None = st.session_state.get("d2d_drug_results")
        sel_stored: list[str]  = st.session_state.get("d2d_selected_drugs", [])
        info_stored: dict      = st.session_state.get("d2d_drug_info_map", {})

        if dr_stored is not None and sel_stored:
            total_res = sum(len(v) for v in dr_stored.values())
            st.markdown(
                f'<div style="font-size:0.82rem;color:var(--muted);margin:0.6rem 0 0.2rem 0">'
                f'🔎 Kết quả từ <strong>{len(sel_stored)}</strong> thuốc · '
                f'<strong>{total_res}</strong> dự đoán tổng</div>',
                unsafe_allow_html=True,
            )

            # Sơ đồ mạng kết nối
            network_html = _build_network_html(
                drug_names=sel_stored,
                drug_info_map=info_stored,
                drug_results=dr_stored,
                top_diseases=top_k,
            )
            st.markdown(network_html, unsafe_allow_html=True)

            # Cấu trúc phân tử
            st.markdown(
                "<hr style='border:none;border-top:1px solid var(--border);margin:1.2rem 0 0.8rem 0'>",
                unsafe_allow_html=True,
            )
            st.markdown(
                '<div class="mol-section-title">🧪 Cấu trúc phân tử các thuốc đã chọn</div>',
                unsafe_allow_html=True,
            )
            n_per_row = min(len(sel_stored), 4)
            mol_cols  = st.columns(n_per_row)
            for i, dname in enumerate(sel_stored):
                with mol_cols[i % n_per_row]:
                    smiles  = info_stored.get(dname, {}).get("smiles")
                    c_color = _DRUG_COLORS[i % len(_DRUG_COLORS)]
                    st.markdown(
                        f'<div style="border-top:3px solid {c_color};border-radius:4px 4px 0 0;'
                        f'padding:4px 8px;font-size:0.72rem;font-weight:700;color:{c_color};'
                        f'text-transform:uppercase;margin-bottom:4px">💊 Thuốc {i + 1}: {dname}</div>',
                        unsafe_allow_html=True,
                    )
                    img_bytes = _render_molecule_preview(smiles, dname)
                    _render_molecule_download(img_bytes, dname)

            # Chú thích / ghi chú
            st.markdown(
                "<hr style='border:none;border-top:1px solid var(--border);margin:1rem 0 0.6rem 0'>",
                unsafe_allow_html=True,
            )
            legend_dots = "".join(
                f'<span style="display:inline-flex;align-items:center;gap:5px;margin-right:1rem">'
                f'<span style="display:inline-block;width:12px;height:12px;border-radius:50%;'
                f'background:{_DRUG_COLORS[i % len(_DRUG_COLORS)]}"></span>'
                f'<span style="font-size:0.82rem;color:var(--text);font-weight:600">{dn}</span>'
                f'</span>'
                for i, dn in enumerate(sel_stored)
            )
            all_known = sum(1 for v in dr_stored.values() for r in v if r.get("known"))
            all_pred  = sum(1 for v in dr_stored.values() for r in v if not r.get("known"))
            st.markdown(
                f'<div class="info-box">'
                f'<div style="font-weight:700;margin-bottom:0.4rem">📝 Chú thích màu sắc dây nối</div>'
                f'<div style="display:flex;flex-wrap:wrap;gap:0.2rem;margin-bottom:0.6rem">{legend_dots}</div>'
                f'<div style="font-size:0.82rem">'
                f'✅ <strong>Đã biết ({all_known})</strong>: liên kết có trong dataset huấn luyện — '
                f'đã được xác nhận qua nghiên cứu. &nbsp;|&nbsp; '
                f'🔬 <strong>Dự đoán ({all_pred})</strong>: AI suy luận từ cấu trúc đồ thị — '
                f'<em>không phải khuyến cáo y tế</em>.'
                f'</div></div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                '<div class="warn-box" style="margin-top:0.8rem">👆 Chọn thuốc và nhấn '
                '<strong>Dự đoán ngay</strong> để xem sơ đồ kết nối thuốc–bệnh.</div>',
                unsafe_allow_html=True,
            )
        card_close()

    # ── Tab B: Disease → Drug ──────────────────────────────────────────
    with tab_b:
        card_open("Tìm thuốc tiềm năng từ tên bệnh", "🦠")
        st.markdown(
            '<div class="info-box">'
            'Chọn số lượng bệnh muốn so sánh, sau đó chọn từng bệnh. '
            'AI sẽ dự đoán các thuốc liên quan và vẽ sơ đồ kết nối có màu phân biệt. '
            '<span class="badge-known" style="font-size:0.78rem">✅ Đã biết</span> '
            '= liên kết trong dataset huấn luyện; '
            '<span class="badge-pred" style="font-size:0.78rem">🔬 Dự đoán</span> '
            '= phát hiện mới từ AI.</div>',
            unsafe_allow_html=True,
        )

        selected_dataset_b = st.selectbox(
            "📊 Dataset",
            DATASET_OPTIONS,
            index=0,
            key="ds_dis2d_outer",
            help="Chọn dataset — danh sách bệnh và kết quả dự đoán sẽ tải lại theo dataset này",
        )

        diseases_raw = _load_dropdown_values(
            f"disease_options_{selected_dataset_b}",
            lambda ds=selected_dataset_b: client.list_diseases(limit=1000, dataset=ds),
        )
        disease_name_list = [item["name"] if isinstance(item, dict) else item for item in diseases_raw]

        # ── Bước 1: số bệnh ──────────────────────────────────────────
        st.markdown(
            '<div style="font-size:0.78rem;font-weight:700;color:var(--muted);'
            'text-transform:uppercase;letter-spacing:0.06em;margin-bottom:0.3rem">'
            '🔢 Bước 1 — Chọn số lượng bệnh muốn so sánh (tối đa 5)</div>',
            unsafe_allow_html=True,
        )
        n_diseases = int(st.number_input(
            "Số bệnh muốn so sánh", min_value=1, max_value=5, value=1, step=1,
            key="n_diseases_dis2d",
            help="Nhập 1–5. Mỗi bệnh sẽ có màu dây nối riêng trong sơ đồ.",
            label_visibility="collapsed",
        ))

        # ── Bước 2: chọn từng bệnh ───────────────────────────────────
        st.markdown(
            '<div style="font-size:0.78rem;font-weight:700;color:var(--muted);'
            'text-transform:uppercase;letter-spacing:0.06em;margin:0.6rem 0 0.3rem 0">'
            '🦠 Bước 2 — Chọn tên từng bệnh</div>',
            unsafe_allow_html=True,
        )
        dis_sel_cols      = st.columns(n_diseases)
        selected_diseases: list[str] = []
        for i, col in enumerate(dis_sel_cols):
            c = _DRUG_COLORS[i % len(_DRUG_COLORS)]
            col.markdown(
                f'<div style="height:4px;background:{c};border-radius:4px;margin-bottom:4px"></div>',
                unsafe_allow_html=True,
            )
            default_idx = min(i, len(disease_name_list) - 1) if disease_name_list else 0
            nm = col.selectbox(
                f"🦠 Bệnh {i + 1}",
                options=disease_name_list,
                index=default_idx,
                key=f"dis_dis2d_{selected_dataset_b}_{i}",
            )
            selected_diseases.append(nm)

        # ── Bước 3: thông số + submit ─────────────────────────────────
        st.markdown(
            '<div style="font-size:0.78rem;font-weight:700;color:var(--muted);'
            'text-transform:uppercase;letter-spacing:0.06em;margin:0.6rem 0 0.3rem 0">'
            '⚙️ Bước 3 — Cấu hình tìm kiếm</div>',
            unsafe_allow_html=True,
        )
        with st.form("form_disease_to_drug"):
            fc2, fc3 = st.columns([2, 2])
            top_k     = fc2.slider(
                "🔢 Số kết quả mỗi bệnh (Top-K)",
                min_value=1, max_value=50, value=10, step=1, key="topk_dis2d",
            )
            threshold = fc3.slider(
                "📏 Ngưỡng tối thiểu", min_value=0.0, max_value=1.0, value=0.0, step=0.01,
                key="thr_dis2d", help="Chỉ hiển thị kết quả có điểm ≥ ngưỡng này",
            )
            submitted_b = st.form_submit_button("🔍 Dự đoán ngay", use_container_width=True)

        if submitted_b:
            unique_diseases = list(dict.fromkeys(d for d in selected_diseases if d))
            if not unique_diseases:
                st.warning("⚠️ Vui lòng chọn ít nhất một bệnh.")
            else:
                with st.spinner(f"🤖 AI đang phân tích {len(unique_diseases)} bệnh..."):
                    dr_b: dict[str, list] = {}
                    errors_b: list[str]   = []
                    for dname in unique_diseases:
                        try:
                            data = client.predict_disease_to_drug(
                                name=dname, top_k=top_k, threshold=threshold, dataset=selected_dataset_b
                            )
                            dr_b[dname] = data.get("results", [])
                        except Exception as exc:  # noqa: BLE001
                            errors_b.append(f"{dname}: {exc}")
                    if errors_b:
                        st.error("❌ Lỗi dự đoán: " + "; ".join(errors_b))
                    st.session_state["dis2d_disease_results"]   = dr_b
                    st.session_state["dis2d_selected_diseases"] = unique_diseases
                    st.session_state.pop("history_rows", None)

        # ── Kết quả ───────────────────────────────────────────────────
        dr_b_stored: dict | None  = st.session_state.get("dis2d_disease_results")
        sel_b_stored: list[str]   = st.session_state.get("dis2d_selected_diseases", [])

        if dr_b_stored is not None and sel_b_stored:
            total_res_b = sum(len(v) for v in dr_b_stored.values())
            st.markdown(
                f'<div style="font-size:0.82rem;color:var(--muted);margin:0.6rem 0 0.2rem 0">'
                f'🔎 Kết quả từ <strong>{len(sel_b_stored)}</strong> bệnh · '
                f'<strong>{total_res_b}</strong> dự đoán tổng</div>',
                unsafe_allow_html=True,
            )

            # Sơ đồ mạng kết nối
            network_html_b = _build_dis_network_html(
                disease_names=sel_b_stored,
                disease_results=dr_b_stored,
                top_drugs=top_k,
            )
            st.markdown(network_html_b, unsafe_allow_html=True)

            # Chú thích / ghi chú
            st.markdown(
                "<hr style='border:none;border-top:1px solid var(--border);margin:1rem 0 0.6rem 0'>",
                unsafe_allow_html=True,
            )
            legend_dots_b = "".join(
                f'<span style="display:inline-flex;align-items:center;gap:5px;margin-right:1rem">'
                f'<span style="display:inline-block;width:12px;height:12px;border-radius:50%;'
                f'background:{_DRUG_COLORS[i % len(_DRUG_COLORS)]}"></span>'
                f'<span style="font-size:0.82rem;color:var(--text);font-weight:600">{dn}</span>'
                f'</span>'
                for i, dn in enumerate(sel_b_stored)
            )
            all_known_b = sum(1 for v in dr_b_stored.values() for r in v if r.get("known"))
            all_pred_b  = sum(1 for v in dr_b_stored.values() for r in v if not r.get("known"))
            st.markdown(
                f'<div class="info-box">'
                f'<div style="font-weight:700;margin-bottom:0.4rem">📝 Chú thích màu sắc dây nối</div>'
                f'<div style="display:flex;flex-wrap:wrap;gap:0.2rem;margin-bottom:0.6rem">{legend_dots_b}</div>'
                f'<div style="font-size:0.82rem">'
                f'✅ <strong>Đã biết ({all_known_b})</strong>: liên kết có trong dataset huấn luyện — '
                f'đã được xác nhận qua nghiên cứu. &nbsp;|&nbsp; '
                f'🔬 <strong>Dự đoán ({all_pred_b})</strong>: AI suy luận từ cấu trúc đồ thị — '
                f'<em>không phải khuyến cáo y tế</em>.'
                f'</div></div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                '<div class="warn-box" style="margin-top:0.8rem">👆 Chọn bệnh và nhấn '
                '<strong>Dự đoán ngay</strong> để xem sơ đồ kết nối bệnh–thuốc.</div>',
                unsafe_allow_html=True,
            )
        card_close()

    # ── Tab C: Protein ─────────────────────────────────────────────────
    with tab_c:
        card_open("Tra cứu Protein", "🧬")
        st.markdown(
            '<div class="info-box">'
            'Chọn số lượng Protein muốn so sánh, sau đó chọn từng Protein. '
            'Hệ thống sẽ vẽ sơ đồ kết nối tới thuốc và bệnh liên quan kèm '
            'cấu trúc hóa học của các thuốc liên kết (nếu có).</div>',
            unsafe_allow_html=True,
        )

        proteins         = _load_dropdown_values("protein_options", lambda: client.list_proteins(limit=1000))
        drugs_for_prot   = _load_dropdown_values("drug_options", lambda: client.list_drugs(limit=1000))
        protein_name_list = [item.get("accession") or item.get("name") or str(item.get("id", "")) for item in proteins]
        protein_info_map  = {(item.get("accession") or item.get("name") or str(item.get("id", ""))): item for item in proteins}
        drug_smiles_map   = {item["name"]: item.get("smiles") for item in drugs_for_prot if item.get("smiles")}

        # ── Bước 1: số protein ────────────────────────────────────────
        st.markdown(
            '<div style="font-size:0.78rem;font-weight:700;color:var(--muted);'
            'text-transform:uppercase;letter-spacing:0.06em;margin-bottom:0.3rem">'
            '🔢 Bước 1 — Chọn số lượng Protein muốn so sánh (tối đa 5)</div>',
            unsafe_allow_html=True,
        )
        n_proteins = int(st.number_input(
            "Số protein", min_value=1, max_value=5, value=1, step=1,
            key="n_proteins_prot",
            help="Nhập 1–5. Mỗi protein sẽ có màu dây nối riêng.",
            label_visibility="collapsed",
        ))

        # ── Bước 2: chọn từng protein ─────────────────────────────────
        st.markdown(
            '<div style="font-size:0.78rem;font-weight:700;color:var(--muted);'
            'text-transform:uppercase;letter-spacing:0.06em;margin:0.6rem 0 0.3rem 0">'
            '🧬 Bước 2 — Chọn tên từng Protein</div>',
            unsafe_allow_html=True,
        )
        prot_sel_cols     = st.columns(n_proteins)
        selected_proteins: list[str] = []
        for i, col in enumerate(prot_sel_cols):
            c = _DRUG_COLORS[i % len(_DRUG_COLORS)]
            col.markdown(
                f'<div style="height:4px;background:{c};border-radius:4px;margin-bottom:4px"></div>',
                unsafe_allow_html=True,
            )
            default_idx = min(i, len(protein_name_list) - 1) if protein_name_list else 0
            nm = col.selectbox(
                f"🧬 Protein {i + 1}",
                options=protein_name_list,
                index=default_idx,
                key=f"prot_prot_{i}",
            )
            selected_proteins.append(nm)

        # ── Bước 3: thông số + submit ─────────────────────────────────
        st.markdown(
            '<div style="font-size:0.78rem;font-weight:700;color:var(--muted);'
            'text-transform:uppercase;letter-spacing:0.06em;margin:0.6rem 0 0.3rem 0">'
            '⚙️ Bước 3 — Cấu hình tra cứu</div>',
            unsafe_allow_html=True,
        )
        with st.form("form_protein"):
            fc1, fc2, fc3 = st.columns([2, 2, 2])
            dataset       = fc1.selectbox("📊 Dataset", DATASET_OPTIONS, index=0, key="ds_protein")
            top_k         = fc2.slider("🔢 Giới hạn kết quả", min_value=1, max_value=50, value=10, step=1, key="topk_protein")
            show_sequence = fc3.checkbox("🔤 Hiển thị chuỗi Protein", value=False, key="show_protein_sequence")
            submitted_c   = st.form_submit_button("🔍 Tra cứu ngay", use_container_width=True)

        if submitted_c:
            unique_proteins = list(dict.fromkeys(p for p in selected_proteins if p))
            if not unique_proteins:
                st.warning("⚠️ Vui lòng chọn ít nhất một Protein.")
            else:
                with st.spinner(f"🔎 Đang tra cứu {len(unique_proteins)} protein..."):
                    pr: dict[str, dict] = {}
                    errors_c: list[str] = []
                    for pname in unique_proteins:
                        prow = protein_info_map.get(pname)
                        if prow is None:
                            errors_c.append(f"{pname}: không tìm thấy")
                            continue
                        try:
                            data = client.get_protein_links(protein_id=int(prow["id"]))
                            pr[pname] = data
                        except Exception as exc:  # noqa: BLE001
                            errors_c.append(f"{pname}: {exc}")
                    if errors_c:
                        st.error("❌ Lỗi tra cứu: " + "; ".join(errors_c))
                    st.session_state["protein_results"]  = pr
                    st.session_state["protein_selected"] = unique_proteins
                    st.session_state["show_prot_seq"]    = show_sequence
                    st.session_state.pop("history_rows", None)

        # ── Kết quả ───────────────────────────────────────────────────
        pr_stored: dict | None  = st.session_state.get("protein_results")
        sel_p_stored: list[str] = st.session_state.get("protein_selected", [])
        show_seq: bool          = st.session_state.get("show_prot_seq", False)

        if pr_stored is not None and sel_p_stored:
            total_drugs_p    = len({r["name"] for pdata in pr_stored.values() for r in pdata.get("drugs", [])})
            total_diseases_p = len({r["name"] for pdata in pr_stored.values() for r in pdata.get("diseases", [])})
            st.markdown(
                f'<div style="font-size:0.82rem;color:var(--muted);margin:0.6rem 0 0.2rem 0">'
                f'🔎 Từ <strong>{len(sel_p_stored)}</strong> protein · '
                f'<strong>{total_drugs_p}</strong> thuốc · '
                f'<strong>{total_diseases_p}</strong> bệnh liên quan</div>',
                unsafe_allow_html=True,
            )

            # Sequence expander
            if show_seq:
                for pname in sel_p_stored:
                    seq = pr_stored.get(pname, {}).get("sequence", "")
                    if seq:
                        with st.expander(f"🔤 Chuỗi Protein: {pr_stored[pname].get('accession', pname)}"):
                            st.code(seq, language=None)

            # ── Drug network ───────────────────────────────────────────
            st.markdown(
                '<div style="font-size:0.78rem;font-weight:700;color:var(--muted);'
                'text-transform:uppercase;letter-spacing:0.06em;margin:0.8rem 0 0.3rem 0">'
                '💊 Sơ đồ kết nối Protein → Thuốc</div>',
                unsafe_allow_html=True,
            )
            drug_net = _build_protein_network_html(sel_p_stored, pr_stored, "drugs", top_k)
            st.markdown(drug_net, unsafe_allow_html=True)

            # ── Disease network ────────────────────────────────────────
            st.markdown(
                '<div style="font-size:0.78rem;font-weight:700;color:var(--muted);'
                'text-transform:uppercase;letter-spacing:0.06em;margin:0.8rem 0 0.3rem 0">'
                '🦠 Sơ đồ kết nối Protein → Bệnh</div>',
                unsafe_allow_html=True,
            )
            dis_net = _build_protein_network_html(sel_p_stored, pr_stored, "diseases", top_k)
            st.markdown(dis_net, unsafe_allow_html=True)

            # ── Chemical structures of linked drugs ────────────────────
            linked_drug_names = list(dict.fromkeys(
                r["name"]
                for pdata in pr_stored.values()
                for r in pdata.get("drugs", [])
                if drug_smiles_map.get(r["name"])
            ))
            if linked_drug_names:
                st.markdown(
                    "<hr style='border:none;border-top:1px solid var(--border);margin:1.2rem 0 0.8rem 0'>",
                    unsafe_allow_html=True,
                )
                st.markdown(
                    '<div class="mol-section-title">🧪 Cấu trúc phân tử các thuốc liên kết</div>',
                    unsafe_allow_html=True,
                )
                n_per_row  = min(len(linked_drug_names), 4)
                mol_cols_p = st.columns(n_per_row)
                for i, dname in enumerate(linked_drug_names[:top_k]):
                    smiles = drug_smiles_map.get(dname)
                    with mol_cols_p[i % n_per_row]:
                        st.markdown(
                            f'<div style="font-size:0.72rem;font-weight:700;color:var(--primary);'
                            f'margin-bottom:4px">💊 {dname}</div>',
                            unsafe_allow_html=True,
                        )
                        img_bytes = _render_molecule_preview(smiles, dname)
                        _render_molecule_download(img_bytes, dname)

            # ── Legend ─────────────────────────────────────────────────
            st.markdown(
                "<hr style='border:none;border-top:1px solid var(--border);margin:1rem 0 0.6rem 0'>",
                unsafe_allow_html=True,
            )
            legend_dots_p = "".join(
                f'<span style="display:inline-flex;align-items:center;gap:5px;margin-right:1rem">'
                f'<span style="display:inline-block;width:12px;height:12px;border-radius:50%;'
                f'background:{_DRUG_COLORS[i % len(_DRUG_COLORS)]}"></span>'
                f'<span style="font-size:0.82rem;color:var(--text);font-weight:600">'
                f'{pr_stored.get(pn, {}).get("accession", pn)}</span>'
                f'</span>'
                for i, pn in enumerate(sel_p_stored)
            )
            st.markdown(
                f'<div class="info-box">'
                f'<div style="font-weight:700;margin-bottom:0.4rem">📝 Chú thích màu sắc dây nối</div>'
                f'<div style="display:flex;flex-wrap:wrap;gap:0.2rem">{legend_dots_p}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                '<div class="warn-box" style="margin-top:0.8rem">👆 Chọn Protein và nhấn '
                '<strong>Tra cứu ngay</strong> để xem sơ đồ liên kết thuốc và bệnh.</div>',
                unsafe_allow_html=True,
            )
        card_close()

    # ── Tab D: History ─────────────────────────────────────────────────
    with tab_d:
        card_open("Lịch sử tra cứu của bạn", "📋")
        col_refresh, col_info = st.columns([1, 4])
        with col_refresh:
            if st.button("🔄 Tải lại", use_container_width=True):
                st.session_state.pop("history_rows", None)
        with col_info:
            st.markdown(
                '<div class="info-box" style="font-size:0.83rem">'
                '📋 Hiển thị tối đa 200 bản ghi gần nhất.</div>',
                unsafe_allow_html=True,
            )
        if st.session_state.get("history_rows") is None:
            try:
                st.session_state["history_rows"] = client.history()
            except Exception as exc:  # noqa: BLE001
                st.error(f"Không tải được lịch sử: {exc}")
                st.session_state["history_rows"] = []
        show_history_table(st.session_state.get("history_rows", []))
        card_close()

