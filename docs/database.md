# Database Module (`backend/app/models.py`)

## 1) Mục tiêu
Module này định nghĩa toàn bộ cấu trúc dữ liệu quan hệ cho hệ thống DDA bằng SQLAlchemy ORM. Đây là lớp trung tâm để FastAPI thao tác với SQLite.

## 2) Bảng dữ liệu

### `users`
- `id` (Integer, PK): Khóa chính người dùng.
- `username` (String, unique, index): Tên đăng nhập duy nhất.
- `password_hash` (String): Mật khẩu đã băm.
- `role` (String): Vai trò (`admin` hoặc `user`).

### `drugs`
- `id` (Integer, PK): Khóa chính thuốc.
- `name` (String, unique, index): Tên thuốc.
- `features` (Text): Đặc trưng của thuốc (đề xuất lưu JSON string/vector serialized).

### `diseases`
- `id` (Integer, PK): Khóa chính bệnh.
- `name` (String, unique, index): Tên bệnh.
- `features` (Text): Đặc trưng bệnh (đề xuất lưu JSON string/vector serialized).

### `predictions_history`
- `id` (Integer, PK): Khóa chính bản ghi dự đoán.
- `user_id` (FK -> `users.id`): Người thực hiện truy vấn.
- `drug_name` (String): Tên thuốc đầu vào tại thời điểm dự đoán.
- `disease_name` (String): Tên bệnh trong kết quả dự đoán.
- `score` (Float): Điểm tin cậy mô hình trả về.
- `timestamp` (DateTime): Thời gian tạo bản ghi (UTC).

## 3) Quan hệ dữ liệu
- `User` 1 - N `PredictionHistory`:
  - Một người dùng có nhiều lượt dự đoán.
  - Dùng `back_populates` 2 chiều để truy cập ORM thuận tiện.

## 4) Luồng logic sử dụng
1. FastAPI tạo session DB từ engine SQLite.
2. API Auth đọc/ghi bảng `users`.
3. API Admin CRUD bảng `drugs`, `diseases`.
4. API Dự đoán ghi kết quả vào `predictions_history`.
5. API Lịch sử truy vấn `predictions_history` theo `user_id`.

## 5) Giao tiếp với các file khác
- `backend/app/main.py` (sẽ tạo ở bước sau):
  - Import model để migrate/tạo bảng và query dữ liệu.
- `backend/app/ai/gcn_model.py`:
  - Dùng dữ liệu `drugs`, `diseases` làm đầu vào sinh đồ thị/đặc trưng.
- `frontend/app.py`:
  - Gọi API backend, không truy cập DB trực tiếp.

## 6) Ghi chú triển khai
- Cột `features` dùng kiểu `Text` để linh hoạt với vector kích thước khác nhau.
- Có thể nâng cấp sang JSON type khi đổi sang PostgreSQL.
- Nên thêm Alembic để version hóa schema trong giai đoạn hoàn thiện.