"""
src/data/json_repo.py
──────────────────────────────────────────────────────────────────────────────
Repository layer - cung cap cac ham CRUD su dung json_store.py lam backend.
Duoc goi truc tiep tu routes.py qua `import data.json_repo as repo`.
"""
from __future__ import annotations

import hashlib
import logging
from datetime import datetime
from typing import Any

from .json_store import store

log = logging.getLogger(__name__)

# ── Dataset map ───────────────────────────────────────────────────────────────
_DS_DRUG  = {"B-dataset": "thuoc_b",   "C-dataset": "thuoc_c",   "F-dataset": "thuoc_f"}
_DS_DIS   = {"B-dataset": "benh_b",    "C-dataset": "benh_c",    "F-dataset": "benh_f"}
_DS_PROT  = {"B-dataset": "protein_b", "C-dataset": "protein_c", "F-dataset": "protein_f"}
_DS_LINK  = {"B-dataset": "lien_ket_b","C-dataset": "lien_ket_c","F-dataset": "lien_ket_f"}


def _hash(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


# ── Bootstrap ─────────────────────────────────────────────────────────────────

def bootstrap() -> None:
    """Dam bao tai khoan mac dinh ton tai va co password_hash."""
    defaults = [
        {"id": 1, "username": "admin", "email": "admin@medlink.ai",
         "password_hash": _hash("admin123"), "role": "admin"},
        {"id": 2, "username": "user",  "email": "user@medlink.ai",
         "password_hash": _hash("user123"),  "role": "user"},
        {"id": 3, "username": "expert", "email": "expert@medlink.ai",
         "password_hash": _hash("expert123"), "role": "expert"},
    ]
    for default in defaults:
        existing = store.users.find_one(username=default["username"])
        if existing is None:
            store.users.upsert(default)
        else:
            changed = False
            # Nếu có hash rỗng hoặc hash bị sai (ví dụ user123 bị sai thành e606... ko khớp _hash)
            # Ta sẽ ép lại hash cho đúng nếu nó bị null. (Không đè pass người dùng tự đổi)
            if not existing.get("password_hash"):
                existing["password_hash"] = default["password_hash"]
                changed = True
            
            # Cập nhật email nếu thiếu
            if not existing.get("email"):
                existing["email"] = default["email"]
                changed = True
                
            if changed:
                store.users.upsert(existing)


# ── Auth / Users ──────────────────────────────────────────────────────────────

def get_user_by_username(username: str) -> dict | None:
    return store.users.find_one(username=username)


def get_user_by_username_and_email(username: str, email: str) -> dict | None:
    rows = store.users.find(username=username)
    for r in rows:
        if r.get("email") == email:
            return r
    return None


def user_exists(username: str) -> bool:
    return store.users.find_one(username=username) is not None


def email_exists(email: str) -> bool:
    return store.users.find_one(email=email) is not None


def create_user(username: str, email: str, password_hash: str, role: str = "user") -> dict:
    all_users = store.users.all()
    new_id = max((u.get("id", 0) for u in all_users), default=0) + 1
    record = {
        "id": new_id,
        "username": username,
        "email": email,
        "password_hash": password_hash,
        "role": role,
    }
    return store.users.upsert(record)


def update_user_password(username: str, new_hash: str) -> bool:
    user = store.users.find_one(username=username)
    if not user:
        return False
    user["password_hash"] = new_hash
    store.users.upsert(user)
    return True


# ── Predictions ───────────────────────────────────────────────────────────────

def add_prediction(
    user_id: int,
    direction: str,
    input_name: str,
    target_id: int,
    target_name: str,
    score: float,
    known: bool = False,
) -> dict:
    all_preds = store.prediction_history.all()
    new_id = max((p.get("id", 0) for p in all_preds), default=0) + 1
    record: dict[str, Any] = {
        "id": new_id,
        "user_id": user_id,
        "direction": direction,
        "input_name": input_name,
        "target_id": target_id,
        "target_name": target_name,
        "score": score,
        "known": known,
        "timestamp": datetime.utcnow().isoformat(),
    }
    return store.prediction_history.upsert(record)


def list_predictions_by_user(user_id: int, limit: int = 200) -> list[dict]:
    rows = store.prediction_history.find(user_id=user_id)
    rows.sort(key=lambda r: r.get("timestamp", ""), reverse=True)
    return rows[:limit]


def list_all_predictions(limit: int = 200, offset: int = 0) -> list[dict]:
    rows = store.prediction_history.all()
    rows.sort(key=lambda r: r.get("timestamp", ""), reverse=True)
    return rows[offset : offset + limit]


# ── Drugs ─────────────────────────────────────────────────────────────────────

def list_drugs(limit: int = 200, offset: int = 0, dataset: str | None = None) -> list[dict]:
    if dataset:
        tname = _DS_DRUG.get(dataset)
        if not tname:
            raise ValueError(f"Dataset khong hop le: {dataset}")
        rows = store.table(tname).all()
    else:
        rows = store.drugs.all()
    return rows[offset : offset + limit]


def upsert_drug(
    drug_id: int | None,
    name: str,
    external_id: str | None = None,
    smiles: str | None = None,
) -> dict:
    all_drugs = store.drugs.all()
    if drug_id is None:
        drug_id = max((d.get("id", 0) for d in all_drugs), default=0) + 1
    record = {"id": drug_id, "name": name, "external_id": external_id, "smiles": smiles}
    return store.drugs.upsert(record)


def delete_drug(drug_id: int) -> bool:
    return store.drugs.delete(drug_id)


# ── Diseases ──────────────────────────────────────────────────────────────────

def list_diseases(limit: int = 200, offset: int = 0, dataset: str | None = None) -> list[dict]:
    if dataset:
        tname = _DS_DIS.get(dataset)
        if not tname:
            raise ValueError(f"Dataset khong hop le: {dataset}")
        rows = store.table(tname).all()
    else:
        rows = store.diseases.all()
    return rows[offset : offset + limit]


def upsert_disease(disease_id: int | None, name: str) -> dict:
    all_diseases = store.diseases.all()
    if disease_id is None:
        disease_id = max((d.get("id", 0) for d in all_diseases), default=0) + 1
    record = {"id": disease_id, "name": name}
    return store.diseases.upsert(record)


def delete_disease(disease_id: int) -> bool:
    return store.diseases.delete(disease_id)


# ── Proteins ──────────────────────────────────────────────────────────────────

def list_proteins(limit: int = 200, offset: int = 0) -> list[dict]:
    rows = store.proteins.all()
    return rows[offset : offset + limit]


def get_protein_links(protein_id: int) -> dict | None:
    protein = store.proteins.get(protein_id)
    if protein is None:
        return None
    drug_links = store.drug_protein_links.find(protein_id=protein_id)
    dis_links = [r for r in store.protein_disease_links.all() if r.get("protein_id") == protein_id]
    return {
        "protein": protein,
        "drug_links": drug_links,
        "disease_links": dis_links,
    }


# ── Links ─────────────────────────────────────────────────────────────────────

def list_links(limit: int = 500, offset: int = 0) -> list[dict]:
    rows = store.drug_disease_links.all()
    return rows[offset : offset + limit]


def create_link(drug_id: int, disease_id: int) -> dict:
    all_links = store.drug_disease_links.all()
    # Avoid duplicates
    for lnk in all_links:
        if lnk.get("drug_id") == drug_id and lnk.get("disease_id") == disease_id:
            return lnk
    new_id = max((l.get("id", 0) for l in all_links), default=0) + 1
    record = {"id": new_id, "drug_id": drug_id, "disease_id": disease_id}
    return store.drug_disease_links.upsert(record)


def delete_link(drug_id: int, disease_id: int) -> bool:
    rows = store.drug_disease_links.find(drug_id=drug_id, disease_id=disease_id)
    if not rows:
        return False
    for row in rows:
        store.drug_disease_links.delete(row["id"])
    return True


# ── Stats ─────────────────────────────────────────────────────────────────────

def user_stats() -> dict:
    return {
        "total_users": store.users.count(),
        "total_drugs": store.drugs.count(),
        "total_diseases": store.diseases.count(),
        "total_links": store.drug_disease_links.count(),
        "total_predictions": store.prediction_history.count(),
    }


def admin_stats() -> dict:
    return user_stats()


def prediction_direction_stats() -> list[dict]:
    rows = store.prediction_history.all()
    counts: dict[str, int] = {}
    for r in rows:
        d = r.get("direction", "unknown")
        counts[d] = counts.get(d, 0) + 1
    return [{"direction": k, "count": v} for k, v in counts.items()]


# ── Dataset preview ───────────────────────────────────────────────────────────

def dataset_preview(dataset: str) -> dict:
    dtname = _DS_DRUG.get(dataset)
    distname = _DS_DIS.get(dataset)
    ptname = _DS_PROT.get(dataset)
    ltname = _DS_LINK.get(dataset)
    if not dtname:
        raise ValueError(f"Dataset khong hop le: {dataset}")
    drugs = store.table(dtname).all()[:5]
    diseases = store.table(distname).all()[:5]
    proteins = store.table(ptname).all()[:5]
    links = store.table(ltname).all()[:5]
    return {
        "dataset": dataset,
        "drugs":    {"count": store.table(dtname).count(),    "sample": drugs},
        "diseases": {"count": store.table(distname).count(),  "sample": diseases},
        "proteins": {"count": store.table(ptname).count(),    "sample": proteins},
        "links":    {"count": store.table(ltname).count(),    "sample": links},
    }
