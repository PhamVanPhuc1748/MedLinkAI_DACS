"""
Script đẩy toàn bộ dữ liệu từ 3 dataset CSV vào SQL Server He_Thong_Du_Doan_Thuoc.
Gộp thuốc/bệnh từ B, C, F dataset, dedup theo tên, remap ID liên kết.

Chạy: python seed_sqlserver.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "backend"))

import pandas as pd
from sqlalchemy import text

from app.database import SessionLocal, engine, init_db
from app.models import Disease, Drug, DrugDiseaseLink, User
from app.security import hash_password

DATASETS = ["B-dataset", "C-dataset", "F-dataset"]


# ── load helpers ─────────────────────────────────────────────────────────────

def load_drug_df(dataset_dir: Path) -> pd.DataFrame:
    df = pd.read_csv(dataset_dir / "DrugInformation.csv")
    if str(df.columns[0]).startswith("Unnamed"):
        df = df.drop(columns=[df.columns[0]])
    df = df.reset_index(drop=True)
    df["local_id"] = range(len(df))
    return df


def load_disease_df(dataset_dir: Path) -> pd.DataFrame:
    df = pd.read_csv(dataset_dir / "DiseaseFeature.csv", header=None)
    return pd.DataFrame({
        "local_id": range(len(df)),
        "name": df.iloc[:, 0].astype(str).str.strip(),
    })


def load_links_df(dataset_dir: Path) -> pd.DataFrame:
    df = pd.read_csv(dataset_dir / "DrugDiseaseAssociationNumber.csv")
    if not {"drug", "disease"}.issubset(df.columns):
        raise ValueError(f"Thiếu cột drug/disease trong {dataset_dir}")
    return df[["drug", "disease"]].astype(int)


# ── merge all datasets ────────────────────────────────────────────────────────

def build_merged_data() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Trả về (drugs_merged, diseases_merged, links_merged)
    drugs_merged : global_id, name, external_id, smiles
    diseases_merged: global_id, name
    links_merged   : global_drug_id, global_disease_id
    """
    all_drugs: dict[str, dict] = {}     # name -> {global_id, external_id, smiles}
    all_diseases: dict[str, int] = {}   # name -> global_id
    all_links: set[tuple[int, int]] = set()

    drug_counter = 0
    disease_counter = 0

    for ds_name in DATASETS:
        ds_dir = ROOT / "dataset" / ds_name
        print(f"  Đọc {ds_name}...")

        # Drugs
        drug_local2global: dict[int, int] = {}
        try:
            drug_df = load_drug_df(ds_dir)
            for _, row in drug_df.iterrows():
                name = str(row["name"]).strip()
                if name not in all_drugs:
                    ext_id = str(row.get("id", "")) if pd.notna(row.get("id", None)) else None
                    smiles = str(row.get("smiles", "")) if pd.notna(row.get("smiles", None)) else None
                    all_drugs[name] = {
                        "global_id": drug_counter,
                        "external_id": ext_id,
                        "smiles": smiles,
                    }
                    drug_counter += 1
                drug_local2global[int(row["local_id"])] = all_drugs[name]["global_id"]
        except Exception as e:
            print(f"    [WARN] drug: {e}")

        # Diseases
        disease_local2global: dict[int, int] = {}
        try:
            dis_df = load_disease_df(ds_dir)
            for _, row in dis_df.iterrows():
                name = str(row["name"]).strip()
                if name not in all_diseases:
                    all_diseases[name] = disease_counter
                    disease_counter += 1
                disease_local2global[int(row["local_id"])] = all_diseases[name]
        except Exception as e:
            print(f"    [WARN] disease: {e}")

        # Links - remap local ID -> global ID
        try:
            lnk_df = load_links_df(ds_dir)
            for _, row in lnk_df.iterrows():
                g_drug = drug_local2global.get(int(row["drug"]))
                g_dis  = disease_local2global.get(int(row["disease"]))
                if g_drug is not None and g_dis is not None:
                    all_links.add((g_drug, g_dis))
        except Exception as e:
            print(f"    [WARN] links: {e}")

        print(f"    drugs={len(drug_local2global)}, diseases={len(disease_local2global)}, links={len(all_links)}")

    # Build DataFrames
    drugs_merged = pd.DataFrame([
        {"global_id": v["global_id"], "name": k, "external_id": v["external_id"], "smiles": v["smiles"]}
        for k, v in all_drugs.items()
    ]).sort_values("global_id").reset_index(drop=True)

    diseases_merged = pd.DataFrame([
        {"global_id": v, "name": k}
        for k, v in all_diseases.items()
    ]).sort_values("global_id").reset_index(drop=True)

    links_merged = pd.DataFrame(list(all_links), columns=["drug_global_id", "disease_global_id"])

    return drugs_merged, diseases_merged, links_merged


# ── seed into SQL Server ──────────────────────────────────────────────────────

def seed_all() -> None:
    db = SessionLocal()
    try:
        # 1. Users
        if db.query(User).count() == 0:
            db.add(User(username="admin", password_hash=hash_password("admin123"), role="admin"))
            db.add(User(username="user",  password_hash=hash_password("user123"),  role="user"))
            db.commit()
            print("  [OK]   users — thêm 2 tài khoản (admin, user)")
        else:
            print(f"  [SKIP] users — đã có {db.query(User).count()} tài khoản")

        # Build merged data
        print("\n  Gộp dữ liệu từ 3 dataset...")
        drugs_df, diseases_df, links_df = build_merged_data()
        print(f"\n  Tổng sau gộp: {len(drugs_df)} thuốc | {len(diseases_df)} bệnh | {len(links_df)} liên kết")

        # 2. Drugs
        if db.query(Drug).count() == 0:
            batch = [
                Drug(
                    id=int(row["global_id"]),
                    name=str(row["name"]),
                    external_id=str(row["external_id"]) if row["external_id"] else None,
                    smiles=str(row["smiles"]) if row["smiles"] else None,
                )
                for _, row in drugs_df.iterrows()
            ]
            db.bulk_save_objects(batch)
            db.commit()
            print(f"  [OK]   drugs — đã thêm {len(batch)} thuốc")
        else:
            print(f"  [SKIP] drugs — đã có {db.query(Drug).count()} dòng")

        # 3. Diseases
        if db.query(Disease).count() == 0:
            batch = [
                Disease(id=int(row["global_id"]), name=str(row["name"]))
                for _, row in diseases_df.iterrows()
            ]
            db.bulk_save_objects(batch)
            db.commit()
            print(f"  [OK]   diseases — đã thêm {len(batch)} bệnh")
        else:
            print(f"  [SKIP] diseases — đã có {db.query(Disease).count()} dòng")

        # 4. Links
        if db.query(DrugDiseaseLink).count() == 0:
            batch = [
                DrugDiseaseLink(drug_id=int(row["drug_global_id"]), disease_id=int(row["disease_global_id"]))
                for _, row in links_df.iterrows()
            ]
            db.bulk_save_objects(batch)
            db.commit()
            print(f"  [OK]   links — đã thêm {len(batch)} liên kết thuốc-bệnh")
        else:
            print(f"  [SKIP] links — đã có {db.query(DrugDiseaseLink).count()} dòng")

    except Exception as exc:
        db.rollback()
        print(f"\n[ERROR] {exc}")
        raise
    finally:
        db.close()


# ── main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    print("=" * 60)
    print(" SEED SQL SERVER — He_Thong_Du_Doan_Thuoc")
    print("=" * 60)

    print("\n[1] Khởi tạo bảng...")
    init_db()
    print("    OK")

    print("\n[2] Kiểm tra kết nối...")
    with engine.connect() as conn:
        row = conn.execute(text("SELECT DB_NAME() AS db, @@SERVERNAME AS srv")).fetchone()
        print(f"    {row.db} trên {row.srv}")

    print("\n[3] Seed dữ liệu...")
    seed_all()

    print("\n[4] Thống kê cuối:")
    db = SessionLocal()
    try:
        print(f"    Users    : {db.query(User).count()}")
        print(f"    Drugs    : {db.query(Drug).count()}")
        print(f"    Diseases : {db.query(Disease).count()}")
        print(f"    Links    : {db.query(DrugDiseaseLink).count()}")
    finally:
        db.close()

    print("\n Hoàn tất!\n")


if __name__ == "__main__":
    main()


import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "backend"))

import pandas as pd
from sqlalchemy import text
from sqlalchemy.dialects.mssql import dialect as mssql_dialect

from app.database import SessionLocal, engine, init_db
from app.models import Disease, Drug, DrugDiseaseLink, User
from app.security import hash_password


# ── helpers ──────────────────────────────────────────────────────────────────

def _normalize(text_val: str) -> str:
    return " ".join(str(text_val).strip().lower().split())


def load_drug_table(dataset_dir: Path) -> pd.DataFrame:
    df = pd.read_csv(dataset_dir / "DrugInformation.csv")
    # Bỏ cột index thừa nếu có
    if str(df.columns[0]).startswith("Unnamed"):
        df = df.drop(columns=[df.columns[0]])
    df["drug_id"] = range(len(df))
    return df


def load_disease_table(dataset_dir: Path) -> pd.DataFrame:
    df = pd.read_csv(dataset_dir / "DiseaseFeature.csv", header=None)
    return pd.DataFrame({"disease_id": range(len(df)), "name": df.iloc[:, 0].astype(str)})


def load_links(dataset_dir: Path) -> pd.DataFrame:
    return pd.read_csv(dataset_dir / "DrugDiseaseAssociationNumber.csv")


# ── seeding functions ─────────────────────────────────────────────────────────

def seed_users(db) -> None:
    if db.query(User).count() > 0:
        print("  [SKIP] users — đã có dữ liệu")
        return
    db.add(User(username="admin", password_hash=hash_password("admin123"), role="admin"))
    db.add(User(username="user",  password_hash=hash_password("user123"),  role="user"))
    db.commit()
    print("  [OK]   users — đã thêm 2 tài khoản (admin, user)")


def seed_drugs(db, dataset_dir: Path, dataset_name: str) -> None:
    existing = db.query(Drug).count()
    if existing > 0:
        print(f"  [SKIP] drugs — đã có {existing} dòng")
        return

    df = load_drug_table(dataset_dir)
    batch = []
    for _, row in df.iterrows():
        smiles_val = str(row["smiles"]) if "smiles" in df.columns and pd.notna(row.get("smiles")) else None
        ext_id     = str(row["id"])     if "id"     in df.columns and pd.notna(row.get("id"))     else None
        batch.append(Drug(
            id=int(row["drug_id"]),
            name=str(row["name"]),
            external_id=ext_id,
            smiles=smiles_val,
        ))
    db.bulk_save_objects(batch)
    db.commit()
    print(f"  [OK]   drugs — đã thêm {len(batch)} thuốc từ {dataset_name}")


def seed_diseases(db, dataset_dir: Path, dataset_name: str) -> None:
    existing = db.query(Disease).count()
    if existing > 0:
        print(f"  [SKIP] diseases — đã có {existing} dòng")
        return

    df = load_disease_table(dataset_dir)
    batch = [Disease(id=int(r["disease_id"]), name=str(r["name"])) for _, r in df.iterrows()]
    db.bulk_save_objects(batch)
    db.commit()
    print(f"  [OK]   diseases — đã thêm {len(batch)} bệnh từ {dataset_name}")


def seed_links(db, dataset_dir: Path, dataset_name: str) -> None:
    existing = db.query(DrugDiseaseLink).count()
    if existing > 0:
        print(f"  [SKIP] drug_disease_links — đã có {existing} dòng")
        return

    df = load_links(dataset_dir)
    if not {"drug", "disease"}.issubset(df.columns):
        print(f"  [WARN] {dataset_name}/DrugDiseaseAssociationNumber.csv thiếu cột drug/disease — bỏ qua")
        return

    # Lọc trùng trước khi insert
    df_unique = df[["drug", "disease"]].drop_duplicates()
    batch = [
        DrugDiseaseLink(drug_id=int(r["drug"]), disease_id=int(r["disease"]))
        for _, r in df_unique.iterrows()
    ]
    db.bulk_save_objects(batch)
    db.commit()
    print(f"  [OK]   links — đã thêm {len(batch)} liên kết thuốc-bệnh từ {dataset_name}")


# ── main ──────────────────────────────────────────────────────────────────────

def run(dataset_name: str) -> None:
    dataset_dir = ROOT / dataset_name

    if not dataset_dir.exists():
        print(f"[ERROR] Thư mục không tồn tại: {dataset_dir}")
        return

    print(f"\n{'='*55}")
    print(f" Dataset: {dataset_name}")
    print(f"{'='*55}")

    db = SessionLocal()
    try:
        seed_users(db)
        seed_drugs(db, dataset_dir, dataset_name)
        seed_diseases(db, dataset_dir, dataset_name)
        seed_links(db, dataset_dir, dataset_name)
    except Exception as exc:
        db.rollback()
        print(f"  [ERROR] {exc}")
        raise
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed dữ liệu CSV vào SQL Server")
    parser.add_argument(
        "--dataset",
        default="B-dataset",
        choices=["B-dataset", "C-dataset", "F-dataset", "all"],
        help="Dataset muốn seed (mặc định: B-dataset)",
    )
    args = parser.parse_args()

    # Tạo bảng nếu chưa có
    print("\n[1] Khởi tạo bảng trong SQL Server...")
    init_db()
    print("    Bảng đã sẵn sàng.")

    # Kiểm tra kết nối
    print("\n[2] Kiểm tra kết nối...")
    with engine.connect() as conn:
        row = conn.execute(text("SELECT DB_NAME() AS db, @@SERVERNAME AS srv")).fetchone()
        print(f"    Kết nối: {row.db} trên {row.srv}")

    print("\n[3] Bắt đầu seed dữ liệu...")
    datasets = ["B-dataset", "C-dataset", "F-dataset"] if args.dataset == "all" else [args.dataset]
    for ds in datasets:
        run(ds)

    print("\n[4] Hoàn tất! Thống kê SQL Server:")
    db = SessionLocal()
    try:
        print(f"    Users    : {db.query(User).count()}")
        print(f"    Drugs    : {db.query(Drug).count()}")
        print(f"    Diseases : {db.query(Disease).count()}")
        print(f"    Links    : {db.query(DrugDiseaseLink).count()}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
