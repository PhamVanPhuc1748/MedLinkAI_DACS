from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import pandas as pd

try:
    from .mo_hinh_ai import FuzzyGCN
except ImportError:
    from mo_hinh_ai import FuzzyGCN


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
    out = pd.DataFrame({"disease_id": range(len(df)), "name": df.iloc[:, 0].astype(str)})
    out["name_norm"] = out["name"].map(_normalize)
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
    dataset_dir = _dataset_dir(dataset)
    drug_dim = pd.read_csv(dataset_dir / "DrugFingerprint.csv", nrows=1, index_col=0).shape[1]
    disease_df = pd.read_csv(dataset_dir / "DiseaseFeature.csv", nrows=1, header=None)
    disease_dim = int(disease_df.shape[1]) - 1
    return int(drug_dim), int(disease_dim)


@lru_cache(maxsize=4)
def get_model(dataset: str = "B-dataset") -> FuzzyGCN:
    root = _project_root()
    weights = root / "weights" / "fuzzy_gcn_all.pth"
    drug_dim, disease_dim = infer_feature_dims(dataset)
    model = FuzzyGCN(
        so_chieu_thuoc=drug_dim,
        so_chieu_benh=disease_dim,
        so_chieu_an=256,
        so_chieu_ra=128,
        so_lop_gcn=3,
        duong_dan_trong_so=str(weights),
    )
    model.tai_trong_so()
    diseases = load_disease_table(dataset)
    model.id_sang_ten_benh = {
        int(row["disease_id"]): str(row["name"])
        for _, row in diseases.iterrows()
    }
    model.eval()
    return model


@lru_cache(maxsize=4096)
def _predict_all_diseases_for_drug(dataset: str, drug_id: int) -> dict[int, float]:
    """Tra ve score class-1 theo tung disease cho mot drug_id."""
    diseases = load_disease_table(dataset)
    model = get_model(dataset)
    # Lay toan bo benh de tranh mat score khi doi top-k/threshold.
    preds = model.du_doan_top_k(drug_id=int(drug_id), k=int(len(diseases)))
    scores: dict[int, float] = {}
    for item in preds:
        disease_id = int(item["disease_id"])
        score = float(item.get("Probability", item.get("score", 0.0)))
        scores[disease_id] = score
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
