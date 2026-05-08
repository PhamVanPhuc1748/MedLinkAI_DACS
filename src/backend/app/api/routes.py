from __future__ import annotations
import json
import math
import os
import secrets
import smtplib
import sys
from collections import defaultdict
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from pathlib import Path
from typing import Annotated, Dict, Optional
from fastapi import APIRouter, Depends, Header, HTTPException, status
# Đảm bảo src/ trong sys.path để import json_repo
_SRC = Path(__file__).resolve().parents[3]
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))
import data.json_repo as repo
from data.data_source_status import data_source
from ..ai.inference_service import (
    predict_diseases_by_drug_name,
    predict_drugs_by_disease_name,
)
from ..schemas import (
    AdminRecalcRequest,
    DiseaseIn,
    DrugIn,
    ForgotPasswordRequest,
    HistoryItem,
    LinkIn,
    LoginRequest,
    LoginResponse,
    ModelCompareRequest,
    PredictRequest,
    PredictResponse,
    PredictionItem,
    RegisterRequest,
    ResetPasswordRequest,
    SeedDatasetRequest,
    StatsResponse,
)
from ..security import AuthUser, create_token, hash_password, verify_password
router = APIRouter(prefix="/api", tags=["api"])
TOKENS: dict[str, AuthUser] = {}
_OTP_STORE: dict[str, dict] = {}
def _routes_project_root() -> Path:
    return Path(__file__).resolve().parents[4]
def _send_reset_email(to_email: str, username: str, otp: str) -> None:
    smtp_host = os.environ.get("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.environ.get("SMTP_PORT", "587"))
    smtp_user = os.environ.get("SMTP_USER", "")
    smtp_pass = os.environ.get("SMTP_PASSWORD", "")
    if not smtp_user or not smtp_pass:
        raise RuntimeError(
            "SMTP chua duoc cau hinh. Vui long dat bien moi truong SMTP_USER va SMTP_PASSWORD."
        )
    body = (
        f"Xin chao {username},\n\n"
        f"Ma OTP dat lai mat khau cua ban la: {otp}\n"
        f"Ma co hieu luc trong 10 phut.\n\n"
        f"Neu ban khong yeu cau dat lai mat khau, vui long bo qua email nay.\n\n"
        f"-- MedLink AI Team"
    )
    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = "Ma OTP dat lai mat khau MedLink AI"
    msg["From"]    = smtp_user
    msg["To"]      = to_email
    with smtplib.SMTP(smtp_host, smtp_port) as server:
        server.ehlo()
        server.starttls()
        server.login(smtp_user, smtp_pass)
        server.send_message(msg)
def _auth_from_header(authorization: str | None) -> AuthUser:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Thieu token")
    token = authorization.split(" ", 1)[1].strip()
    user = TOKENS.get(token)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token khong hop le")
    return user
def get_current_user(
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
) -> AuthUser:
    return _auth_from_header(authorization)
def require_admin(user: Annotated[AuthUser, Depends(get_current_user)]) -> AuthUser:
    if user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Chi admin duoc phep")
    return user
# ── Health ────────────────────────────────────────────────────────────────────
@router.get("/health")
def health() -> dict:
    repo.bootstrap()
    import logging
    logging.getLogger(__name__).info(
        "[API] /health -- nguon du lieu: %s", data_source._short_summary()
    )
    return {"status": "ok", "data_source": data_source.current_source()}
# ── Auth ──────────────────────────────────────────────────────────────────────
@router.post("/auth/login", response_model=LoginResponse)
def login(payload: LoginRequest) -> LoginResponse:
    repo.bootstrap()
    user = repo.get_user_by_username(payload.username)
    if not user or not user.get("password_hash"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sai tai khoan / mat khau")
    if not verify_password(payload.password, user["password_hash"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sai tai khoan / mat khau")
    token = create_token()
    TOKENS[token] = AuthUser(id=user["id"], username=user["username"], role=user["role"])
    return LoginResponse(token=token, username=user["username"], role=user["role"])
@router.post("/auth/register")
def register(payload: RegisterRequest) -> dict:
    repo.bootstrap()
    if repo.user_exists(payload.username):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Ten dang nhap da ton tai")
    if repo.email_exists(payload.email):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email da duoc su dung")
    repo.create_user(
        username=payload.username,
        email=payload.email,
        password_hash=hash_password(payload.password),
        role="user",
    )
    return {"message": "Dang ky thanh cong"}
@router.post("/auth/forgot-password")
def forgot_password(payload: ForgotPasswordRequest) -> dict:
    repo.bootstrap()
    user = repo.get_user_by_username_and_email(payload.username, payload.email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Khong tim thay tai khoan voi ten dang nhap va email nay",
        )
    otp = f"{secrets.randbelow(1_000_000):06d}"
    _OTP_STORE[payload.username] = {
        "otp": otp,
        "email": payload.email,
        "expires": datetime.utcnow() + timedelta(minutes=10),
    }
    try:
        _send_reset_email(payload.email, payload.username, otp)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Khong the gui email: {exc}",
        ) from exc
    return {"message": "Da gui ma OTP den email cua ban."}
@router.post("/auth/reset-password")
def reset_password(payload: ResetPasswordRequest) -> dict:
    entry = _OTP_STORE.get(payload.username)
    if not entry:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Khong co yeu cau dat lai mat khau")
    if entry["otp"] != payload.otp:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Ma OTP khong chinh xac")
    if datetime.utcnow() > entry["expires"]:
        _OTP_STORE.pop(payload.username, None)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Ma OTP da het han")
    if not repo.update_user_password(payload.username, hash_password(payload.new_password)):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Nguoi dung khong ton tai")
    _OTP_STORE.pop(payload.username, None)
    return {"message": "Dat lai mat khau thanh cong"}
# ── Predict ───────────────────────────────────────────────────────────────────
@router.post("/predict/drug-to-disease", response_model=PredictResponse)
def predict_drug_to_disease(
    payload: PredictRequest,
    user: Annotated[AuthUser, Depends(get_current_user)],
) -> PredictResponse:
    input_name, preds = predict_diseases_by_drug_name(
        drug_name=payload.name,
        dataset=payload.dataset,
        top_k=payload.top_k,
        threshold=payload.threshold,
    )
    for item in preds:
        repo.add_prediction(
            user_id=user.id, direction="drug_to_disease",
            input_name=input_name, target_id=item["id"], target_name=item["name"],
            score=float(item["score"]), known=bool(item.get("known", False)),
        )
    return PredictResponse(
        direction="drug_to_disease",
        input_name=input_name,
        results=[PredictionItem(**x) for x in preds],
    )
@router.post("/predict/disease-to-drug", response_model=PredictResponse)
def predict_disease_to_drug(
    payload: PredictRequest,
    user: Annotated[AuthUser, Depends(get_current_user)],
) -> PredictResponse:
    input_name, preds = predict_drugs_by_disease_name(
        disease_name=payload.name,
        dataset=payload.dataset,
        top_k=payload.top_k,
        threshold=payload.threshold,
    )
    for item in preds:
        repo.add_prediction(
            user_id=user.id, direction="disease_to_drug",
            input_name=input_name, target_id=item["id"], target_name=item["name"],
            score=float(item["score"]), known=bool(item.get("known", False)),
        )
    return PredictResponse(
        direction="disease_to_drug",
        input_name=input_name,
        results=[PredictionItem(**x) for x in preds],
    )
# ── History ───────────────────────────────────────────────────────────────────
@router.get("/history", response_model=list[HistoryItem])
def history(user: Annotated[AuthUser, Depends(get_current_user)]) -> list[HistoryItem]:
    rows = repo.list_predictions_by_user(user.id, limit=200)
    result = []
    for r in rows:
        try:
            ts = datetime.fromisoformat(r["timestamp"]) if r.get("timestamp") else datetime.utcnow()
        except (ValueError, TypeError):
            ts = datetime.utcnow()
        result.append(HistoryItem(
            id=r.get("id", 0), direction=r["direction"], input_name=r["input_name"],
            target_id=r["target_id"], target_name=r["target_name"],
            score=r["score"], known=bool(r.get("known", False)), timestamp=ts,
        ))
    return result
# ── Data lists ────────────────────────────────────────────────────────────────
_VALID_DATASETS = {"B-dataset", "C-dataset", "F-dataset"}
@router.get("/drugs")
def list_drugs(
    user: AuthUser = Depends(get_current_user),
    limit: int = 200,
    offset: int = 0,
    dataset: Optional[str] = None,
) -> list[dict]:
    _ = user
    if dataset and dataset not in _VALID_DATASETS:
        raise HTTPException(status_code=400, detail="Dataset khong hop le")
    try:
        return repo.list_drugs(limit=limit, offset=offset, dataset=dataset)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
@router.get("/diseases")
def list_diseases(
    user: AuthUser = Depends(get_current_user),
    limit: int = 200,
    offset: int = 0,
    dataset: Optional[str] = None,
) -> list[dict]:
    _ = user
    if dataset and dataset not in _VALID_DATASETS:
        raise HTTPException(status_code=400, detail="Dataset khong hop le")
    try:
        return repo.list_diseases(limit=limit, offset=offset, dataset=dataset)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
@router.get("/proteins")
def list_proteins(
    user: AuthUser = Depends(get_current_user),
    limit: int = 200,
    offset: int = 0,
) -> list[dict]:
    _ = user
    return repo.list_proteins(limit=limit, offset=offset)
@router.get("/proteins/{protein_id}/links")
def get_protein_links(
    protein_id: int,
    user: AuthUser = Depends(get_current_user),
) -> dict:
    _ = user
    result = repo.get_protein_links(protein_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Protein khong ton tai")
    return result
@router.get("/links")
def list_links(
    user: AuthUser = Depends(get_current_user),
    limit: int = 500,
    offset: int = 0,
) -> list[dict]:
    _ = user
    return repo.list_links(limit=limit, offset=offset)
# ── User stats ────────────────────────────────────────────────────────────────
@router.get("/stats")
def user_stats(user: AuthUser = Depends(get_current_user)) -> dict:
    _ = user
    return repo.user_stats()
# ── Admin stats ───────────────────────────────────────────────────────────────
@router.get("/admin/stats", response_model=StatsResponse)
def admin_stats(_: Annotated[AuthUser, Depends(require_admin)]) -> StatsResponse:
    s = repo.admin_stats()
    return StatsResponse(**s)
@router.get("/admin/stats/predictions-by-direction")
def admin_prediction_direction_stats(
    _: Annotated[AuthUser, Depends(require_admin)],
) -> list[dict]:
    return repo.prediction_direction_stats()
@router.get("/admin/predictions")
def admin_list_predictions(
    _: Annotated[AuthUser, Depends(require_admin)],
    limit: int = 200,
    offset: int = 0,
) -> list[dict]:
    rows = repo.list_all_predictions(limit=limit, offset=offset)
    result = []
    for r in rows:
        ts = r.get("timestamp", "")
        result.append({
            "id":          r.get("id", 0),
            "user_id":     r.get("user_id"),
            "direction":   r.get("direction"),
            "input_name":  r.get("input_name"),
            "target_id":   r.get("target_id"),
            "target_name": r.get("target_name"),
            "score":       r.get("score"),
            "timestamp":   ts,
        })
    return result
# ── Admin CRUD ────────────────────────────────────────────────────────────────
@router.post("/admin/drugs")
def admin_create_drug(payload: DrugIn, _: Annotated[AuthUser, Depends(require_admin)]) -> dict:
    repo.upsert_drug(payload.id, payload.name, payload.external_id, payload.smiles)
    return {"ok": True}
@router.post("/admin/diseases")
def admin_create_disease(payload: DiseaseIn, _: Annotated[AuthUser, Depends(require_admin)]) -> dict:
    repo.upsert_disease(payload.id, payload.name)
    return {"ok": True}
@router.delete("/admin/drugs/{drug_id}")
def admin_delete_drug(drug_id: int, _: Annotated[AuthUser, Depends(require_admin)]) -> dict:
    repo.delete_drug(drug_id)
    return {"ok": True}
@router.delete("/admin/diseases/{disease_id}")
def admin_delete_disease(disease_id: int, _: Annotated[AuthUser, Depends(require_admin)]) -> dict:
    repo.delete_disease(disease_id)
    return {"ok": True}
@router.post("/admin/links")
def admin_create_link(payload: LinkIn, _: Annotated[AuthUser, Depends(require_admin)]) -> dict:
    repo.create_link(payload.drug_id, payload.disease_id)
    return {"ok": True}
@router.delete("/admin/links/{drug_id}/{disease_id}")
def admin_delete_link(
    drug_id: int,
    disease_id: int,
    _: Annotated[AuthUser, Depends(require_admin)],
) -> dict:
    repo.delete_link(drug_id, disease_id)
    return {"ok": True}
# ── Admin dataset seed ────────────────────────────────────────────────────────
@router.post("/admin/dataset/seed")
def admin_seed_dataset(
    payload: SeedDatasetRequest,
    _: Annotated[AuthUser, Depends(require_admin)],
) -> dict:
    """Tai dataset tu CSV goc -> ghi vao JSON store."""
    import pandas as _pd
    from ..ai.inference_service import (
        load_disease_table, load_drug_table, load_links, load_protein_table,
    )
    from data.json_store import store as _store
    dataset = payload.dataset
    if dataset not in _VALID_DATASETS:
        raise HTTPException(status_code=400, detail="Dataset khong hop le")
    _DS_DRUG  = {"B-dataset": _store.thuoc_b, "C-dataset": _store.thuoc_c, "F-dataset": _store.thuoc_f}
    _DS_DIS   = {"B-dataset": _store.benh_b,  "C-dataset": _store.benh_c,  "F-dataset": _store.benh_f}
    _DS_PROT  = {"B-dataset": _store.protein_b, "C-dataset": _store.protein_c, "F-dataset": _store.protein_f}
    _DS_LINK  = {"B-dataset": _store.lien_ket_b, "C-dataset": _store.lien_ket_c, "F-dataset": _store.lien_ket_f}
    drugs_df    = load_drug_table(dataset)
    diseases_df = load_disease_table(dataset)
    proteins_df = load_protein_table(dataset)
    links_df    = load_links(dataset)
    drug_records = []
    for _, row in drugs_df.iterrows():
        smiles = str(row["smiles"]) if "smiles" in drugs_df.columns and _pd.notna(row.get("smiles")) else None
        ext_id = str(row["id"]) if "id" in drugs_df.columns else None
        drug_records.append({"local_id": int(row["drug_id"]), "name": str(row["name"]),
                              "external_id": ext_id, "smiles": smiles})
    _DS_DRUG[dataset].replace_all(drug_records)
    dis_records = [{"local_id": int(r["disease_id"]), "name": str(r["name"])}
                   for _, r in diseases_df.iterrows()]
    _DS_DIS[dataset].replace_all(dis_records)
    prot_records = [{"local_id": int(r["protein_id"]), "accession": str(r["accession"])}
                    for _, r in proteins_df.iterrows()]
    _DS_PROT[dataset].replace_all(prot_records)
    link_records = [{"drug_local_id": int(r["drug"]), "disease_local_id": int(r["disease"])}
                    for _, r in links_df.iterrows()]
    _DS_LINK[dataset].replace_all(link_records)
    return {
        "message":  f"Da cap nhat dataset {dataset} vao JSON thanh cong",
        "dataset":  dataset,
        "drugs":    len(drug_records),
        "diseases": len(dis_records),
        "proteins": len(prot_records),
        "links":    len(link_records),
    }
@router.get("/admin/dataset/{dataset}/preview")
def admin_dataset_preview(
    dataset: str,
    _: Annotated[AuthUser, Depends(require_admin)],
) -> dict:
    if dataset not in _VALID_DATASETS:
        raise HTTPException(status_code=400, detail="Dataset khong hop le")
    try:
        return repo.dataset_preview(dataset)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
# ── Model metrics ─────────────────────────────────────────────────────────────
_METRICS_FILENAME = "kfold_metrics.json"
_DATASET_NAMES = ["B-dataset", "C-dataset", "F-dataset"]
def _find_metrics_files(weights_root: Path) -> Dict[str, Path]:
    found: Dict[str, Path] = {}
    for ds in _DATASET_NAMES:
        p = weights_root / ds / _METRICS_FILENAME
        if p.exists():
            found[ds] = p
    flat = weights_root / _METRICS_FILENAME
    if flat.exists() and not found:
        found["default"] = flat
    return found
def _extract_metrics(data: dict) -> dict:
    if "metrics" in data and isinstance(data["metrics"], dict):
        first_val = next(iter(data["metrics"].values()), None)
        if isinstance(first_val, dict) and "mean" in first_val:
            return data["metrics"]
    flat: dict = data.get("mean", data)
    return {k: {"mean": v, "std": None} for k, v in flat.items() if isinstance(v, float)}
@router.get("/model/metrics")
def model_metrics(
    dataset: Optional[str] = None,
    user: AuthUser = Depends(get_current_user),
) -> dict:
    _ = user
    weights_root = _routes_project_root() / "weights"
    available = _find_metrics_files(weights_root)
    if not available:
        raise HTTPException(status_code=404, detail=f"Khong tim thay '{_METRICS_FILENAME}'")
    if dataset:
        if dataset not in available:
            raise HTTPException(status_code=404, detail=f"Khong tim thay metrics cho '{dataset}'")
        data = json.loads(available[dataset].read_text(encoding="utf-8"))
        return {"dataset": dataset, "path": str(available[dataset]), "metrics": _extract_metrics(data)}
    result: dict = {"datasets": {}}
    for ds, path in available.items():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            result["datasets"][ds] = {"path": str(path), "metrics": _extract_metrics(data)}
        except Exception:
            result["datasets"][ds] = {"error": "Khong doc duoc file"}
    return result
@router.post("/model/compare")
def model_compare(payload: ModelCompareRequest, user: AuthUser = Depends(get_current_user)) -> dict:
    _ = user
    given = Path(payload.folder_path)
    if given.is_file() and given.suffix.lower() == ".json":
        metrics_file: Path | None = given
    else:
        candidates = [given / _METRICS_FILENAME, given / "weights" / _METRICS_FILENAME]
        for ds in _DATASET_NAMES:
            candidates += [given / ds / _METRICS_FILENAME, given / "weights" / ds / _METRICS_FILENAME]
        metrics_file = next((p for p in candidates if p.exists()), None)
    if metrics_file is None:
        raise HTTPException(status_code=404, detail=f"Khong tim thay '{_METRICS_FILENAME}' trong '{given}'")
    try:
        data = json.loads(metrics_file.read_text(encoding="utf-8"))
        return {"path": str(metrics_file), "metrics": _extract_metrics(data)}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Loi doc file: {exc}") from exc
# ── Admin recalculate metrics ─────────────────────────────────────────────────
@router.post("/admin/model/recalculate")
def admin_recalculate_metrics(
    payload: AdminRecalcRequest,
    user: AuthUser = Depends(get_current_user),
) -> dict:
    _ = user
    dataset = payload.dataset
    if dataset not in _DATASET_NAMES:
        raise HTTPException(status_code=400, detail=f"Dataset khong hop le. Chon: {_DATASET_NAMES}")
    weights_root = _routes_project_root() / "weights"
    metrics_path = weights_root / dataset / _METRICS_FILENAME
    if not metrics_path.exists():
        raise HTTPException(status_code=404, detail=f"Khong tim thay '{metrics_path}'")
    try:
        data = json.loads(metrics_path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Loi doc file: {exc}") from exc
    folds: list = data.get("folds", [])
    metric_keys = ["AUC", "AUPR", "Accuracy", "Precision", "Recall", "F1", "MCC"]
    def _aggregate(fold_list: list) -> Dict[str, dict]:
        result: Dict[str, dict] = {}
        for k in metric_keys:
            vals = [float(f[k]) for f in fold_list if k in f]
            if not vals:
                continue
            mean_val = sum(vals) / len(vals)
            variance = sum((x - mean_val) ** 2 for x in vals) / max(len(vals) - 1, 1)
            result[k] = {"mean": round(mean_val, 6), "std": round(math.sqrt(variance), 6)}
        return result
    if folds:
        new_metrics = _aggregate(folds)
        data["metrics"] = new_metrics
        data["mean"] = {k: v["mean"] for k, v in new_metrics.items()}
        data["std"]  = {k: v["std"]  for k, v in new_metrics.items()}
        metrics_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        return {
            "message": f"Tinh lai thanh cong tu {len(folds)} folds (dataset: {dataset}).",
            "dataset": dataset, "metrics": new_metrics, "source": "folds",
        }
    pth_dir   = weights_root / dataset
    pth_files = sorted(pth_dir.glob("best_fold_*.pth"))
    if not pth_files:
        raise HTTPException(
            status_code=404,
            detail=(
                f"Khong tim thay .pth trong '{pth_dir}' va 'folds' trong JSON rong. "
                "Vui long train lai de tao du lieu folds."
            ),
        )
    try:
        import numpy as np
        import torch
        from sklearn.model_selection import StratifiedKFold
        from ..ai.huan_luyen import (
            CauHinh, can_chinh_hang, dat_seed, doc_lien_ket, doc_ma_tran,
            giai_ma_diem, tao_canh_am, tao_do_thi, tinh_chi_so,
        )
        from ..ai.mo_hinh_ai import FuzzyGCN
        cau_hinh = CauHinh(ten_dataset=dataset)
        dat_seed(cau_hinh.seed)
        project_root  = _routes_project_root()
        duong_dataset = project_root / "dataset" / dataset
        canh_duong = doc_lien_ket(duong_dataset / cau_hinh.tep_lien_ket)
        max_thuoc  = int(canh_duong[:, 0].max()) + 1
        max_benh   = int(canh_duong[:, 1].max()) + 1
        thuoc = can_chinh_hang(doc_ma_tran(duong_dataset / cau_hinh.tep_thuoc), max_thuoc, "Thuoc")
        benh  = can_chinh_hang(doc_ma_tran(duong_dataset / cau_hinh.tep_benh),  max_benh,  "Benh")
        so_thuoc, so_benh = thuoc.shape[0], benh.shape[0]
        hop_le     = ((canh_duong[:, 0] >= 0) & (canh_duong[:, 0] < so_thuoc)
                      & (canh_duong[:, 1] >= 0) & (canh_duong[:, 1] < so_benh))
        canh_duong = canh_duong[hop_le]
        tap_duong  = set(zip(canh_duong[:, 0].tolist(), canh_duong[:, 1].tolist()))
        so_am      = max(1, int(len(canh_duong) * cau_hinh.ti_le_am))
        canh_am    = tao_canh_am(so_thuoc, so_benh, tap_duong, so_am)
        canh_tat_ca = np.vstack([canh_duong, canh_am])
        nhan_tat_ca = np.hstack([np.ones(len(canh_duong), dtype=np.int64),
                                  np.zeros(len(canh_am), dtype=np.int64)])
        graph_data  = tao_do_thi(thuoc, benh, canh_duong)
        skf    = StratifiedKFold(n_splits=len(pth_files), shuffle=True, random_state=cau_hinh.seed)
        device = torch.device("cpu")
        fold_metrics: list = []
        for fold_id, (_, test_idx) in enumerate(skf.split(canh_tat_ca, nhan_tat_ca), start=1):
            pth_path = pth_dir / f"best_fold_{fold_id}.pth"
            if not pth_path.exists():
                continue
            state = torch.load(pth_path, map_location=device, weights_only=True)
            _kich_an = int(state["ma_hoa_thuoc.weight"].shape[0])
            _last_bias = sorted(
                [k for k in state if k.startswith("cac_lop_gcn.") and k.endswith(".bias")],
                key=lambda k: int(k.split(".")[1]),
            )[-1]
            _kich_ra = int(state[_last_bias].shape[0])
            _so_lop  = len({k.split(".")[1] for k in state if k.startswith("cac_lop_gcn.")})
            mo_hinh = FuzzyGCN(
                so_chieu_thuoc=thuoc.shape[1], so_chieu_benh=benh.shape[1],
                so_chieu_an=_kich_an, so_chieu_ra=_kich_ra, so_lop_gcn=_so_lop,
                duong_dan_trong_so=str(pth_path),
            ).to(device)
            mo_hinh.load_state_dict(state)
            mo_hinh.eval()
            g = graph_data.to(device)
            with torch.no_grad():
                cap_test = torch.from_numpy(canh_tat_ca[test_idx].T).long().to(device)
                emb  = mo_hinh(g)
                diem = torch.sigmoid(giai_ma_diem(emb, cap_test, so_thuoc)).cpu().numpy()
            fold_metrics.append(tinh_chi_so(nhan_tat_ca[test_idx], diem))
        if not fold_metrics:
            raise HTTPException(status_code=500, detail="Khong eval duoc fold nao.")
        new_metrics = _aggregate(fold_metrics)
        data.update({"metrics": new_metrics,
                     "mean":   {k: v["mean"] for k, v in new_metrics.items()},
                     "std":    {k: v["std"]  for k, v in new_metrics.items()},
                     "folds":  fold_metrics})
        metrics_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        return {
            "message": f"Tinh lai thanh cong tu {len(fold_metrics)} .pth files (dataset: {dataset}).",
            "dataset": dataset, "metrics": new_metrics, "source": "pth_eval",
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Loi tinh lai metrics: {exc}",
        ) from exc
