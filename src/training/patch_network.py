"""
Patch v3: Sửa 2 vấn đề trong render_network_page:
1. Score 1.0 "ảo": chú thích rõ "Đã xác nhận" thay vì hiển thị score=1.0
   → Đổi tên hiển thị trong tooltip và bỏ score trên cạnh known-link
2. Protein edges không hiện: vì drug_protein_links chứa drug_id không thuộc
   5 thuốc đang chọn (range lệch nhau).
   → Tự động thêm node mới (thuốc/bệnh/protein) khi có liên kết protein
"""

from pathlib import Path
_THIS_DIR = Path(__file__).resolve().parent      # src/training/
_PROJECT_ROOT = _THIS_DIR.parent.parent          # model_GNN_new/
FPATH = str(_PROJECT_ROOT / "src" / "frontend" / "app_modern.py")

with open(FPATH, "rb") as f:
    raw = f.read()

# ──────────────────────────────────────────────────────────────────────────────
# FIX 1: Score 1.0 trên known-link edges (Thuốc-Bệnh đã xác nhận)
# Thay: title="Thuốc–Bệnh · Đã xác nhận"  + không có score label
# Thêm: score thực tế vào title
# ──────────────────────────────────────────────────────────────────────────────
OLD_KNOWN_EDGE = (
    b"            net.add_edge(\r\n"
    b"                d_node, dis_node,\r\n"
    b"                value=score,\r\n"
    b"                color={\"color\": \"#00ccff\", \"highlight\": \"#00f5d4\", \"hover\": \"#00f5d4\"},\r\n"
    b"                title=f\"Thu\xe1\xbb\x91c\xe2\x80\x93B\xe1\xbb\x87nh \xc2\xb7 \xc4\x90\xc3\xa3 x\xc3\xa1c nh\xe1\xba\xadn\",\r\n"
    b"                width=2,\r\n"
    b"                arrows=\"to\",\r\n"
    b"            )\r\n"
    b"            verified_dd_pairs.add((d_name, dis_name))\r\n"
    b"            edge_count += 1"
)
NEW_KNOWN_EDGE = (
    b"            net.add_edge(\r\n"
    b"                d_node, dis_node,\r\n"
    b"                value=score,\r\n"
    b"                color={\"color\": \"#00ccff\", \"highlight\": \"#00f5d4\", \"hover\": \"#00f5d4\"},\r\n"
    b"                title=f\"\\u2705 Thu\xe1\xbb\x91c\\u2013B\xe1\xbb\x87nh \xc2\xb7 \xc4\x90\xc3\xa3 x\xc3\xa1c nh\xe1\xba\xadn<br>Score: {score:.3f}\",\r\n"
    b"                width=max(1.5, score * 2.5),\r\n"
    b"                arrows=\"to\",\r\n"
    b"            )\r\n"
    b"            verified_dd_pairs.add((d_name, dis_name))\r\n"
    b"            edge_count += 1"
)
if OLD_KNOWN_EDGE in raw:
    raw = raw.replace(OLD_KNOWN_EDGE, NEW_KNOWN_EDGE, 1)
    print("Fix 1 applied: known-link tooltip now shows real score")
else:
    print("Fix 1 NOT FOUND")

# ──────────────────────────────────────────────────────────────────────────────
# FIX 2: Protein edges – thêm node mới nếu drug/bệnh liên kết protein chưa có
# Thay toàn bộ block "# Thuốc–Protein edges" và "# Bệnh–Protein edges"
# ──────────────────────────────────────────────────────────────────────────────
OLD_PROT_BLOCK = (
    b"    # Thu\xe1\xbb\x91c\xe2\x80\x93Protein edges\r\n"
    b"    dp_links = _load_links_json(\"drug_protein_links.json\")\r\n"
    b"    for link in dp_links:\r\n"
    b"        d_name = drug_id_map.get(link.get(\"drug_id\"), \"\")\r\n"
    b"        p_name = protein_id_map.get(link.get(\"protein_id\"), \"\")\r\n"
    b"        if d_name in drug_set and p_name in protein_set:\r\n"
    b"            d_node = drug_name_to_idx[d_name]\r\n"
    b"            p_node = protein_name_to_idx[p_name]\r\n"
    b"            net.add_edge(\r\n"
    b"                d_node, p_node,\r\n"
    b"                color={\"color\": \"#9966ff\", \"highlight\": \"#cc99ff\", \"hover\": \"#cc99ff\"},\r\n"
    b"                title=f\"Thu\xe1\xbb\x91c\xe2\x80\x93Protein \xc2\xb7 T\xc6\xb0\xc6\xa1ng t\xc3\xa1c th\xe1\xbb\xb1c\",\r\n"
    b"                width=2,\r\n"
    b"                dashes=True,\r\n"
    b"            )\r\n"
    b"            edge_count += 1\r\n"
    b"\r\n"
    b"    # B\xe1\xbb\x87nh\xe2\x80\x93Protein edges\r\n"
    b"    dis_p_links = _load_links_json(\"protein_disease_links.json\")\r\n"
    b"    for link in dis_p_links:\r\n"
    b"        dis_name = disease_id_map.get(link.get(\"disease_id\"), \"\")\r\n"
    b"        p_name = protein_id_map.get(link.get(\"protein_id\"), \"\")\r\n"
    b"        if dis_name in disease_set and p_name in protein_set:\r\n"
    b"            dis_node = disease_name_to_idx[dis_name]\r\n"
    b"            p_node = protein_name_to_idx[p_name]\r\n"
    b"            net.add_edge(\r\n"
    b"                dis_node, p_node,\r\n"
    b"                color={\"color\": \"#ff9900\", \"highlight\": \"#ffcc33\", \"hover\": \"#ffcc33\"},\r\n"
    b"                title=f\"B\xe1\xbb\x87nh\xe2\x80\x93Protein \xc2\xb7 Li\xc3\xaan quan th\xe1\xbb\xb1c\",\r\n"
    b"                width=2,\r\n"
    b"                dashes=True,\r\n"
    b"            )\r\n"
    b"            edge_count += 1\r\n"
    b"\r\n"
    b"    # N\xe1\xba\xbfu kh\xc3\xb4ng t\xc3\xacm th\xe1\xba\xa5y li\xc3\xaan k\xe1\xba\xbft th\xe1\xbb\xb1c n\xc3\xa0o (do node \xc4\x91\xc3\xa3 ch\xe1\xbb\x8dn ch\xc6\xb0a c\xc3\xb3 link),\r\n"
    b"    # hi\xe1\xbb\x83n th\xe1\xbb\x8b th\xc3\xb4ng b\xc3\xa1o\r\n"
    b"    if edge_count == 0:\r\n"
    b"        st.info(\"\xe2\x84\xb9\xef\xb8\x8f Kh\xc3\xb4ng t\xc3\xacm th\xe1\xba\xa5y li\xc3\xaan k\xe1\xba\xbft th\xe1\xbb\xb1c gi\xe1\xbb\xafa c\xc3\xa1c node \xc4\x91\xc3\xa3 ch\xe1\xbb\x8dn trong dataset n\xc3\xa0y. \"\r\n"
    b"                \"\xc3\x97 th\xe1\xba\xbb ch\xe1\xbb\x8dn c\xc3\xa1c thu\xe1\xbb\x91c/b\xe1\xbb\x87nh/protein kh\xc3\xa1c.\")"
)

NEW_PROT_BLOCK = (
    b"    # \xe2\x94\x80\xe2\x94\x80 Thu\xe1\xbb\x91c\xe2\x80\x93Protein edges: t\xe1\xbb\xb1 \xc4\x91\xe1\xbb\x99ng th\xc3\xaam node n\xe1\xba\xbfu c\xe1\xba\xa7n \xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\r\n"
    b"    # Gi\xe1\xbb\x9bi h\xe1\xba\xa1n: ch\xe1\xbb\x89 th\xc3\xaam node m\xe1\xbb\x9bi khi protein \xc4\x91\xc3\xa3 c\xc3\xb3 trong graph (ph\xe1\xba\xa3i \xc4\x91\xc6\xb0\xe1\xbb\xa3c ch\xe1\xbb\x8dn),\r\n"
    b"    # nh\xc6\xb0ng thu\xe1\xbb\x91c/b\xe1\xbb\x87nh c\xc3\xb3 li\xc3\xaan k\xe1\xba\xbft protein c\xc3\xb3 th\xe1\xbb\x83 t\xe1\xbb\xb1 \xc4\x91\xe1\xbb\x99ng \xc4\x91\xc6\xb0\xe1\xbb\xa3c th\xc3\xaam\r\n"
    b"    _MAX_PROT_NODES = 10\r\n"
    b"    _prot_added = 0\r\n"
    b"\r\n"
    b"    dp_links = _load_links_json(\"drug_protein_links.json\")\r\n"
    b"    for link in dp_links:\r\n"
    b"        d_id = link.get(\"drug_id\")\r\n"
    b"        p_id = link.get(\"protein_id\")\r\n"
    b"        d_name = drug_id_map.get(d_id, \"\")\r\n"
    b"        p_name = protein_id_map.get(p_id, \"\")\r\n"
    b"        if not d_name or not p_name:\r\n"
    b"            continue\r\n"
    b"        # Ch\xe1\xbb\x89 x\xe1\xbb\xad l\xc3\xbd n\xe1\xba\xbfu thu\xe1\xbb\x91c \xc4\x91\xc3\xa3 c\xc3\xb3 trong graph\r\n"
    b"        if d_name not in drug_name_to_idx:\r\n"
    b"            continue\r\n"
    b"        # T\xe1\xbb\xb1 \xc4\x91\xe1\xbb\x99ng th\xc3\xaam node protein n\xe1\xba\xbfu ch\xc6\xb0a c\xc3\xb3\r\n"
    b"        if p_name not in protein_name_to_idx:\r\n"
    b"            if _prot_added >= _MAX_PROT_NODES:\r\n"
    b"                continue\r\n"
    b"            new_pid = f\"AutoP_{_ai_node_counter}\"\r\n"
    b"            _ai_node_counter += 1\r\n"
    b"            _prot_added += 1\r\n"
    b"            net.add_node(\r\n"
    b"                n_id=new_pid,\r\n"
    b"                label=p_name,\r\n"
    b"                shape=\"triangle\",\r\n"
    b"                color={\r\n"
    b"                    \"background\": \"#00cc66\",\r\n"
    b"                    \"border\":     \"#00ffaa\",\r\n"
    b"                    \"highlight\":  {\"background\": \"#00dd77\", \"border\": \"#00f5d4\"},\r\n"
    b"                    \"hover\":      {\"background\": \"#00bb55\", \"border\": \"#00f5d4\"},\r\n"
    b"                },\r\n"
    b"                size=18,\r\n"
    b"                title=f\"\\U0001f9ec <b>Protein</b>: {p_name}<br>Li\\u00ean k\\u1ebft t\\u1ef1 \xc4\x91\xe1\xbb\x99ng th\\xeam\",\r\n"
    b"                font={\"color\": \"#86efac\", \"size\": 12},\r\n"
    b"                shadow=True,\r\n"
    b"            )\r\n"
    b"            protein_name_to_idx[p_name] = new_pid\r\n"
    b"        d_node = drug_name_to_idx[d_name]\r\n"
    b"        p_node = protein_name_to_idx[p_name]\r\n"
    b"        net.add_edge(\r\n"
    b"            d_node, p_node,\r\n"
    b"            color={\"color\": \"#9966ff\", \"highlight\": \"#cc99ff\", \"hover\": \"#cc99ff\"},\r\n"
    b"            title=f\"\\U0001f9ec Thu\xe1\xbb\x91c\xe2\x80\x93Protein \xc2\xb7 T\xc6\xb0\xc6\xa1ng t\xc3\xa1c th\xe1\xbb\xb1c<br>{d_name} \\u2192 {p_name}\",\r\n"
    b"            width=1.5,\r\n"
    b"            dashes=True,\r\n"
    b"        )\r\n"
    b"        edge_count += 1\r\n"
    b"\r\n"
    b"    # B\xe1\xbb\x87nh\xe2\x80\x93Protein edges\r\n"
    b"    dis_p_links = _load_links_json(\"protein_disease_links.json\")\r\n"
    b"    for link in dis_p_links:\r\n"
    b"        dis_id = link.get(\"disease_id\")\r\n"
    b"        p_id = link.get(\"protein_id\")\r\n"
    b"        dis_name = disease_id_map.get(dis_id, \"\")\r\n"
    b"        p_name = protein_id_map.get(p_id, \"\")\r\n"
    b"        if not dis_name or not p_name:\r\n"
    b"            continue\r\n"
    b"        # Ch\xe1\xbb\x89 x\xe1\xbb\xad l\xc3\xbd n\xe1\xba\xbfu b\xe1\xbb\x87nh \xc4\x91\xc3\xa3 c\xc3\xb3 trong graph\r\n"
    b"        if dis_name not in disease_name_to_idx:\r\n"
    b"            continue\r\n"
    b"        # T\xe1\xbb\xb1 \xc4\x91\xe1\xbb\x99ng th\xc3\xaam node protein n\xe1\xba\xbfu ch\xc6\xb0a c\xc3\xb3\r\n"
    b"        if p_name not in protein_name_to_idx:\r\n"
    b"            if _prot_added >= _MAX_PROT_NODES:\r\n"
    b"                continue\r\n"
    b"            new_pid = f\"AutoP_{_ai_node_counter}\"\r\n"
    b"            _ai_node_counter += 1\r\n"
    b"            _prot_added += 1\r\n"
    b"            net.add_node(\r\n"
    b"                n_id=new_pid,\r\n"
    b"                label=p_name,\r\n"
    b"                shape=\"triangle\",\r\n"
    b"                color={\r\n"
    b"                    \"background\": \"#00cc66\",\r\n"
    b"                    \"border\":     \"#00ffaa\",\r\n"
    b"                    \"highlight\":  {\"background\": \"#00dd77\", \"border\": \"#00f5d4\"},\r\n"
    b"                    \"hover\":      {\"background\": \"#00bb55\", \"border\": \"#00f5d4\"},\r\n"
    b"                },\r\n"
    b"                size=18,\r\n"
    b"                title=f\"\\U0001f9ec <b>Protein</b>: {p_name}<br>Li\\u00ean k\\u1ebft t\\u1ef1 \xc4\x91\xe1\xbb\x99ng th\\xeam\",\r\n"
    b"                font={\"color\": \"#86efac\", \"size\": 12},\r\n"
    b"                shadow=True,\r\n"
    b"            )\r\n"
    b"            protein_name_to_idx[p_name] = new_pid\r\n"
    b"        dis_node = disease_name_to_idx[dis_name]\r\n"
    b"        p_node = protein_name_to_idx[p_name]\r\n"
    b"        net.add_edge(\r\n"
    b"            dis_node, p_node,\r\n"
    b"            color={\"color\": \"#ff9900\", \"highlight\": \"#ffcc33\", \"hover\": \"#ffcc33\"},\r\n"
    b"            title=f\"\\U0001f9ec B\xe1\xbb\x87nh\xe2\x80\x93Protein \xc2\xb7 Li\xc3\xaan quan th\xe1\xbb\xb1c<br>{dis_name} \\u2192 {p_name}\",\r\n"
    b"            width=1.5,\r\n"
    b"            dashes=True,\r\n"
    b"        )\r\n"
    b"        edge_count += 1\r\n"
    b"\r\n"
    b"    if edge_count == 0 and not net_ai_predict:\r\n"
    b"        st.info(\"\xe2\x84\xb9\xef\xb8\x8f Kh\xc3\xb4ng t\xc3\xacm th\xe1\xba\xa5y li\xc3\xaan k\xe1\xba\xbft n\xc3\xa0o gi\xe1\xbb\xafa c\xc3\xa1c node \xc4\x91\xc3\xa3 ch\xe1\xbb\x8dn. \"\r\n"
    b"                \"\xc3\x97 th\xe1\xba\xbb ch\xe1\xbb\x8dn c\xc3\xa1c thu\xe1\xbb\x91c/b\xe1\xbb\x87nh/protein kh\xc3\xa1c, ho\xe1\xba\xb7c b\xe1\xba\xadt d\xe1\xbb\xb1 \xc4\x91o\xc3\xa1n AI.\")"
)

if OLD_PROT_BLOCK in raw:
    raw = raw.replace(OLD_PROT_BLOCK, NEW_PROT_BLOCK, 1)
    print("Fix 2 applied: protein edges now auto-add nodes")
else:
    print("Fix 2 NOT FOUND - check raw bytes")
    # Debug
    idx = raw.find(b"# Thu\xe1\xbb\x91c\xe2\x80\x93Protein edges")
    if idx >= 0:
        print(f"Found protein block at offset {idx}")
        print(repr(raw[idx:idx+200]))
    else:
        print("PROTEIN BLOCK HEADER NOT FOUND")

with open(FPATH, "wb") as f:
    f.write(raw)

print("Done.")
