# Database Design - Drug Disease AI Platform

## Muc tieu
Co so du lieu duoc thiet ke de phuc vu 4 nhom chuc nang:
- xac thuc nguoi dung
- quan ly du lieu thuoc/benh/lien ket
- luu lich su tra cuu du doan
- thong ke su dung he thong

## Cac bang chinh

### 1) `users`
- `id` (PK)
- `username` (unique)
- `password_hash`
- `role` (`user` | `admin`)

### 2) `drugs`
- `id` (PK, trung voi index thuoc trong dataset)
- `name` (unique)
- `external_id` (nullable)
- `smiles` (nullable)
- `features` (nullable, du phong)

### 3) `diseases`
- `id` (PK, trung voi index benh trong dataset)
- `name` (unique)
- `features` (nullable, du phong)

### 4) `drug_disease_links`
- `id` (PK)
- `drug_id` (FK -> drugs.id)
- `disease_id` (FK -> diseases.id)
- unique constraint: (`drug_id`, `disease_id`)

### 5) `predictions_history`
- `id` (PK)
- `user_id` (FK -> users.id)
- `direction` (`drug_to_disease` | `disease_to_drug`)
- `input_name`
- `target_id`
- `target_name`
- `score` (float 0..1)
- `timestamp` (UTC datetime)

## Luong du lieu
1. Khi backend khoi dong, `init_db()` tao bang neu chua ton tai.
2. API `/api/health` se bootstrap du lieu tu dataset B-dataset vao bang drug/disease/link neu DB dang rong.
3. Moi lan goi endpoint du doan, ket qua top-k duoc ghi vao `predictions_history`.

## Ghi chu mapping ID
- `DiseaseFeature.csv` khong co header, doc voi `header=None`.
- `disease_id` va `drug_id` phai lay tu cung mot dataset de tranh lech ID.
