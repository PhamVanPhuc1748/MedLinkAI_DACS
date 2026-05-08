# Huấn Luyện Mô Hình (`backend/app/ai/huan_luyen.py`)

## 1) Mục tiêu
File `huan_luyen.py` dùng để huấn luyện mô hình FuzzyGCN trên các dataset DDA. File này có chú thích tiếng Việt rất chi tiết, phù hợp cho người mới học.

## 2) Khu vực cấu hình (Hyperparameters)
Ngay đầu file có lớp `CauHinhHuanLuyen` và `argparse` cho phép cấu hình:
- Đường dẫn dataset.
- Số vòng lặp (epochs).
- Tốc độ học (learning_rate).
- Weight decay.
- Số lớp GCN.
- Kích thước lớp ẩn và đầu ra.
- Tỉ lệ negative sampling.
- Thiết bị huấn luyện và AMP.

## 3) Luồng huấn luyện
1. Đọc dữ liệu từ CSV và chuẩn hóa số hàng.
2. Xây `HeteroData` cho đồ thị hai phía.
3. Huấn luyện theo từng dataset trong danh sách.
4. Lưu checkpoint `.pth` và metadata `.json` sau mỗi dataset.
5. In ra các chỉ số AUC, AUPR, F1-score bằng tiếng Việt.

## 4) Chỉ số đánh giá
File sử dụng `scikit-learn` để tính:
- AUC (ROC-AUC)
- AUPR (Average Precision)
- F1-score

## 5) Liên kết với các phần khác
- `backend/app/ai/mo_hinh_ai.py`: định nghĩa mô hình FuzzyGCN tiếng Việt.
- `backend/app/ai/test_gui.py`: GUI giúp kiểm thử kết quả.
