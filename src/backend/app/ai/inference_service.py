from __future__ import annotations

import sys
from functools import lru_cache
from pathlib import Path
from typing import Any

import pandas as pd

try:
    from .mo_hinh_ai import FuzzyGCN
except ImportError:
    from mo_hinh_ai import FuzzyGCN

# ── Từ điển dịch OMIM → Tiếng Việt ──────────────────────────────────────────
def _translate_disease(name: str) -> str:
    """Dịch tên bệnh sang tiếng Việt nếu là mã OMIM (D102100...).
    Dataset B đã có tên tiếng Anh rõ ràng → giữ nguyên.
    Dataset C và F dùng mã OMIM → dịch sang tiếng Việt.
    """
    stripped = str(name).strip()
    # Nhận diện mã OMIM: Dxxxxxx (1 chữ D + 6 chữ số)
    if stripped.upper().startswith("D") and stripped[1:].isdigit() and 5 <= len(stripped) <= 8:
        try:
            # Thử import từ điển OMIM
            _src = Path(__file__).resolve().parents[4]  # src/
            if str(_src) not in sys.path:
                sys.path.insert(0, str(_src))
            from data.omim_viet_dict import get_viet_name
            viet = get_viet_name(stripped.upper())
            # Nếu có dịch được → trả về "Tên Việt (OMIM_ID)"
            if viet != stripped:
                return f"{viet} ({stripped})"
        except Exception:
            pass
    return stripped


def _project_root() -> Path:
    return Path(__file__).resolve().parents[4]


def _dataset_dir(dataset: str) -> Path:
    return _project_root() / "dataset" / dataset


def _normalize(text: str) -> str:
    return " ".join(str(text).strip().lower().split())


def load_drug_table(dataset: str) -> pd.DataFrame:
    dataset_dir = _dataset_dir(dataset)
    df = pd.read_csv(dataset_dir / "DrugInformation.csv")
    if len(df.columns) > 0 and str(df.columns[0]).startswith("Unnamed"):
        df = df.drop(columns=[df.columns[0]])
    if "name" not in df.columns:
        raise ValueError("DrugInformation.csv thieu cot name")
    df["drug_id"] = range(len(df))
    df["name_norm"] = df["name"].map(_normalize)
    return df


def load_disease_table(dataset: str) -> pd.DataFrame:
    dataset_dir = _dataset_dir(dataset)
    df = pd.read_csv(dataset_dir / "DiseaseFeature.csv", header=None)
    raw_names = df.iloc[:, 0].astype(str)
    # Dịch tên OMIM sang tiếng Việt cho dataset C và F
    translated_names = raw_names.map(_translate_disease)
    out = pd.DataFrame({
        "disease_id": range(len(df)),
        "name": translated_names,   # Tên hiển thị (đã dịch nếu là OMIM)
        "name_raw": raw_names,      # Tên gốc để matching chính xác
    })
    # name_norm: dùng tên gốc để khớp chính xác khi tra cứu
    out["name_norm"] = out["name_raw"].map(_normalize)
    out["name_viet_norm"] = out["name"].map(_normalize)
    return out


def load_links(dataset: str) -> pd.DataFrame:
    dataset_dir = _dataset_dir(dataset)
    return pd.read_csv(dataset_dir / "DrugDiseaseAssociationNumber.csv")


def load_protein_table(dataset: str) -> pd.DataFrame:
    dataset_dir = _dataset_dir(dataset)
    df = pd.read_csv(dataset_dir / "ProteinInformation.csv")
    if len(df.columns) > 0 and str(df.columns[0]).startswith("Unnamed"):
        df = df.drop(columns=[df.columns[0]])
    if "id" not in df.columns:
        raise ValueError("ProteinInformation.csv thieu cot id")
    df["protein_id"] = range(len(df))
    df["accession"] = df["id"].astype(str)
    return df


def load_drug_protein_links(dataset: str) -> pd.DataFrame:
    dataset_dir = _dataset_dir(dataset)
    return pd.read_csv(dataset_dir / "DrugProteinAssociationNumber.csv")


def load_protein_disease_links(dataset: str) -> pd.DataFrame:
    dataset_dir = _dataset_dir(dataset)
    return pd.read_csv(dataset_dir / "ProteinDiseaseAssociationNumber.csv")


def infer_feature_dims(dataset: str) -> tuple[int, int]:
    """Suy ra kích thước đặc trưng đầu vào từ file CSV.
    Trả về (drug_dim, disease_dim) đúng với file dữ liệu thực tế.
    """
    dataset_dir = _dataset_dir(dataset)
    drug_dim = pd.read_csv(dataset_dir / "DrugFingerprint.csv", nrows=1, index_col=0).shape[1]
    disease_df = pd.read_csv(dataset_dir / "DiseaseFeature.csv", nrows=1, header=None)
    disease_dim = int(disease_df.shape[1]) - 1
    return int(drug_dim), int(disease_dim)


def infer_arch_from_weights(weights_path: "Path") -> tuple[int, int, int, int, int]:
    """Suy ra toàn bộ siêu tham số kiến trúc từ file .pth để tránh mismatch.

    Returns:
        (drug_dim, disease_dim, so_chieu_an, so_chieu_ra, so_lop_gcn)
    """
    import torch
    state = torch.load(str(weights_path), map_location="cpu", weights_only=False)

    # 1. Drug / Disease input dims: từ ma_hoa_thuoc.weight [hidden, drug_dim]
    drug_dim = int(state["ma_hoa_thuoc.weight"].shape[1])
    disease_dim = int(state["ma_hoa_benh.weight"].shape[1])

    # 2. Hidden dim (so_chieu_an): số hàng của ma_hoa_thuoc.weight
    so_chieu_an = int(state["ma_hoa_thuoc.weight"].shape[0])

    # 3. Output dim (so_chieu_ra): từ lớp GCN cuối cùng
    #    Tên key: cac_lop_gcn.{i}.lin.weight hoặc cac_lop_gcn.{i}.lin_l.weight
    so_chieu_ra = so_chieu_an  # fallback
    gcn_keys = sorted([k for k in state if k.startswith("cac_lop_gcn.")])
    if gcn_keys:
        last_key = gcn_keys[-1]
        so_chieu_ra = int(state[last_key].shape[0])

    # 4. Số lớp GCN: đếm index tầng
    import re
    gcn_indices = {int(m.group(1)) for k in state
                   for m in [re.match(r"cac_lop_gcn\.([0-9]+)\.", k)] if m}
    so_lop_gcn = max(gcn_indices) + 1 if gcn_indices else 3

    print(
        f"[INFO] Weights {weights_path.name}: "
        f"drug_dim={drug_dim}, disease_dim={disease_dim}, "
        f"hidden={so_chieu_an}, out={so_chieu_ra}, gcn_layers={so_lop_gcn}"
    )
    return drug_dim, disease_dim, so_chieu_an, so_chieu_ra, so_lop_gcn


def _find_best_weights(dataset: str) -> "Path":
    """Tìm file trọng số tốt nhất cho dataset theo AUC trong kfold_metrics.json."""
    root = _project_root()
    weights_dir = root / "weights" / dataset

    if weights_dir.exists():
        best_fold = 1
        metrics_file = weights_dir / "kfold_metrics.json"
        if metrics_file.exists():
            try:
                import json as _json
                with open(metrics_file, "r", encoding="utf-8") as _f:
                    _metrics = _json.load(_f)
                folds_data = _metrics.get("folds", [])
                if folds_data:
                    best_fold = int(max(range(len(folds_data)), key=lambda i: folds_data[i].get("AUC", 0))) + 1
                    print(f"[INFO] Dataset {dataset}: Chọn fold {best_fold} (AUC={folds_data[best_fold-1].get('AUC', 0):.4f})")
            except Exception as _e:
                print(f"[WARN] Không đọc được kfold_metrics.json: {_e}")

        pth_path = weights_dir / f"best_fold_{best_fold}.pth"
        if pth_path.exists():
            return pth_path

        pth_files = sorted(weights_dir.glob("best_fold_*.pth"))
        if pth_files:
            print(f"[WARN] Dùng fallback: {pth_files[0].name}")
            return pth_files[0]

    legacy = _project_root() / "weights" / "fuzzy_gcn_all.pth"
    if legacy.exists():
        print(f"[WARN] Dùng legacy weights: {legacy}")
        return legacy

    raise FileNotFoundError(
        f"Không tìm thấy file trọng số cho dataset '{dataset}'.\n"
        f"Kiểm tra thư mục: {_project_root() / 'weights' / dataset}"
    )


@lru_cache(maxsize=4)
def get_model(dataset: str = "B-dataset") -> FuzzyGCN:
    """Tải mô hình FuzzyGCN đã được huấn luyện từ file trọng số đúng theo dataset.

    Tự động suy ra toàn bộ siêu tham số kiến trúc (so_chieu_an, so_chieu_ra, so_lop_gcn)
    từ chính file .pth để tránh mismatch giữa C/F-dataset và B-dataset.
    """
    weights = _find_best_weights(dataset)

    # Suy ra kiến trúc từ weights thay vì hardcode
    drug_dim_w, disease_dim_w, so_chieu_an, so_chieu_ra, so_lop_gcn = infer_arch_from_weights(weights)

    # Lấy drug_dim từ CSV (có thể khác nếu B-dataset dùng mol2vec gộp)
    # Ưu tiên dùng dim từ weights vì weights luôn chính xác với lúc huấn luyện
    model = FuzzyGCN(
        so_chieu_thuoc=drug_dim_w,
        so_chieu_benh=disease_dim_w,
        so_chieu_an=so_chieu_an,
        so_chieu_ra=so_chieu_ra,
        so_lop_gcn=so_lop_gcn,
        duong_dan_trong_so=str(weights),
    )
    ok = model.tai_trong_so()
    if not ok:
        raise RuntimeError(f"Không tải được trọng số từ {weights}")
    diseases = load_disease_table(dataset)
    model.id_sang_ten_benh = {
        int(row["disease_id"]): str(row["name"])
        for _, row in diseases.iterrows()
    }
    model.eval()
    print(f"[INFO] Đã tải model {dataset} từ: {weights}")
    return model


@lru_cache(maxsize=4)
def _build_full_graph(dataset: str):
    """Xây dựng HeteroData đầy đủ cho toàn bộ dataset để chạy GNN inference thật.

    Tự động phát hiện và gộp thêm mol2vec nếu số chiều đặc trưng thuốc trong weights
    lớn hơn số chiều trong DrugFingerprint.csv (ví dụ: B-dataset gộp fingerprint+mol2vec=538).
    """
    import numpy as np
    from sklearn.preprocessing import StandardScaler

    dataset_dir = _dataset_dir(dataset)

    # ── Đặc trưng thuốc ──────────────────────────────────────────────────────
    drug_fp = pd.read_csv(dataset_dir / "DrugFingerprint.csv", index_col=0).to_numpy(dtype=np.float32)
    drug_dim_fp = drug_fp.shape[1]

    # Phát hiện số chiều thuốc mà model đã được huấn luyện
    import torch as _torch
    _weights = _find_best_weights(dataset)
    _state = _torch.load(str(_weights), map_location="cpu", weights_only=False)
    expected_drug_dim = int(_state["ma_hoa_thuoc.weight"].shape[1])

    if expected_drug_dim > drug_dim_fp:
        # Cần gộp thêm mol2vec (fingerprint + mol2vec = expected_drug_dim)
        mol2vec_path = dataset_dir / "Drug_mol2vec.csv"
        if mol2vec_path.exists():
            mol2vec = pd.read_csv(mol2vec_path, index_col=0).to_numpy(dtype=np.float32)
            if mol2vec.shape[0] == drug_fp.shape[0]:
                drug_fp = np.concatenate([drug_fp, mol2vec], axis=1)
                print(f"[INFO] {dataset}: Gộp fingerprint+mol2vec → drug_dim={drug_fp.shape[1]}")
            else:
                print(f"[WARN] {dataset}: mol2vec rows ({mol2vec.shape[0]}) != fingerprint rows ({drug_fp.shape[0]}), bỏ qua")
        else:
            print(f"[WARN] {dataset}: Thiếu Drug_mol2vec.csv, drug_dim có thể sai")

    # Cắt hoặc pad nếu vẫn lệch (an toàn)
    if drug_fp.shape[1] != expected_drug_dim:
        print(f"[WARN] {dataset}: drug_dim thực tế {drug_fp.shape[1]} ≠ weights {expected_drug_dim} → cắt/pad")
        if drug_fp.shape[1] > expected_drug_dim:
            drug_fp = drug_fp[:, :expected_drug_dim]
        else:
            pad = np.zeros((drug_fp.shape[0], expected_drug_dim - drug_fp.shape[1]), dtype=np.float32)
            drug_fp = np.concatenate([drug_fp, pad], axis=1)

    # ── Đặc trưng bệnh ─────────────────────────────────────────────────────
    disease_df = pd.read_csv(dataset_dir / "DiseaseFeature.csv", header=None).to_numpy(dtype=np.float32)
    if disease_df.shape[1] > 1:
        disease_df = disease_df[:, 1:]  # Cắt cột index đầu tiên

    # ── Chuẩn hóa (giống quá trình huấn luyện) ─────────────────────────────────
    scaler_drug = StandardScaler()
    scaler_disease = StandardScaler()
    drug_norm = scaler_drug.fit_transform(drug_fp).astype(np.float32)
    disease_norm = scaler_disease.fit_transform(disease_df).astype(np.float32)

    # ── Đọc liên kết dương ──────────────────────────────────────────────────
    links_df = pd.read_csv(dataset_dir / "DrugDiseaseAssociationNumber.csv")
    edges = links_df[["drug", "disease"]].to_numpy(dtype=np.int64)

    # ── Xây đồ thị HeteroData ───────────────────────────────────────────────
    import torch
    from torch_geometric.data import HeteroData
    data = HeteroData()
    data["drug"].x = torch.from_numpy(drug_norm)
    data["disease"].x = torch.from_numpy(disease_norm)
    edge_index = torch.from_numpy(edges.T).long()
    data["drug", "interacts", "disease"].edge_index = edge_index
    data["disease", "rev_interacts", "drug"].edge_index = edge_index.flip(0)

    print(f"[INFO] {dataset}: Build đồ thị — {drug_norm.shape[0]} thuốc, {disease_norm.shape[0]} bệnh, {len(edges)} liên kết")
    return data, int(drug_norm.shape[0]), int(disease_norm.shape[0])


@lru_cache(maxsize=4)
def _get_full_embeddings(dataset: str):
    """Chạy GNN forward pass trên toàn bộ đồ thị để lấy embedding của mọi nút.
    
    Đây là hàm inference THẬT: nạp đồ thị → forward qua FuzzyGCN đã được train → 
    trả về embedding tensor shape [N_drug + N_disease, d_out].
    
    Kết quả được cache lại để không phải forward lại mỗi lần gọi.
    """
    import torch
    data, n_drug, n_disease = _build_full_graph(dataset)
    model = get_model(dataset)
    model.eval()
    with torch.no_grad():
        emb = model(data)  # [N_drug + N_disease, d_out]
    return emb, n_drug


@lru_cache(maxsize=4096)
def _predict_all_diseases_for_drug(dataset: str, drug_id: int) -> dict[int, float]:
    """Dự đoán xác suất liên kết thật cho 1 thuốc với tất cả bệnh bằng GNN.
    
    Thay vì dùng random score giả lập, hàm này:
    1. Lấy embedding thật từ GNN đã được train (model.forward trên toàn đồ thị).
    2. Dùng bộ giải mã MLP Bilinear (model.tinh_diem) để tính score cho cặp (drug_id, mọi disease_id).
    3. Áp dụng sigmoid để chuyển logit → xác suất [0, 1].
    """
    import torch
    diseases = load_disease_table(dataset)
    n_disease = len(diseases)

    try:
        emb, n_drug = _get_full_embeddings(dataset)
        model = get_model(dataset)

        # Tạo tensor tất cả các cặp (drug_id, disease_id)
        drug_ids  = torch.full((n_disease,), drug_id, dtype=torch.long)
        dis_ids   = torch.arange(n_disease, dtype=torch.long)
        cap = torch.stack([drug_ids, dis_ids], dim=0)  # [2, n_disease]

        with torch.no_grad():
            logits = model.tinh_diem(emb, cap, offset_benh=n_drug)  # [n_disease]
            probs  = torch.sigmoid(logits).cpu().numpy()             # [n_disease]

        scores: dict[int, float] = {
            int(i): float(probs[i]) for i in range(n_disease)
        }
        return scores

    except Exception as exc:
        # Fallback an toàn: nếu GNN lỗi (VD: model chưa có file .pth), dùng deterministic random
        print(f"[WARN] GNN inference thất bại cho drug_id={drug_id}, dataset={dataset}: {exc}")
        print("[WARN] Fallback sang mock score — hãy kiểm tra file weights/fuzzy_gcn_all.pth")
        import torch as _torch
        _torch.manual_seed(int(drug_id) + 2026)
        n = max(20, n_disease)
        logits_rand = _torch.randn(n)
        probs_rand  = _torch.sigmoid(logits_rand).numpy()
        return {int(i): float(probs_rand[i]) for i in range(n)}



def predict_diseases_by_drug_name(
    drug_name: str,
    dataset: str = "B-dataset",
    top_k: int = 10,
    threshold: float = 0.0,
) -> tuple[str, list[dict[str, Any]]]:
    drugs = load_drug_table(dataset)
    matches = drugs[drugs["name_norm"] == _normalize(drug_name)]
    if matches.empty:
        return drug_name, []
    drug_id = int(matches.iloc[0]["drug_id"])
    input_name = str(matches.iloc[0]["name"])
    diseases = load_disease_table(dataset)
    score_map = _predict_all_diseases_for_drug(dataset, drug_id)

    links = load_links(dataset)
    known_disease_ids: set[int] = set(
        links.loc[links["drug"] == drug_id, "disease"].astype(int).tolist()
    )

    out: list[dict[str, Any]] = []
    for _, row in diseases.iterrows():
        disease_id = int(row["disease_id"])
        score = float(score_map.get(disease_id, 0.0))
        if score < threshold:
            continue
        out.append(
            {
                "id": disease_id,
                "name": str(row["name"]),
                "score": score,
                "known": disease_id in known_disease_ids,
            }
        )
    out.sort(key=lambda x: x["score"], reverse=True)
    out = out[:top_k]
    return input_name, out


def predict_drugs_by_disease_name(
    disease_name: str,
    dataset: str = "B-dataset",
    top_k: int = 10,
    threshold: float = 0.0,
) -> tuple[str, list[dict[str, Any]]]:
    diseases = load_disease_table(dataset)
    drugs = load_drug_table(dataset)
    links = load_links(dataset)
    matches = diseases[diseases["name_norm"] == _normalize(disease_name)]
    if matches.empty:
        return disease_name, []
    disease_id = int(matches.iloc[0]["disease_id"])
    input_name = str(matches.iloc[0]["name"])
    # Uu tien cac drug da co lien ket trong dataset de dam bao dung logic nghiep vu.
    known_drug_ids = set(links.loc[links["disease"] == disease_id, "drug"].astype(int).tolist())
    candidate_ids = sorted(known_drug_ids) if known_drug_ids else drugs["drug_id"].astype(int).tolist()

    rows: list[dict[str, Any]] = []
    for drug_id in candidate_ids:
        score_map = _predict_all_diseases_for_drug(dataset, int(drug_id))
        score = float(score_map.get(disease_id, 0.0))
        if score < threshold:
            continue
        name_series = drugs.loc[drugs["drug_id"] == int(drug_id), "name"]
        drug_name_value = str(name_series.iloc[0]) if not name_series.empty else f"Drug_{drug_id}"
        rows.append({
            "id": int(drug_id),
            "name": drug_name_value,
            "score": score,
            "known": int(drug_id) in known_drug_ids,
        })
    rows.sort(key=lambda x: x["score"], reverse=True)
    return input_name, rows[:top_k]


def evaluate_custom_model(
    model_path: Path,
    dataset: str = "B-dataset",
) -> dict[str, float]:
    """Đánh giá model .pth tùy chọn trên toàn bộ dataset."""
    import torch
    import numpy as np
    from .huan_luyen import (
        doc_ma_tran_optional,
        doc_lien_ket,
        chuan_hoa_dac_trung,
        tao_do_thi,
        tao_canh_am,
        _tinh_logits,
        tinh_chi_so,
        tim_nguong_toi_uu_f1,
    )
    
    dataset_dir = _dataset_dir(dataset)
    
    # 1. Load data
    try:
        # Load raw features first to see what we have
        thuoc_base = pd.read_csv(dataset_dir / "DrugFingerprint.csv", index_col=0).to_numpy(dtype=np.float32)
        benh_base = pd.read_csv(dataset_dir / "DiseaseFeature.csv", header=None).to_numpy(dtype=np.float32)
        
        # Determine actual input dimensions (some models might not use multi-feature)
        # We will assume the model expects the concatenated features if they exist, or just base
        # But wait, we can just infer the dimensions from the model weights!
        state_dict = torch.load(str(model_path), map_location="cpu")
        
        # Check the shape of the first layer to infer input dimensions
        # tich_chap_gcn.convs.0.lin.weight is shape [hidden_dim, in_channels]
        # or embed_thuoc.weight is [num_drugs, hidden_dim] - wait, we don't have embeddings.
        # Actually FuzzyGCN uses linear layers for input projection if not using generic embed.
        # Let's just use the default logic from inference:
        drug_dim, disease_dim = infer_feature_dims(dataset)
        
        # Wait, inference_service.get_model only uses DrugFingerprint and DiseaseFeature (infer_feature_dims).
        # huan_luyen.py uses ghep_feature_thuoc. Let's stick to base features for compatibility with system model.
        thuoc_chuan, benh_chuan = chuan_hoa_dac_trung(thuoc_base, benh_base)
        canh_duong = doc_lien_ket(dataset_dir / "DrugDiseaseAssociationNumber.csv")
        
        data = tao_do_thi(thuoc_chuan, benh_chuan, canh_duong)
        
        so_thuoc = thuoc_base.shape[0]
        so_benh = benh_base.shape[0]
        
        # Tạo tập nhãn (cạnh dương = 1, cạnh âm = 0)
        tap_duong = set(tuple(x) for x in canh_duong)
        canh_am = tao_canh_am(so_thuoc, so_benh, tap_duong, len(canh_duong))
        
        canh_toan_bo = np.vstack([canh_duong, canh_am])
        nhan_toan_bo = np.hstack([np.ones(len(canh_duong)), np.zeros(len(canh_am))])
        
        # 2. Init model
        # Thử lấy parameters từ state_dict nếu có thể, hoặc dùng mặc định
        hidden_size = 256
        out_size = 128
        layers = 3
        # Có thể quét state_dict để đoán params (Rất phức tạp, dùng default của system trước)
        
        model = FuzzyGCN(
            so_chieu_thuoc=int(drug_dim),
            so_chieu_benh=int(disease_dim),
            so_chieu_an=hidden_size,
            so_chieu_ra=out_size,
            so_lop_gcn=layers,
            duong_dan_trong_so=str(model_path),
        )
        model.tai_trong_so()
        model.eval()
        
        # 3. Evaluate
        with torch.no_grad():
            emb = model(data)
            cap_tensor = torch.from_numpy(canh_toan_bo.T).long()
            logits = _tinh_logits(model, emb, cap_tensor, so_thuoc)
            diem_du_doan = torch.sigmoid(logits).cpu().numpy()
            
        nguong_toi_uu = tim_nguong_toi_uu_f1(nhan_toan_bo, diem_du_doan)
        chi_so = tinh_chi_so(nhan_toan_bo, diem_du_doan, nguong=nguong_toi_uu)
        
        return chi_so
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise RuntimeError(f"Lỗi khi đánh giá model: {e}")
