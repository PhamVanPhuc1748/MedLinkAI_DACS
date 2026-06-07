# Cấu Trúc Hệ Thống (Bản Dùng Lại Cho AI - Tiết Kiệm Token)

## 1) Mục tiêu file này

File này là "bộ nhớ dự án" để AI đọc nhanh trước khi làm việc.

- Mục tiêu: không phải đọc lại toàn bộ codebase từ đầu.
- Cách dùng: mỗi phiên mới, cho AI đọc file này trước, sau đó chỉ mở thêm file liên quan trực tiếp đến task.
- Quy tắc: cập nhật mục `Delta cập nhật` sau mỗi thay đổi lớn.

## 2) Tóm tắt 30 giây

- Tên dự án: `model_GNN_new` (MedLink AI).
- Nghiệp vụ chính: dự đoán liên kết Thuốc - Bệnh bằng GNN (FuzzyGCN), có backend API + frontend Streamlit.
- Dữ liệu: nằm trong `dataset/` với các bộ `B-dataset`, `C-dataset`, `F-dataset`.
- Trọng số/metric: nằm trong `weights/`.
- Huấn luyện có 2 script chính:
  - Script đầy đủ (khuyến nghị): `src/backend/app/ai/huan_luyen.py`.
  - Auto-tune: `src/training/auto_tune.py`.

## 3) Kiến trúc tổng thể

```
model_GNN_new/                         <- Project root
├── main.py                            <- Launcher chính (backend + frontend)
├── requirements.txt
├── .gitignore
├── db_config.json
│
├── dataset/                           <- Dữ liệu B/C/F-dataset (CSV)
├── weights/                           <- Trọng số model .pth + kfold_metrics.json
├── lib/                               <- JS libraries (vis, tom-select, bindings)
│
└── src/
    ├── backend/                       <- FastAPI backend
    │   └── app/
    │       ├── ai/                    <- Model AI core
    │       ├── api/routes.py          <- API endpoints
    │       ├── models.py, schemas.py
    │       ├── database.py, security.py
    │
    ├── frontend/                      <- Streamlit frontend
    │   ├── app_modern.py              <- Entry point UI
    │   └── app/
    │       ├── pages/                 <- admin.py, auth.py, user.py, landing.py
    │       ├── services/api_client.py
    │       ├── ui/theme.py, components.py
    │       └── state.py, config.py
    │
    ├── data/                          <- JSON data store
    │   ├── *.json (drugs, diseases, proteins, links, users...)
    │   ├── json_store.py, json_repo.py
    │   └── disease_translator.py, omim_viet_dict.py
    │
    ├── scripts/                       <- Scripts quản trị
    │   ├── database/                  <- Scripts liên quan database
    │   │   ├── setup_database.py      <- Khởi tạo SQL Server (gọi bởi main.py)
    │   │   ├── seed_all_datasets.py
    │   │   ├── seed_sqlserver.py
    │   │   ├── cap_nhat_dtb.py
    │   │   ├── clear_db.py
    │   │   ├── check_db.py
    │   │   └── generate_disease_names.py
    │   │
    │   └── utils/                     <- Scripts tiện ích chung
    │       ├── _test_import.py
    │       ├── check_syntax.py
    │       └── run_seed.ps1
    │
    ├── training/                      <- Scripts huấn luyện AI
    │   ├── auto_tune.py               <- Tự động tìm siêu tham số
    │   ├── train_logger.py            <- Logger kết quả train
    │   ├── patch_network.py           <- Patch frontend visualization
    │   ├── train_logs/                <- Log huấn luyện (jsonl, csv)
    │   └── lich_su_thong_so_train/    <- Lịch sử thông số trial
    │
    └── cautruchethong/                <- Tài liệu hệ thống
        └── cautruchethong.md
```

## 4) Bản đồ file quan trọng theo vai trò

### 4.1 Chạy hệ thống

- `main.py`: khởi động toàn bộ ứng dụng (backend + UI).
- `src/backend/app/__init__.py`: entry FastAPI app.
- `src/frontend/app_modern.py`: entry Streamlit UI.

### 4.2 AI Model và Train

- `src/backend/app/ai/mo_hinh_ai.py`: định nghĩa `FuzzyGCN`.
- `src/backend/app/ai/fuzzy_layer.py`: lớp fuzzy (Gaussian + triangular).
- `src/backend/app/ai/gcn_flow.py`: GCN flow, edge weight, decoder MLP.
- `src/backend/app/ai/gnn_algorithm.py`: xử lý đồ thị dị thể.
- `src/backend/app/ai/model_factory.py`: khởi tạo model theo cấu hình.
- `src/backend/app/ai/huan_luyen.py`: pipeline train đầy đủ (KFold).
- `src/backend/app/ai/inference_service.py`: nạp model và suy luận.
- `src/training/auto_tune.py`: tự động tìm siêu tham số.
- `src/training/train_logger.py`: logger lưu kết quả train.

### 4.3 API và DB

- `src/backend/app/api/routes.py`: endpoint chính.
- `src/backend/app/models.py`: ORM models.
- `src/backend/app/schemas.py`: Pydantic schemas.
- `src/backend/app/database.py`: cấu hình kết nối DB/session.
- `src/backend/app/security.py`: hash/verify mật khẩu, auth utils.

### 4.4 Database Scripts

- `src/scripts/database/setup_database.py`: khởi tạo SQL Server (tự động gọi bởi main.py).
- `src/scripts/database/seed_all_datasets.py`: seed B/C/F dataset vào DB.
- `src/scripts/database/seed_sqlserver.py`: seed SQL Server.
- `src/scripts/database/clear_db.py`: xóa dữ liệu.
- `src/scripts/database/check_db.py`: kiểm tra kết nối.

### 4.5 Frontend app

- `src/frontend/app/pages/admin.py`, `auth.py`, `user.py`: trang chức năng.
- `src/frontend/app/services/api_client.py`: gọi API.
- `src/frontend/app/ui/theme.py`, `components.py`: UI system.
- `src/frontend/app/state.py`, `config.py`: state/config.

## 5) Luồng dữ liệu AI

1. Đọc feature thuốc + bệnh từ CSV.
2. Đọc cạnh dương drug-disease.
3. Sinh cạnh âm theo `negative-rate`.
4. Gộp thành bài toán phân loại nhị phân link prediction.
5. Chia `StratifiedKFold`.
6. Mỗi fold train `FuzzyGCN` rồi đánh giá AUC/AUPR/F1...
7. Lưu best weight theo fold và lưu `kfold_metrics.json`.

## 6) Lệnh thao tác thường dùng

```powershell
# Chạy full app
python main.py

# Chỉ chạy backend API
python main.py --api-only

# Chạy train AI
python src/backend/app/ai/huan_luyen.py --dataset B-dataset

# Auto-tune siêu tham số
python src/training/auto_tune.py --dataset C-dataset --trials 20

# Kiểm tra database
python src/scripts/database/check_db.py

# Seed dữ liệu vào DB
python src/scripts/database/seed_all_datasets.py

# Xem leaderboard kết quả train
python src/training/train_logger.py leaderboard
```

## 7) Quy ước khi làm việc với AI (để tiết kiệm token)

- Bước 1: luôn gửi file này trước.
- Bước 2: chỉ định rõ phạm vi file cần sửa.
- Bước 3: yêu cầu AI "không đọc toàn bộ repo".
- Bước 4: nếu task nhỏ, chỉ cho AI mở đúng 1-3 file.
- Bước 5: sau khi sửa xong, cập nhật `Delta cập nhật`.

## 8) Template yêu cầu sửa code chuẩn

```text
Context:
- Tôi đã có file tổng quan: src/cautruchethong/cautruchethong.md
- Task hiện tại: <task>

Phạm vi:
- Được đọc/sửa: <file A>, <file B>
- Không đụng vào: <file C>, <module D>

Yêu cầu kỹ thuật:
- Đầu vào:
- Đầu ra:
- Edge cases:
- Tiêu chí hoàn thành:

Sau khi làm xong:
- Cho tôi patch tóm tắt theo từng file.
- Nêu lệnh test ngắn gọn.
```

## 9) Delta cập nhật (chỉ thêm mới, không xoá lịch sử)

### [2026-05-31] Sắp xếp lại cấu trúc thư mục

- File ảnh hưởng: Tất cả scripts ở root, main.py
- Thay đổi chính:
  - `auto_tune.py`, `train_logger.py`, `patch_network.py` -> `src/training/`
  - `train_logs/`, `lich_su_thong_so_train/` -> `src/training/`
  - `setup_database.py`, `seed_*.py`, `cap_nhat_dtb.py`, `clear_db.py`, `check_db.py`, `generate_disease_names.py` -> `src/scripts/database/`
  - `_test_import.py`, `check_syntax.py`, `run_seed.ps1` -> `src/scripts/utils/`
  - `main.py` cập nhật đường dẫn `setup_database.py`
  - Tất cả file đã cập nhật ROOT = Path(__file__).resolve().parent.parent.parent
- Ảnh hưởng API/DB: Không
- Cần AI chú ý lần sau: Root scripts không còn ở root nữa. Dùng đường dẫn mới src/scripts/ và src/training/.

## Phụ lục A - Danh sách module Python hiện có (snapshot)

- Root: `main.py` (launcher duy nhất còn lại ở root)
- Backend AI: `src/backend/app/ai/*`
- Backend API/DB: `src/backend/app/api/*`, `models.py`, `schemas.py`, `database.py`, `security.py`
- Frontend: `src/frontend/app_modern.py`, `src/frontend/app/*`
- Data: `src/data/*.json`, `src/data/*.py`
- Training scripts: `src/training/auto_tune.py`, `src/training/train_logger.py`, `src/training/patch_network.py`
- Database scripts: `src/scripts/database/*.py`
- Utils: `src/scripts/utils/*`
