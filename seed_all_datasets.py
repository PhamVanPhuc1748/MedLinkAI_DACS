"""
Script cập nhật dữ liệu dataset C và F vào database.
- Bảng chính (drugs, diseases, proteins, links): upsert các bản ghi mới từ C/F không trùng với B
- Bảng dataset_* : seed lại toàn bộ 3 dataset (B, C, F)

Chạy: python seed_all_datasets.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src" / "backend"))

import pandas as pd
from sqlalchemy import text

from app.database import SessionLocal, engine, init_db
from app.models import (
    Disease, Drug, DrugDiseaseLink, Protein, DrugProteinLink, ProteinDiseaseLink,
    DatasetDrug, DatasetDisease, DatasetProtein, DatasetLink,
)

DATASETS = ["B-dataset", "C-dataset", "F-dataset"]


# ── CSV helpers ───────────────────────────────────────────────────────────────

def load_drug_csv(ds_dir: Path) -> pd.DataFrame:
    df = pd.read_csv(ds_dir / "DrugInformation.csv")
    if str(df.columns[0]).startswith("Unnamed"):
        df = df.drop(columns=[df.columns[0]])
    df = df.reset_index(drop=True)
    df["local_id"] = range(len(df))
    return df


def load_disease_csv(ds_dir: Path) -> pd.DataFrame:
    df = pd.read_csv(ds_dir / "DiseaseFeature.csv", header=None)
    return pd.DataFrame({
        "local_id": range(len(df)),
        "name": df.iloc[:, 0].astype(str).str.strip(),
    })


def load_links_csv(ds_dir: Path) -> pd.DataFrame:
    df = pd.read_csv(ds_dir / "DrugDiseaseAssociationNumber.csv")
    return df[["drug", "disease"]].astype(int)


def load_protein_csv(ds_dir: Path) -> pd.DataFrame:
    df = pd.read_csv(ds_dir / "ProteinInformation.csv")
    if str(df.columns[0]).startswith("Unnamed"):
        df = df.drop(columns=[df.columns[0]])
    df = df.reset_index(drop=True)
    df["local_id"] = range(len(df))
    if "id" not in df.columns:
        df["id"] = df.index.astype(str)
    df["accession"] = df["id"].astype(str)
    return df


def load_drug_protein_csv(ds_dir: Path) -> pd.DataFrame:
    return pd.read_csv(ds_dir / "DrugProteinAssociationNumber.csv")[["drug", "protein"]].astype(int)


def load_protein_disease_csv(ds_dir: Path) -> pd.DataFrame:
    return pd.read_csv(ds_dir / "ProteinDiseaseAssociationNumber.csv")[["protein", "disease"]].astype(int)


# ── Step 1: seed dataset_* tables (per-dataset tables) ───────────────────────

def seed_dataset_tables(db, ds_name: str) -> None:
    """Xóa và nạp lại toàn bộ dữ liệu cho dataset này trong bảng dataset_*."""
    ds_dir = ROOT / "dataset" / ds_name
    print(f"\n  [dataset_*] {ds_name} ...")

    # Xóa cũ
    db.query(DatasetLink).filter(DatasetLink.dataset == ds_name).delete()
    db.query(DatasetProtein).filter(DatasetProtein.dataset == ds_name).delete()
    db.query(DatasetDisease).filter(DatasetDisease.dataset == ds_name).delete()
    db.query(DatasetDrug).filter(DatasetDrug.dataset == ds_name).delete()
    db.commit()

    # Thuốc
    try:
        drug_df = load_drug_csv(ds_dir)
        objs = []
        for _, row in drug_df.iterrows():
            smiles = str(row["smiles"]) if "smiles" in drug_df.columns and pd.notna(row.get("smiles")) else None
            ext_id = str(row["id"]) if "id" in drug_df.columns else None
            objs.append(DatasetDrug(
                dataset=ds_name, local_id=int(row["local_id"]),
                name=str(row["name"]), external_id=ext_id, smiles=smiles,
            ))
        db.bulk_save_objects(objs)
        db.commit()
        print(f"    drugs: {len(objs)}")
    except Exception as e:
        db.rollback()
        print(f"    [WARN] drugs: {e}")

    # Bệnh
    try:
        dis_df = load_disease_csv(ds_dir)
        objs = [DatasetDisease(dataset=ds_name, local_id=int(r["local_id"]), name=str(r["name"]))
                for _, r in dis_df.iterrows()]
        db.bulk_save_objects(objs)
        db.commit()
        print(f"    diseases: {len(objs)}")
    except Exception as e:
        db.rollback()
        print(f"    [WARN] diseases: {e}")

    # Protein
    try:
        prot_df = load_protein_csv(ds_dir)
        objs = [DatasetProtein(dataset=ds_name, local_id=int(r["local_id"]), accession=str(r["accession"]))
                for _, r in prot_df.iterrows()]
        db.bulk_save_objects(objs)
        db.commit()
        print(f"    proteins: {len(objs)}")
    except Exception as e:
        db.rollback()
        print(f"    [WARN] proteins: {e}")

    # Liên kết thuốc–bệnh
    try:
        lnk_df = load_links_csv(ds_dir)
        objs = [DatasetLink(dataset=ds_name, drug_local_id=int(r["drug"]), disease_local_id=int(r["disease"]))
                for _, r in lnk_df.iterrows()]
        db.bulk_save_objects(objs)
        db.commit()
        print(f"    links: {len(objs)}")
    except Exception as e:
        db.rollback()
        print(f"    [WARN] links: {e}")


# ── Step 2: upsert main tables with merged data from all datasets ─────────────

def upsert_main_tables(db) -> None:
    """Gộp thuốc/bệnh/protein từ tất cả dataset và upsert vào bảng chính."""
    print("\n  [main tables] Đọc dữ liệu từ tất cả dataset và upsert...")

    # --- Drugs ---
    existing_drug_names: set[str] = {r.name for r in db.query(Drug.name).all()}
    max_drug_id: int = db.query(Drug).count()  # next id = count (0-based)
    # Actually use max id
    last_drug = db.query(Drug).order_by(Drug.id.desc()).first()
    next_drug_id = (last_drug.id + 1) if last_drug else 0

    new_drugs: list[Drug] = []
    for ds_name in DATASETS:
        ds_dir = ROOT / "dataset" / ds_name
        try:
            drug_df = load_drug_csv(ds_dir)
            for _, row in drug_df.iterrows():
                name = str(row["name"]).strip()
                if name not in existing_drug_names:
                    smiles = str(row["smiles"]) if "smiles" in drug_df.columns and pd.notna(row.get("smiles")) else None
                    ext_id = str(row["id"]) if "id" in drug_df.columns else None
                    new_drugs.append(Drug(id=next_drug_id, name=name, external_id=ext_id, smiles=smiles))
                    existing_drug_names.add(name)
                    next_drug_id += 1
        except Exception as e:
            print(f"    [WARN] drug {ds_name}: {e}")

    if new_drugs:
        db.bulk_save_objects(new_drugs)
        db.commit()
        print(f"    Thêm {len(new_drugs)} thuốc mới vào bảng drugs")
    else:
        print("    Không có thuốc mới cần thêm")

    # --- Diseases ---
    existing_dis_names: set[str] = {r.name for r in db.query(Disease.name).all()}
    last_dis = db.query(Disease).order_by(Disease.id.desc()).first()
    next_dis_id = (last_dis.id + 1) if last_dis else 0

    new_diseases: list[Disease] = []
    for ds_name in DATASETS:
        ds_dir = ROOT / "dataset" / ds_name
        try:
            dis_df = load_disease_csv(ds_dir)
            for _, row in dis_df.iterrows():
                name = str(row["name"]).strip()
                if name not in existing_dis_names:
                    new_diseases.append(Disease(id=next_dis_id, name=name))
                    existing_dis_names.add(name)
                    next_dis_id += 1
        except Exception as e:
            print(f"    [WARN] disease {ds_name}: {e}")

    if new_diseases:
        db.bulk_save_objects(new_diseases)
        db.commit()
        print(f"    Thêm {len(new_diseases)} bệnh mới vào bảng diseases")
    else:
        print("    Không có bệnh mới cần thêm")

    # --- Proteins ---
    existing_acc: set[str] = {r.accession for r in db.query(Protein.accession).all()}
    last_prot = db.query(Protein).order_by(Protein.id.desc()).first()
    next_prot_id = (last_prot.id + 1) if last_prot else 0

    new_proteins: list[Protein] = []
    for ds_name in DATASETS:
        ds_dir = ROOT / "dataset" / ds_name
        try:
            prot_df = load_protein_csv(ds_dir)
            for _, row in prot_df.iterrows():
                acc = str(row["accession"]).strip()
                if acc not in existing_acc:
                    new_proteins.append(Protein(id=next_prot_id, accession=acc))
                    existing_acc.add(acc)
                    next_prot_id += 1
        except Exception as e:
            print(f"    [WARN] protein {ds_name}: {e}")

    if new_proteins:
        db.bulk_save_objects(new_proteins)
        db.commit()
        print(f"    Thêm {len(new_proteins)} protein mới vào bảng proteins")
    else:
        print("    Không có protein mới cần thêm")

    # --- DrugDiseaseLinks (dùng name mapping) ---
    # Build name -> id maps
    drug_name_to_id: dict[str, int] = {r.name: r.id for r in db.query(Drug).all()}
    dis_name_to_id: dict[str, int] = {r.name: r.id for r in db.query(Disease).all()}
    existing_links: set[tuple[int, int]] = {
        (r.drug_id, r.disease_id) for r in db.query(DrugDiseaseLink.drug_id, DrugDiseaseLink.disease_id).all()
    }

    new_links: list[DrugDiseaseLink] = []
    for ds_name in DATASETS:
        ds_dir = ROOT / "dataset" / ds_name
        try:
            drug_df = load_drug_csv(ds_dir)
            dis_df = load_disease_csv(ds_dir)
            lnk_df = load_links_csv(ds_dir)
            local_drug_id_to_name = {int(r["local_id"]): str(r["name"]).strip() for _, r in drug_df.iterrows()}
            local_dis_id_to_name = {int(r["local_id"]): str(r["name"]).strip() for _, r in dis_df.iterrows()}
            for _, row in lnk_df.iterrows():
                d_name = local_drug_id_to_name.get(int(row["drug"]))
                dis_name = local_dis_id_to_name.get(int(row["disease"]))
                if d_name and dis_name:
                    g_drug = drug_name_to_id.get(d_name)
                    g_dis = dis_name_to_id.get(dis_name)
                    if g_drug is not None and g_dis is not None:
                        key = (g_drug, g_dis)
                        if key not in existing_links:
                            new_links.append(DrugDiseaseLink(drug_id=g_drug, disease_id=g_dis))
                            existing_links.add(key)
        except Exception as e:
            print(f"    [WARN] links {ds_name}: {e}")

    if new_links:
        db.bulk_save_objects(new_links)
        db.commit()
        print(f"    Thêm {len(new_links)} liên kết thuốc-bệnh mới")
    else:
        print("    Không có liên kết thuốc-bệnh mới")


# ── main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    print("=" * 60)
    print(" SEED ALL DATASETS — C-dataset và F-dataset vào DB")
    print("=" * 60)

    print("\n[1] Khởi tạo bảng mới (nếu chưa có)...")
    init_db()
    print("    OK — đã tạo/kiểm tra bảng dataset_drugs, dataset_diseases, dataset_proteins, dataset_links")

    db = SessionLocal()
    try:
        print("\n[2] Kiểm tra trạng thái DB hiện tại:")
        print(f"    Drugs    : {db.query(Drug).count()}")
        print(f"    Diseases : {db.query(Disease).count()}")
        print(f"    Proteins : {db.query(Protein).count()}")
        print(f"    Links    : {db.query(DrugDiseaseLink).count()}")

        print("\n[3] Upsert vào bảng chính (thêm thuốc/bệnh/protein mới từ C, F)...")
        upsert_main_tables(db)

        print("\n[4] Seed bảng dataset_* cho tất cả 3 dataset...")
        for ds in DATASETS:
            seed_dataset_tables(db, ds)

        print("\n[5] Thống kê sau cập nhật:")
        print(f"    Drugs    : {db.query(Drug).count()}")
        print(f"    Diseases : {db.query(Disease).count()}")
        print(f"    Proteins : {db.query(Protein).count()}")
        print(f"    Links    : {db.query(DrugDiseaseLink).count()}")
        from app.models import DatasetDrug as DD
        for ds in DATASETS:
            cnt = db.query(DD).filter(DD.dataset == ds).count()
            print(f"    DatasetDrug [{ds}]: {cnt}")

    except Exception as exc:
        db.rollback()
        print(f"\n[ERROR] {exc}")
        raise
    finally:
        db.close()

    print("\n Hoàn tất!\n")


if __name__ == "__main__":
    main()
