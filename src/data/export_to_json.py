"""
src/data/export_to_json.py
──────────────────────────────────────────────────────────────────────────────
Script xuất toàn bộ dữ liệu từ database (SQL Server hoặc SQLite)
ra các file JSON trong thư mục src/data/.

  python src/data/export_to_json.py            # xuất tất cả bảng
  python src/data/export_to_json.py --table drugs diseases   # chỉ xuất 2 bảng
  python src/data/export_to_json.py --dry-run  # chỉ kiểm tra kết nối, không ghi

Lưu ý: mật khẩu (password_hash) của bảng users KHÔNG được xuất ra JSON.
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

# ── Đảm bảo import đúng package ──────────────────────────────────────────────
_ROOT = Path(__file__).resolve().parents[2]          # project root
_SRC  = _ROOT / "src"
for _p in (_ROOT, _SRC, _SRC / "backend"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("export_to_json")

DATA_DIR = Path(__file__).resolve().parent


# ── Hàm xuất từng bảng ───────────────────────────────────────────────────────
def _export_users(session, store) -> int:
    from app.models import User
    rows = session.query(User).all()
    records = [
        {
            "id":       r.id,
            "username": r.username,
            "email":    r.email,
            "role":     r.role,
            # password_hash bị loại bỏ để bảo mật
        }
        for r in rows
    ]
    store.users.replace_all(records)
    return len(records)


def _export_drugs(session, store) -> int:
    from app.models import Drug
    rows = session.query(Drug).all()
    records = [{"id": r.id, "name": r.name, "external_id": r.external_id, "smiles": r.smiles} for r in rows]
    store.drugs.replace_all(records)
    return len(records)


def _export_diseases(session, store) -> int:
    from app.models import Disease
    rows = session.query(Disease).all()
    records = [{"id": r.id, "name": r.name, "features": r.features} for r in rows]
    store.diseases.replace_all(records)
    return len(records)


def _export_proteins(session, store) -> int:
    from app.models import Protein
    rows = session.query(Protein).all()
    records = [{"id": r.id, "accession": r.accession, "sequence": r.sequence} for r in rows]
    store.proteins.replace_all(records)
    return len(records)


def _export_drug_disease_links(session, store) -> int:
    from app.models import DrugDiseaseLink
    rows = session.query(DrugDiseaseLink).all()
    records = [{"id": r.id, "drug_id": r.drug_id, "disease_id": r.disease_id} for r in rows]
    store.drug_disease_links.replace_all(records)
    return len(records)


def _export_drug_protein_links(session, store) -> int:
    from app.models import DrugProteinLink
    rows = session.query(DrugProteinLink).all()
    records = [{"id": r.id, "drug_id": r.drug_id, "protein_id": r.protein_id} for r in rows]
    store.drug_protein_links.replace_all(records)
    return len(records)


def _export_protein_disease_links(session, store) -> int:
    from app.models import ProteinDiseaseLink
    rows = session.query(ProteinDiseaseLink).all()
    records = [{"id": r.id, "protein_id": r.protein_id, "disease_id": r.disease_id} for r in rows]
    store.protein_disease_links.replace_all(records)
    return len(records)


def _export_prediction_history(session, store) -> int:
    from app.models import PredictionHistory
    rows = session.query(PredictionHistory).all()
    records = [
        {
            "id":          r.id,
            "user_id":     r.user_id,
            "direction":   r.direction,
            "input_name":  r.input_name,
            "target_id":   r.target_id,
            "target_name": r.target_name,
            "score":       float(r.score),
            "known":       bool(r.known),
            "timestamp":   r.timestamp.isoformat() if r.timestamp else None,
        }
        for r in rows
    ]
    store.prediction_history.replace_all(records)
    return len(records)


def _export_dataset_tables(session, store) -> dict[str, int]:
    from app.models import (
        ThuocB, ThuocC, ThuocF,
        BenhB, BenhC, BenhF,
        ProteinB, ProteinC, ProteinF,
        LienKetB, LienKetC, LienKetF,
    )

    mapping = [
        (ThuocB,    store.thuoc_b,    lambda r: {"id": r.id, "local_id": r.local_id, "name": r.name, "external_id": r.external_id, "smiles": r.smiles}),
        (ThuocC,    store.thuoc_c,    lambda r: {"id": r.id, "local_id": r.local_id, "name": r.name, "external_id": r.external_id, "smiles": r.smiles}),
        (ThuocF,    store.thuoc_f,    lambda r: {"id": r.id, "local_id": r.local_id, "name": r.name, "external_id": r.external_id, "smiles": r.smiles}),
        (BenhB,     store.benh_b,     lambda r: {"id": r.id, "local_id": r.local_id, "name": r.name}),
        (BenhC,     store.benh_c,     lambda r: {"id": r.id, "local_id": r.local_id, "name": r.name}),
        (BenhF,     store.benh_f,     lambda r: {"id": r.id, "local_id": r.local_id, "name": r.name}),
        (ProteinB,  store.protein_b,  lambda r: {"id": r.id, "local_id": r.local_id, "accession": r.accession}),
        (ProteinC,  store.protein_c,  lambda r: {"id": r.id, "local_id": r.local_id, "accession": r.accession}),
        (ProteinF,  store.protein_f,  lambda r: {"id": r.id, "local_id": r.local_id, "accession": r.accession}),
        (LienKetB,  store.lien_ket_b, lambda r: {"id": r.id, "drug_local_id": r.drug_local_id, "disease_local_id": r.disease_local_id}),
        (LienKetC,  store.lien_ket_c, lambda r: {"id": r.id, "drug_local_id": r.drug_local_id, "disease_local_id": r.disease_local_id}),
        (LienKetF,  store.lien_ket_f, lambda r: {"id": r.id, "drug_local_id": r.drug_local_id, "disease_local_id": r.disease_local_id}),
    ]

    counts: dict[str, int] = {}
    for model_cls, tbl, to_dict in mapping:
        rows = session.query(model_cls).all()
        records = [to_dict(r) for r in rows]
        tbl.replace_all(records)
        counts[tbl._path.stem] = len(records)
    return counts


# ── Bảng → hàm xuất (cho --table filter) ─────────────────────────────────────
_EXPORT_FN = {
    "users":                  _export_users,
    "drugs":                  _export_drugs,
    "diseases":               _export_diseases,
    "proteins":               _export_proteins,
    "drug_disease_links":     _export_drug_disease_links,
    "drug_protein_links":     _export_drug_protein_links,
    "protein_disease_links":  _export_protein_disease_links,
    "prediction_history":     _export_prediction_history,
}


# ── Hàm chính ─────────────────────────────────────────────────────────────────
def export_all(only_tables: list[str] | None = None, dry_run: bool = False) -> None:
    from app.database import SessionLocal, engine, SQLALCHEMY_DATABASE_URL
    from sqlalchemy import text

    log.info("=" * 60)
    log.info("Bắt đầu xuất dữ liệu → JSON")
    log.info("Nguồn DB  : %s", SQLALCHEMY_DATABASE_URL)
    log.info("Thư mục   : %s", DATA_DIR)
    log.info("=" * 60)

    # Kiểm tra kết nối
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        log.info("✅ Kết nối DB thành công")
    except Exception as exc:
        log.error("❌ Không thể kết nối DB: %s", exc)
        sys.exit(1)

    if dry_run:
        log.info("[DRY-RUN] Không ghi file, chỉ kiểm tra kết nối.")
        return

    from src.data.json_store import store

    session = SessionLocal()
    total_rows = 0
    try:
        # Xuất bảng chung
        for tbl_name, fn in _EXPORT_FN.items():
            if only_tables and tbl_name not in only_tables:
                continue
            try:
                n = fn(session, store)
                log.info("  %-30s → %d bản ghi", tbl_name, n)
                total_rows += n
            except Exception as exc:  # noqa: BLE001
                log.warning("  %-30s → LỖI: %s", tbl_name, exc)

        # Xuất bảng dataset (nếu không lọc hoặc có trong danh sách)
        dataset_names = {
            "thuoc_b","thuoc_c","thuoc_f",
            "benh_b","benh_c","benh_f",
            "protein_b","protein_c","protein_f",
            "lien_ket_b","lien_ket_c","lien_ket_f",
        }
        if not only_tables or any(t in dataset_names for t in (only_tables or [])):
            try:
                ds_counts = _export_dataset_tables(session, store)
                for name, n in ds_counts.items():
                    if not only_tables or name in only_tables:
                        log.info("  %-30s → %d bản ghi", name, n)
                        total_rows += n
            except Exception as exc:  # noqa: BLE001
                log.warning("  dataset tables → LỖI: %s", exc)

    finally:
        session.close()

    log.info("=" * 60)
    log.info("✅ Xuất xong — tổng %d bản ghi vào %s", total_rows, DATA_DIR)
    log.info("=" * 60)


# ── CLI ───────────────────────────────────────────────────────────────────────
def _parse() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Xuất DB → JSON (src/data/)")
    p.add_argument("--table", nargs="+", metavar="TABLE",
                   help="Chỉ xuất các bảng được liệt kê (mặc định: tất cả)")
    p.add_argument("--dry-run", action="store_true",
                   help="Chỉ kiểm tra kết nối, không ghi file JSON")
    return p.parse_args()


if __name__ == "__main__":
    args = _parse()
    export_all(only_tables=args.table, dry_run=args.dry_run)
