# Cấu Trúc Hệ Thống (Bản Dùng Lại Cho AI - Tiết Kiệm Token)

## 1) Mục tiêu file này

File này là “bộ nhớ dự án” để AI đọc nhanh trước khi làm việc.

- Mục tiêu: không phải đọc lại toàn bộ codebase từ đầu.
- Cách dùng: mỗi phiên mới, cho AI đọc file này trước, sau đó chỉ mở thêm file liên quan trực tiếp đến task.
- Quy tắc: cập nhật mục `Delta cập nhật` sau mỗi thay đổi lớn.

## 2) Tóm tắt 30 giây

- Tên dự án: `model_GNN_new` (MedLink AI).
- Nghiệp vụ chính: dự đoán liên kết Thuốc - Bệnh bằng GNN (FuzzyGCN), có backend API + frontend Streamlit.
- Dữ liệu: nằm trong `dataset/` với các bộ `B-dataset`, `C-dataset`, `F-dataset`.
- Trọng số/métric: nằm trong `weights/`.
- Huấn luyện có 2 script chính.
- Script đơn giản: `src/Ai/huan_luyen.py`.
- Script đầy đủ hơn (khuyến nghị): `src/backend/app/ai/huan_luyen.py`.

## 3) Kiến trúc tổng thể

- `main.py` (root): launcher chạy backend + frontend.
- `src/backend/`: API, database, AI core.
- `src/frontend/`: UI Streamlit phía client.
- `src/backend/app/ai/`: mô hình, thuật toán GNN, train, inference.
- `src/backend/app/api/`: route API.
- `src/backend/app/models.py`, `schemas.py`, `database.py`, `security.py`: lớp dữ liệu và bảo mật.

## 4) Bản đồ file quan trọng theo vai trò

### 4.1 Chạy hệ thống

- `main.py`: khởi động toàn bộ ứng dụng.
- `src/backend/main.py`: entry backend.
- `src/frontend/streamlit_app.py`: entry frontend.

### 4.2 AI Model và Train

- `src/backend/app/ai/mo_hinh_ai.py`: định nghĩa `FuzzyGCN`.
- `src/backend/app/ai/fuzzy_layer.py`: lớp fuzzy (Gaussian + triangular).
- `src/backend/app/ai/gcn_flow.py`: GCN flow, edge weight, decoder MLP.
- `src/backend/app/ai/gnn_algorithm.py`: chuyển đồ thị dị thể sang đồng nhất và xử lý liên quan.
- `src/backend/app/ai/model_factory.py`: khởi tạo model theo cấu hình.
- `src/backend/app/ai/huan_luyen.py`: pipeline train đầy đủ (KFold, loss kết hợp, early stopping, scheduler).
- `src/Ai/huan_luyen.py`: pipeline train bản rút gọn.
- `src/backend/app/ai/inference_service.py`: nạp model và suy luận.

### 4.3 API và DB

- `src/backend/app/api/routes.py`: endpoint chính.
- `src/backend/app/models.py`: ORM models.
- `src/backend/app/schemas.py`: Pydantic schemas.
- `src/backend/app/database.py`: cấu hình kết nối DB/session.
- `src/backend/app/security.py`: hash/verify mật khẩu, auth utils.

### 4.4 Frontend app

- `src/frontend/app/pages/admin.py`, `auth.py`, `user.py`: trang chức năng.
- `src/frontend/app/services/api_client.py`: gọi API.
- `src/frontend/app/ui/theme.py`, `components.py`: UI system.
- `src/frontend/app/state.py`, `config.py`: state/config.

## 5) Luồng dữ liệu AI (chuẩn để AI hiểu nhanh)

1. Đọc feature thuốc + bệnh từ CSV.
2. Đọc cạnh dương drug-disease.
3. Sinh cạnh âm theo `negative-rate`.
4. Gộp thành bài toán phân loại nhị phân link prediction.
5. Chia `StratifiedKFold`.
6. Mỗi fold train `FuzzyGCN` rồi đánh giá AUC/AUPR/F1...
7. Lưu best weight theo fold và lưu `kfold_metrics.json`.

## 6) Khác biệt 2 script train (quan trọng)

- `src/Ai/huan_luyen.py`: đơn giản hơn, phù hợp chạy nhanh hoặc thử nghiệm.
- `src/backend/app/ai/huan_luyen.py`: đầy đủ hơn, có:
- Chuẩn hoá đặc trưng (tuỳ chọn).
- Loss kết hợp `BCE + Label Smoothing + Margin Ranking`.
- AdamW + ReduceLROnPlateau.
- Gradient clipping.
- Early stopping theo AUC.
- Nên ưu tiên file backend cho kết quả nghiên cứu/chạy chuẩn.

## 7) Lệnh thao tác thường dùng

- Chạy full app: `python main.py`
- Chạy train backend AI: `python src/backend/app/ai/huan_luyen.py --dataset B-dataset`
- Chạy train bản đơn giản: `python src/Ai/huan_luyen.py --dataset B-dataset`

## 8) Quy ước khi làm việc với AI (để tiết kiệm token)

- Bước 1: luôn gửi file này trước.
- Bước 2: chỉ định rõ phạm vi file cần sửa.
- Bước 3: yêu cầu AI “không đọc toàn bộ repo”.
- Bước 4: nếu task nhỏ, chỉ cho AI mở đúng 1-3 file.
- Bước 5: sau khi sửa xong, cập nhật `Delta cập nhật`.

## 9) Prompt mẫu tái sử dụng (copy-paste)

```text
Đọc file src/cautruchethong/cautruchethong.md trước để lấy context dự án.
Chỉ làm việc trong phạm vi file: <danh_sach_file>.
Không quét toàn bộ repo nếu không cần.
Mục tiêu: <mục_tiêu_cụ_thể>.
Ràng buộc: giữ nguyên API cũ / không đổi DB schema / chỉ sửa tối thiểu.
Trả lời gồm: (1) thay đổi gì, (2) file nào, (3) cách test nhanh.
```

## 10) Template yêu cầu sửa code chuẩn

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

## 11) Delta cập nhật (chỉ thêm mới, không xoá lịch sử)

Mục này là phần quan trọng nhất để giảm token cho phiên sau. Mỗi lần đổi kiến trúc/chức năng, chỉ cần thêm 3-10 dòng.

Mẫu:

```text
## [YYYY-MM-DD] Tên thay đổi ngắn
- File ảnh hưởng: ...
- Thay đổi chính: ...
- Ảnh hưởng API/DB: Có|Không
- Cần AI chú ý lần sau: ...
```

## 12) Chỉ số chất lượng của file này

Nếu file này tốt, AI mới nên:

- Hiểu hệ thống mà không cần đọc lại toàn bộ source.
- Xác định đúng file cần sửa trong < 1 phút.
- Không sửa lan sang module không liên quan.

---

## Phụ lục A - Danh sách module Python hiện có (snapshot)

- Root scripts: `main.py`, `seed_sqlserver.py`, `clear_db.py`
- Backend AI: `src/backend/app/ai/*`
- Backend API/DB: `src/backend/app/api/*`, `models.py`, `schemas.py`, `database.py`, `security.py`
- Frontend: `src/frontend/*`
- Script train phụ: `src/Ai/huan_luyen.py`

Ghi chú: danh sách chi tiết từng hàm/class có thể rất dài và tốn token. Chỉ mở file thật khi task cần.
