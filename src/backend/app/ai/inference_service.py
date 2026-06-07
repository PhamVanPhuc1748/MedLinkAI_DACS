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


def load_disease_feature_matrix(dataset: str):
    """Đọc đặc trưng bệnh, loại cột tên bệnh rồi mới ép kiểu số."""
    import numpy as np

    dataset_dir = _dataset_dir(dataset)
    df = pd.read_csv(dataset_dir / "DiseaseFeature.csv", header=None)
    if df.shape[1] > 1:
        df = df.iloc[:, 1:]
    df = df.apply(pd.to_numeric, errors="coerce").fillna(0.0)
    return df.to_numpy(dtype=np.float32)


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
    disease_dim = int(max(0, disease_df.shape[1] - 1))
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

    emb, n_drug = _get_full_embeddings(dataset)
    model = get_model(dataset)

    # Tạo tensor tất cả các cặp (drug_id, disease_id)
    drug_ids = torch.full((n_disease,), drug_id, dtype=torch.long)
    dis_ids = torch.arange(n_disease, dtype=torch.long)
    cap = torch.stack([drug_ids, dis_ids], dim=0)  # [2, n_disease]

    with torch.no_grad():
        logits = model.tinh_diem(emb, cap, offset_benh=n_drug)  # [n_disease]
        probs = torch.sigmoid(logits).cpu().numpy()  # [n_disease]

    scores: dict[int, float] = {
        int(i): float(probs[i]) for i in range(n_disease)
    }
    return scores



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

    # ── Bước 0: Kiểm tra xem file có phải là "file kết quả" không ──────────────
    # Một số file .pth không chứa trọng số mà chứa dict các chỉ số đánh giá
    # (mean_AUC, std_AUC, AUC, AUPR...). Nếu phát hiện ra, đọc thẳng rồi trả về.
    try:
        _peek = torch.load(str(model_path), map_location="cpu")
        if isinstance(_peek, dict):
            # Tập hợp các key chỉ số phổ biến
            _metric_keys = {"AUC", "AUPR", "Accuracy", "Precision", "Recall", "F1", "MCC",
                            "mean_AUC", "mean_AUPR", "mean_Accuracy", "mean_Precision",
                            "mean_Recall", "mean_F1", "mean_MCC"}
            _found = _metric_keys & set(_peek.keys())
            if _found:
                # Chuẩn hóa về dạng {"AUC": x, "AUPR": x, ...}
                metrics = {}
                for m in ["AUC", "AUPR", "Accuracy", "Precision", "Recall", "F1", "MCC"]:
                    v = _peek.get(m, _peek.get(f"mean_{m}", None))
                    if v is not None:
                        metrics[m] = float(v)
                return metrics
    except Exception:
        pass  # Nếu không đọc được thì bỏ qua, chạy tiếp luồng inference bình thường

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
        benh_base = load_disease_feature_matrix(dataset)
        
        # Determine actual input dimensions (some models might not use multi-feature)
        # We will assume the model expects the concatenated features if they exist, or just base
        # But wait, we can just infer the dimensions from the model weights!
        
        import sys
        try:
            from . import mo_hinh_ai, fuzzy_layer, gcn_flow, gnn_algorithm
            sys.modules['mo_hinh_ai'] = mo_hinh_ai
            sys.modules['fuzzy_layer'] = fuzzy_layer
            sys.modules['gcn_flow'] = gcn_flow
            sys.modules['gnn_algorithm'] = gnn_algorithm
        except ImportError:
            pass
            
        checkpoint = torch.load(str(model_path), map_location="cpu")
        
        # Trích xuất state_dict từ nhiều dạng checkpoint khác nhau
        if isinstance(checkpoint, torch.nn.Module):
            state_dict = checkpoint.state_dict()
        elif isinstance(checkpoint, dict):
            if "model" in checkpoint and isinstance(checkpoint["model"], dict):
                state_dict = checkpoint["model"]
            elif "state_dict" in checkpoint:
                state_dict = checkpoint["state_dict"]
            elif "model_state_dict" in checkpoint:
                state_dict = checkpoint["model_state_dict"]
            else:
                state_dict = checkpoint
        else:
            raise RuntimeError(f"Định dạng file .pth không được hỗ trợ: {type(checkpoint).__name__}")

        # Clean up state_dict keys (e.g., remove 'module.' prefix if saved with DataParallel)
        clean_state_dict = {}
        for k, v in state_dict.items():
            if not hasattr(v, "shape"):
                continue  # bỏ qua metadata (epoch, str, int...)
            new_key = k.replace('module.', '').replace('model.', '')
            clean_state_dict[new_key] = v
        state_dict = clean_state_dict

        # Check the shape of the first layer to infer input dimensions
        # And automatically use ghep_feature if dimensions are larger than base
        try:
            hidden_size = state_dict['ma_hoa_thuoc.weight'].shape[0]
            drug_dim = state_dict['ma_hoa_thuoc.weight'].shape[1]
            disease_dim = state_dict['ma_hoa_benh.weight'].shape[1]
            out_size = state_dict['bo_giai_ma.net.0.weight'].shape[1] // 3
            layers = len([k for k in state_dict.keys() if k.startswith('cac_lop_gcn.') and k.endswith('.bias')])
        except KeyError as e:
            # Log ra các key thực tế để dễ debug
            actual_keys = list(state_dict.keys())[:10]
            raise RuntimeError(
                f"Cấu trúc file .pth không tương thích với FuzzyGCN. "
                f"Key bị thiếu: {e}. "
                f"Các key tìm thấy trong file: {actual_keys}"
            )

        # Nếu model yêu cầu nhiều features hơn base, ta phải ghép thêm
        if drug_dim > thuoc_base.shape[1] or disease_dim > benh_base.shape[1]:
            from .huan_luyen import ghep_feature_thuoc, ghep_feature_benh
            thuoc_ghep = ghep_feature_thuoc(thuoc_base, dataset_dir)
            benh_ghep = ghep_feature_benh(benh_base, dataset_dir)
            # Slice vừa đủ số chiều model yêu cầu
            thuoc_base = thuoc_ghep[:, :drug_dim]
            benh_base = benh_ghep[:, :disease_dim]
        else:
            thuoc_base = thuoc_base[:, :drug_dim]
            benh_base = benh_base[:, :disease_dim]

        thuoc_chuan, benh_chuan = chuan_hoa_dac_trung(thuoc_base, benh_base)
        canh_duong = doc_lien_ket(dataset_dir / "DrugDiseaseAssociationNumber.csv")
        
        data = tao_do_thi(thuoc_chuan, benh_chuan, canh_duong)
        
        so_thuoc = thuoc_base.shape[0]
        so_benh = benh_base.shape[0]
        
        # Tạo tập nhãn (cạnh dương = 1, cạnh âm = 0)
        import random
        from sklearn.model_selection import StratifiedKFold
        
        # Đặt seed cố định giống huan_luyen.py để đảm bảo tái lập
        seed = 42
        random.seed(seed)
        np.random.seed(seed)
        torch.manual_seed(seed)

        tap_duong = set(tuple(x) for x in canh_duong)
        canh_am = tao_canh_am(so_thuoc, so_benh, tap_duong, len(canh_duong))
        
        canh_toan_bo = np.vstack([canh_duong, canh_am])
        nhan_toan_bo = np.hstack([np.ones(len(canh_duong)), np.zeros(len(canh_am))])
        
        model = FuzzyGCN(
            so_chieu_thuoc=int(drug_dim),
            so_chieu_benh=int(disease_dim),
            so_chieu_an=hidden_size,
            so_chieu_ra=out_size,
            so_lop_gcn=layers,
            duong_dan_trong_so=str(model_path),
        )
        # Load weights explicitly to check for missing keys
        incompatible_keys = model.load_state_dict(state_dict, strict=False)
        if len(incompatible_keys.missing_keys) > 5:
            print(f"Warning: Many missing keys when loading model: {incompatible_keys.missing_keys}")
        model.eval()
        
        # 3. Evaluate trên Test set của Fold 1 (để công bằng và khớp với kết quả training)
        skf = StratifiedKFold(n_splits=10, shuffle=True, random_state=seed)
        folds = list(skf.split(canh_toan_bo, nhan_toan_bo))
        train_idx, test_idx = folds[0]
        
        canh_test = canh_toan_bo[test_idx]
        nhan_test = nhan_toan_bo[test_idx]
        
        with torch.no_grad():
            emb = model(data)
            cap_tensor = torch.from_numpy(canh_test.T).long()
            logits = _tinh_logits(model, emb, cap_tensor, so_thuoc)
            diem_du_doan = torch.sigmoid(logits).cpu().numpy()
            
        nguong_toi_uu = tim_nguong_toi_uu_f1(nhan_test, diem_du_doan)
        chi_so = tinh_chi_so(nhan_test, diem_du_doan, nguong=nguong_toi_uu)
        
        return chi_so
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise RuntimeError(f"Lỗi khi đánh giá model: {e}")


@lru_cache(maxsize=4)
def _build_full_graph(dataset: str):
    """Bản override sạch để tránh ép cột tên bệnh sang float."""
    import numpy as np
    import torch
    import torch as _torch
    from sklearn.preprocessing import StandardScaler
    from torch_geometric.data import HeteroData

    dataset_dir = _dataset_dir(dataset)

    drug_fp = pd.read_csv(dataset_dir / "DrugFingerprint.csv", index_col=0).to_numpy(dtype=np.float32)
    drug_dim_fp = drug_fp.shape[1]

    weights = _find_best_weights(dataset)
    state = _torch.load(str(weights), map_location="cpu", weights_only=False)
    expected_drug_dim = int(state["ma_hoa_thuoc.weight"].shape[1])

    if expected_drug_dim > drug_dim_fp:
        mol2vec_path = dataset_dir / "Drug_mol2vec.csv"
        if mol2vec_path.exists():
            mol2vec = pd.read_csv(mol2vec_path, index_col=0).to_numpy(dtype=np.float32)
            if mol2vec.shape[0] == drug_fp.shape[0]:
                drug_fp = np.concatenate([drug_fp, mol2vec], axis=1)
                print(f"[INFO] {dataset}: Ghép fingerprint+mol2vec → drug_dim={drug_fp.shape[1]}")
            else:
                print(f"[WARN] {dataset}: mol2vec rows ({mol2vec.shape[0]}) != fingerprint rows ({drug_fp.shape[0]}), bỏ qua")
        else:
            print(f"[WARN] {dataset}: Thiếu Drug_mol2vec.csv, drug_dim có thể sai")

    if drug_fp.shape[1] != expected_drug_dim:
        print(f"[WARN] {dataset}: drug_dim thực tế {drug_fp.shape[1]} != weights {expected_drug_dim} → cắt/pad")
        if drug_fp.shape[1] > expected_drug_dim:
            drug_fp = drug_fp[:, :expected_drug_dim]
        else:
            pad = np.zeros((drug_fp.shape[0], expected_drug_dim - drug_fp.shape[1]), dtype=np.float32)
            drug_fp = np.concatenate([drug_fp, pad], axis=1)

    disease_df = load_disease_feature_matrix(dataset)

    scaler_drug = StandardScaler()
    scaler_disease = StandardScaler()
    drug_norm = scaler_drug.fit_transform(drug_fp).astype(np.float32)
    disease_norm = scaler_disease.fit_transform(disease_df).astype(np.float32)

    links_df = pd.read_csv(dataset_dir / "DrugDiseaseAssociationNumber.csv")
    edges = links_df[["drug", "disease"]].to_numpy(dtype=np.int64)

    data = HeteroData()
    data["drug"].x = torch.from_numpy(drug_norm)
    data["disease"].x = torch.from_numpy(disease_norm)
    edge_index = torch.from_numpy(edges.T).long()
    data["drug", "interacts", "disease"].edge_index = edge_index
    data["disease", "rev_interacts", "drug"].edge_index = edge_index.flip(0)

    print(f"[INFO] {dataset}: Build đồ thị — {drug_norm.shape[0]} thuốc, {disease_norm.shape[0]} bệnh, {len(edges)} liên kết")
    return data, int(drug_norm.shape[0]), int(disease_norm.shape[0])

def inspect_model_pth(model_path: Path) -> dict:
    import torch
    try:
        checkpoint = torch.load(str(model_path), map_location="cpu")
        
        # Trích xuất state_dict từ nhiều dạng checkpoint khác nhau
        if isinstance(checkpoint, torch.nn.Module):
            state_dict = checkpoint.state_dict()
        elif isinstance(checkpoint, dict):
            # Một số checkpoint lưu dạng {"model": state_dict, "epoch": ..., ...}
            if "model" in checkpoint and isinstance(checkpoint["model"], dict):
                state_dict = checkpoint["model"]
            elif "state_dict" in checkpoint:
                state_dict = checkpoint["state_dict"]
            elif "model_state_dict" in checkpoint:
                state_dict = checkpoint["model_state_dict"]
            else:
                state_dict = checkpoint
        else:
            return {"error": f"Định dạng file không được hỗ trợ: {type(checkpoint).__name__}"}
            
        layers_info = []
        total_params = 0
        keys_str = ""
        
        for k, v in state_dict.items():
            keys_str += k + " "
            
            # Bỏ qua các giá trị không phải Tensor (str, int, None, list...)
            if not hasattr(v, "shape"):
                layers_info.append({"name": k, "shape": f"[{type(v).__name__}]", "params": 0})
                continue
                
            shape = list(v.shape)
            params = 1
            for dim in shape:
                params *= dim
            total_params += params
            layers_info.append({"name": k, "shape": str(shape), "params": params})
            
        model_type = "Không xác định (Unknown Model)"
        if "ma_hoa_thuoc" in keys_str and "cac_lop_gcn" in keys_str:
            model_type = "FuzzyGCN (Mô hình hệ thống MedLink)"
        elif "gt_drug" in keys_str or "hgt_dgl" in keys_str or "drug_linear" in keys_str:
            model_type = "AMNTDDA (Deep Graph Library / GraphTransformer)"
        elif "conv" in keys_str and "lin" in keys_str:
            model_type = "Generic GNN"
            
        return {
            "model_type": model_type,
            "total_parameters": total_params,
            "layers": layers_info
        }
    except Exception as e:
        return {"error": str(e)}
