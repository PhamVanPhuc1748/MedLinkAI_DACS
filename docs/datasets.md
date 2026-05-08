# Giai thich tung file trong cac dataset (B-dataset, C-dataset, F-dataset)

Tai lieu nay giai thich tung file mot cach don gian de nguoi chua biet gi van hieu duoc. Ba thu muc B/C/F deu co cung cau truc va y nghia tuong tu.

## 1) Tep chinh ve lien ket

### `DrugDiseaseAssociationNumber.csv`
- **Y nghia:** Danh sach cac cap Thuoc - Benh da biet la co lien quan.
- **Cot:** `drug`, `disease`
  - `drug` la chi so (index) cua thuoc.
  - `disease` la chi so (index) cua benh.
- **Vi du dong:** `0,3` nghia la thuoc co chi so 0 lien quan voi benh chi so 3.
- **Dung de lam gi:** Day la "nhan dung" de mo hinh hoc xem cap nao la dung.

### `DrugProteinAssociationNumber.csv`
- **Y nghia:** Danh sach cac cap Thuoc - Protein lien quan.
- **Cot:** `drug`, `protein`
  - `drug` la chi so thuoc.
  - `protein` la chi so protein.
- **Dung de lam gi:** Co the dung de mo rong mo hinh theo do thi 3 lop (Thuoc - Protein - Benh).

### `ProteinDiseaseAssociationNumber.csv`
- **Y nghia:** Danh sach cac cap Protein - Benh lien quan.
- **Cot:** `disease`, `protein`
  - `disease` la chi so benh.
  - `protein` la chi so protein.
- **Dung de lam gi:** Mo rong mo hinh theo duong noi qua protein.

## 2) Tep thong tin ten va mo ta

### `DrugInformation.csv`
- **Y nghia:** Danh sach ten thuoc, ma thuoc, va bieu dien phan tu.
- **Cot:** `name`, `id`, `smiles`
  - `name`: ten thuoc de nguoi doc.
  - `id`: ma thuoc (VD: DB00349).
  - `smiles`: chuoi mo ta cau truc hoa hoc.
- **Dung de lam gi:** Hien thi ten thuoc va lien ket voi chi so thuoc.

### `ProteinInformation.csv`
- **Y nghia:** Danh sach protein va chuoi amino acid.
- **Cot:** `id`, `sequence`
  - `id`: ma protein.
  - `sequence`: chuoi amino acid (chu cai A, C, D, ...).
- **Dung de lam gi:** Mo ta protein khi can mo rong mo hinh.

### `Allnode.csv` / `AllNode.csv`
- **Y nghia:** Danh sach tong hop cac nut (thuc the) va chi so.
- **Vi du:** `0,clobazam`
- **Dung de lam gi:** Tra cuu nhanh id -> ten.

## 3) Tep dac trung (feature)

### `DrugFingerprint.csv`
- **Y nghia:** Ma tran dac trung cua thuoc.
- **Hang:** moi hang la 1 thuoc.
- **Cot:** moi cot la 1 dac trung (0/1 hoac gia tri).
- **Dung de lam gi:** Dau vao cua mo hinh cho nut thuoc.

### `Drug_mol2vec.csv`
- **Y nghia:** Dac trung thuoc tu mo hinh mol2vec.
- **Gia tri:** so thuc (co the am/duong).
- **Dung de lam gi:** Dac trung khoa hoc hoa hoc nang cao.

### `DrugGIP.csv`
- **Y nghia:** Ma tran tuong dong thuoc theo GIP (Gaussian Interaction Profile).
- **Hang/Cot:** ca hang va cot la chi so thuoc.
- **Gia tri:** muc do tuong dong (0..1).
- **Dung de lam gi:** Dung lam dac trung bo sung.

### `DiseaseFeature.csv`
- **Y nghia:** Dac trung cua benh.
- **Hang:** moi hang la 1 benh (ten benh o dau dong).
- **Cot:** cac gia tri so thuc.
- **Dung de lam gi:** Dau vao cua mo hinh cho nut benh.

### `DiseaseGIP.csv`
- **Y nghia:** Ma tran tuong dong benh theo GIP.
- **Hang/Cot:** ca hang va cot la chi so benh.
- **Gia tri:** muc do tuong dong (0..1).

### `DiseasePS.csv`
- **Y nghia:** Ma tran tuong dong benh theo PS (Phenotype Similarity).
- **Hang/Cot:** ca hang va cot la chi so benh.
- **Gia tri:** muc do tuong dong (0..1).

### `Protein_ESM.csv`
- **Y nghia:** Dac trung protein tu mo hinh ESM (Embedding).
- **Hang:** moi hang la 1 protein.
- **Cot:** embedding so thuc.

## 4) Tep do thi / lien ket tong hop

### `Alledge.csv`
- **Y nghia:** Danh sach tat ca canh cua do thi.
- **Cot (vi du):** `0,269` nghia la co canh giua nut 0 va 269.
- **Dung de lam gi:** Xay do thi tong hop neu can.

### `adj.csv`
- **Y nghia:** Ma tran ke (adjacency matrix).
- **Hang/Cot:** la chi so nut.
- **Gia tri:** 1 neu co canh, 0 neu khong co.

## 5) Cach lien ket cac chi so
- Chi so **drug** lay theo dong trong `DrugInformation.csv` hoac `DrugFingerprint.csv`.
- Chi so **disease** lay theo thu tu dong trong `DiseaseFeature.csv`.
- Chi so **protein** lay theo thu tu dong trong `ProteinInformation.csv` hoac `Protein_ESM.csv`.

Neu can mo ta cho tung dataset cu the (B/C/F), chi can noi, minh se them bang so luong dong, so cot, va vi du cho moi file.

## 6) Bang thong ke so dong va so cot (Rows x Cols)

Luu y: Con so duoi day la thong ke thuc te tu file CSV. Mot vai file co the co lech 1 dong so voi so luong thuc the, do co dong tieu de hoac dong chi so.

### B-dataset
| File | Rows | Cols |
|---|---:|---:|
| DrugDiseaseAssociationNumber.csv | 18417 | 2 |
| DrugProteinAssociationNumber.csv | 3111 | 2 |
| ProteinDiseaseAssociationNumber.csv | 5899 | 2 |
| DrugInformation.csv | 270 | 3 |
| ProteinInformation.csv | 1022 | 2 |
| Allnode.csv | 1888 | 2 |
| DrugFingerprint.csv | 270 | 270 |
| Drug_mol2vec.csv | 269 | 301 |
| DrugGIP.csv | 270 | 270 |
| DiseaseFeature.csv | 598 | 65 |
| DiseaseGIP.csv | 599 | 599 |
| DiseasePS.csv | 599 | 599 |
| Protein_ESM.csv | 1021 | 321 |
| Alledge.csv | 27424 | 2 |
| adj.csv | 270 | 599 |

### C-dataset
| File | Rows | Cols |
|---|---:|---:|
| DrugDiseaseAssociationNumber.csv | 2533 | 2 |
| DrugProteinAssociationNumber.csv | 3774 | 2 |
| ProteinDiseaseAssociationNumber.csv | 10735 | 2 |
| DrugInformation.csv | 664 | 3 |
| ProteinInformation.csv | 994 | 2 |
| Allnode.csv | 2065 | 1 |
| DrugFingerprint.csv | 664 | 664 |
| Drug_mol2vec.csv | 663 | 301 |
| DrugGIP.csv | 664 | 664 |
| DiseaseFeature.csv | 409 | 65 |
| DiseaseGIP.csv | 410 | 410 |
| DiseasePS.csv | 410 | 410 |
| Protein_ESM.csv | 993 | 321 |
| Alledge.csv | 17039 | 2 |
| adj.csv | 664 | 410 |

### F-dataset
| File | Rows | Cols |
|---|---:|---:|
| DrugDiseaseAssociationNumber.csv | 1934 | 2 |
| DrugProteinAssociationNumber.csv | 3244 | 2 |
| ProteinDiseaseAssociationNumber.csv | 54266 | 2 |
| DrugInformation.csv | 594 | 4 |
| ProteinInformation.csv | 2742 | 2 |
| Allnode.csv | 3647 | 2 |
| DrugFingerprint.csv | 593 | 593 |
| Drug_mol2vec.csv | 592 | 301 |
| DrugGIP.csv | 593 | 593 |
| DiseaseFeature.csv | 313 | 65 |
| DiseaseGIP.csv | 314 | 314 |
| DiseasePS.csv | 314 | 314 |
| Protein_ESM.csv | 2741 | 321 |
| Alledge.csv | 59441 | 2 |
| adj.csv | 593 | 314 |
