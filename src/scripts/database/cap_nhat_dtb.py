"""
cap_nhat_dtb.py — Script nâng cấp CSDL SQL Server cho hệ thống MedLink AI.

Thực hiện:
  1. Đổi tên 8 bảng chính sang tiếng Việt (sp_rename).
  2. Xóa 4 bảng dataset_* cũ (đã gộp dataset).
  3. Tạo 12 bảng dataset riêng theo từng dataset (thuoc_b, benh_c, …).
  4. Nạp toàn bộ dữ liệu CSV vào 12 bảng đó.

Chạy:
    python cap_nhat_dtb.py
"""
from __future__ import annotations

import sys
from pathlib import Path

# Đảm bảo import được từ src/backend
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src" / "backend"))

import pandas as pd
from sqlalchemy import text

from app.database import engine, init_db
from app.models import (
    ThuocB, ThuocC, ThuocF,
    BenhB, BenhC, BenhF,
    ProteinB, ProteinC, ProteinF,
    LienKetB, LienKetC, LienKetF,
)

# ── Cấu hình ──────────────────────────────────────────────────────────────────

RENAME_MAP: dict[str, str] = {
    "users":                "nguoi_dung",
    "drugs":                "thuoc",
    "diseases":             "benh",
    "proteins":             "protein",
    "drug_disease_links":   "lien_ket_thuoc_benh",
    "drug_protein_links":   "lien_ket_thuoc_protein",
    "protein_disease_links":"lien_ket_protein_benh",
    "predictions_history":  "lich_su_du_doan",
}

DROP_OLD_TABLES: list[str] = [
    "dataset_links",
    "dataset_proteins",
    "dataset_diseases",
    "dataset_drugs",
]

DATASETS = ["B-dataset", "C-dataset", "F-dataset"]

DATASET_MODELS = {
    "B-dataset": {"drug": ThuocB, "disease": BenhB, "protein": ProteinB, "link": LienKetB},
    "C-dataset": {"drug": ThuocC, "disease": BenhC, "protein": ProteinC, "link": LienKetC},
    "F-dataset": {"drug": ThuocF, "disease": BenhF, "protein": ProteinF, "link": LienKetF},
}

ROOT = Path(__file__).resolve().parent.parent.parent  # src/scripts/database/ -> root
DATASET_ROOT = ROOT / "dataset"


# ── Helper CSV readers ────────────────────────────────────────────────────────

def _normalize(text_val: str) -> str:
    return " ".join(str(text_val).strip().lower().split())


def _read_drug_df(dataset: str) -> pd.DataFrame:
    df = pd.read_csv(DATASET_ROOT / dataset / "DrugInformation.csv")
    if len(df.columns) > 0 and str(df.columns[0]).startswith("Unnamed"):
        df = df.drop(columns=[df.columns[0]])
    df["drug_id"] = range(len(df))
    return df


def _read_disease_df(dataset: str) -> pd.DataFrame:
    df = pd.read_csv(DATASET_ROOT / dataset / "DiseaseFeature.csv", header=None)
    return pd.DataFrame({"disease_id": range(len(df)), "name": df.iloc[:, 0].astype(str)})


def _read_protein_df(dataset: str) -> pd.DataFrame:
    df = pd.read_csv(DATASET_ROOT / dataset / "ProteinInformation.csv")
    if len(df.columns) > 0 and str(df.columns[0]).startswith("Unnamed"):
        df = df.drop(columns=[df.columns[0]])
    df["protein_id"] = range(len(df))
    df["accession"] = df["id"].astype(str)
    return df


def _read_link_df(dataset: str) -> pd.DataFrame:
    return pd.read_csv(DATASET_ROOT / dataset / "DrugDiseaseAssociationNumber.csv")


# ── Bước 1: Đổi tên bảng ─────────────────────────────────────────────────────

def rename_tables() -> None:
    print("\n[1] Đổi tên bảng sang tiếng Việt …")
    with engine.begin() as conn:
        for old, new in RENAME_MAP.items():
            sql = text(f"""
                IF EXISTS (SELECT 1 FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = :old)
                   AND NOT EXISTS (SELECT 1 FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = :new)
                BEGIN
                    EXEC sp_rename :old, :new
                END
            """)
            conn.execute(sql, {"old": old, "new": new})
            print(f"    {old}  →  {new}")
    print("    ✅ Hoàn tất đổi tên")


# ── Bước 2: Xóa bảng dataset_* cũ ───────────────────────────────────────────

def drop_old_dataset_tables() -> None:
    print("\n[2] Xóa bảng dataset_* cũ …")
    with engine.begin() as conn:
        for tbl in DROP_OLD_TABLES:
            sql = text(f"IF OBJECT_ID(N'{tbl}', N'U') IS NOT NULL DROP TABLE [{tbl}]")
            conn.execute(sql)
            print(f"    Đã xóa (nếu tồn tại): {tbl}")
    print("    ✅ Hoàn tất")


# ── Bước 3: Tạo bảng mới ─────────────────────────────────────────────────────

def create_tables() -> None:
    print("\n[3] Tạo 12 bảng dataset riêng (nếu chưa tồn tại) …")
    init_db()
    print("    ✅ create_all() hoàn tất")


# ── Bước 4: Nạp dữ liệu CSV ──────────────────────────────────────────────────

def seed_dataset(dataset: str, session) -> dict[str, int]:
    models = DATASET_MODELS[dataset]
    m_drug, m_dis, m_prot, m_link = models["drug"], models["disease"], models["protein"], models["link"]

    # Xóa dữ liệu cũ (nếu có)
    session.query(m_link).delete()
    session.query(m_prot).delete()
    session.query(m_dis).delete()
    session.query(m_drug).delete()
    session.commit()

    # Thuốc
    drugs_df = _read_drug_df(dataset)
    drug_objs = []
    for _, row in drugs_df.iterrows():
        smiles_val = str(row["smiles"]) if "smiles" in drugs_df.columns and pd.notna(row.get("smiles")) else None
        ext_id = str(row["id"]) if "id" in drugs_df.columns else None
        drug_objs.append(m_drug(local_id=int(row["drug_id"]), name=str(row["name"]), external_id=ext_id, smiles=smiles_val))
    session.bulk_save_objects(drug_objs)
    session.commit()

    # Bệnh
    diseases_df = _read_disease_df(dataset)
    dis_objs = [m_dis(local_id=int(r["disease_id"]), name=str(r["name"])) for _, r in diseases_df.iterrows()]
    session.bulk_save_objects(dis_objs)
    session.commit()

    # Protein
    proteins_df = _read_protein_df(dataset)
    prot_objs = [m_prot(local_id=int(r["protein_id"]), accession=str(r["accession"])) for _, r in proteins_df.iterrows()]
    session.bulk_save_objects(prot_objs)
    session.commit()

    # Liên kết thuốc–bệnh
    links_df = _read_link_df(dataset)
    link_objs = [m_link(drug_local_id=int(r["drug"]), disease_local_id=int(r["disease"])) for _, r in links_df.iterrows()]
    session.bulk_save_objects(link_objs)
    session.commit()

    return {
        "drugs": len(drugs_df),
        "diseases": len(diseases_df),
        "proteins": len(proteins_df),
        "links": len(links_df),
    }


def seed_all() -> None:
    print("\n[4] Nạp dữ liệu CSV vào 12 bảng dataset …")
    from sqlalchemy.orm import Session

    with Session(engine) as session:
        for ds in DATASETS:
            print(f"\n    Dataset: {ds}")
            counts = seed_dataset(ds, session)
            for entity, cnt in counts.items():
                print(f"      {entity}: {cnt:,}")
    print("\n    ✅ Nạp dữ liệu hoàn tất")


# ── Bước 5: Thống kê ─────────────────────────────────────────────────────────

def print_stats() -> None:
    from sqlalchemy.orm import Session

    print("\n[5] Thống kê cuối cùng:")
    with Session(engine) as s:
        for ds, models in DATASET_MODELS.items():
            d = s.query(models["drug"]).count()
            b = s.query(models["disease"]).count()
            p = s.query(models["protein"]).count()
            lk = s.query(models["link"]).count()
            print(f"    {ds}: thuốc={d:,}  bệnh={b:,}  protein={p:,}  liên_kết={lk:,}")


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("  cap_nhat_dtb.py — Nâng cấp CSDL MedLink AI")
    print("=" * 60)

    try:
        rename_tables()
        drop_old_dataset_tables()
        create_tables()
        seed_all()
        print_stats()
        print("\n✅ Hoàn tất tất cả các bước!\n")
    except Exception as exc:
        print(f"\n❌ Lỗi: {exc}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
