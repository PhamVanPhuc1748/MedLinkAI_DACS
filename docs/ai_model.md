# AI Model Module (`backend/app/ai/gcn_model.py` va `backend/app/ai/mo_hinh_ai.py`)

## 1) Mục tiêu
Module này định nghĩa mô hình `FuzzyGCN` cho bài toán dự đoán tương tác Thuốc - Bệnh (DDA) dựa trên đồ thị hai phía (`HeteroData`) và cơ chế fuzzy để giảm nhiễu. File `mo_hinh_ai.py` là phiên bản có chú thích tiếng Việt chi tiết theo yêu cầu học tập.

## 2) Thành phần chính

### `FuzzyLayer`
- Cơ chế: Hàm thành viên Gaussian.
- Công thức: `membership = exp(-((x - mu)^2) / (2*sigma^2))`.
- Đầu ra: `x * membership`.
- Ý nghĩa: Làm giảm ảnh hưởng của các đặc trưng lệch/ồn trước khi qua GCN.

### `FuzzyGCN`
- Input:
  - `drug_in_channels`: số chiều đặc trưng nút thuốc.
  - `disease_in_channels`: số chiều đặc trưng nút bệnh.
- Kiến trúc:
  1. Mã hóa đặc trưng thuốc/bệnh về cùng không gian ẩn (Linear).
  2. Áp dụng `FuzzyLayer` để khử nhiễu.
  3. Chuyển `HeteroData` -> homogeneous graph.
  4. Chạy nhiều lớp `GCNConv` (cấu hình qua `so_lop_gcn`) với `edge_weight` dựa trên độ tương đồng cosine đã fuzzy hóa.
- Output:
  - Biểu diễn nút sau GCN (phù hợp để xây scoring head trong bước huấn luyện/suy luận thật).

## 3) Hàm suy luận mô phỏng
### `predict_top_k(drug_id, k=5)`
- Cố gắng load trọng số từ file `.pth` qua `load_weights()`.
- Sinh xác suất mô phỏng ổn định (seed theo `drug_id`) để phục vụ tích hợp API/frontend sớm.
- Trả về danh sách Top-K dạng:
  - `disease_id`
  - `disease_name`
  - `score`

## 4) Luồng tích hợp Backend
1. API nhận đầu vào (`drug_id` hoặc tên thuốc).
2. Backend chuẩn hóa dữ liệu thành `HeteroData`.
3. Gọi `model.predict_top_k(...)`.
4. Lưu từng kết quả vào `predictions_history`.
5. Trả JSON cho frontend hiển thị Top-K.

## 5) Giao tiếp với các file khác
- `backend/app/models.py`:
  - Cung cấp dữ liệu thuốc/bệnh để tạo đặc trưng nút.
  - Nhận dữ liệu kết quả để lưu lịch sử dự đoán.
- `backend/app/main.py`:
  - Khởi tạo model singleton, gọi API suy luận.
- `frontend/app/pages/user.py`:
  - Nhận kết quả Top-K, gọi `show_split_result_table()` để hiển thị 2 cột.
- `frontend/app/ui/components.py`:
  - `show_split_result_table(results, entity_label)`: Phân loại kết quả thành 2 nhóm song song:
    - **Cột trái** (`known=True`): ✅ Nhóm Điều Trị — liên kết có trong dataset, đã xác nhận.
    - **Cột phải** (`known=False`): ⚠️ Nguy Cơ / Tác Dụng Phụ — AI dự đoán mới, cần kiểm chứng.
  - `_render_group_table(group, entity_label)`: Render bảng HTML điểm xác suất cho từng nhóm; hiển thị `st.info()` nếu nhóm rỗng.
  - `show_result_table()`: Hàm cũ, giữ lại để tương thích ngược — không dùng trên UI chính.
- `backend/app/ai/huan_luyen.py`:
  - Huấn luyện và đánh giá mô hình, lưu checkpoint và metadata.

## 6) Gợi ý mở rộng
- Bổ sung pipeline train/eval riêng (`train.py`, `inference.py`).
- Thay phần mô phỏng trong `predict_top_k` bằng forward thực trên đồ thị động.
- Thêm calibration (Platt/Temperature scaling) để score phản ánh xác suất tốt hơn.
