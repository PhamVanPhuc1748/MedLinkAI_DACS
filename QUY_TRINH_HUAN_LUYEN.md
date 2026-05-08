# Quy trình Hoạt động của Mô hình Huấn luyện (FuzzyGCN)

Tài liệu này mô tả chi tiết từng bước hoạt động của quá trình huấn luyện mô hình GNN theo nội dung mã nguồn của tệp `backend/app/ai/huan_luyen.py`. Hệ thống thực thi quá trình dự đoán tương tác (link prediction) giữa Thuốc (Drug) và Bệnh (Disease).

---

## Bước 1: Thiết lập và Khởi tạo Cấu hình (Initialization & Configuration)
- **Đọc tham số dòng lệnh:** Sử dụng thư viện `argparse` để đọc các tham số chạy từ Terminal (như tên dataset, số fold, learning rate, epoch...).
- **Cấu hình siêu tham số (Hyperparameters):** Lưu trữ toàn bộ các thông số liên quan qua lớp `CauHinh` dạng Dataclass, quản lý cấu trúc mạng, thiết bị huấn luyện (GPU/CPU) và ngưỡng kích hoạt (early stopping, K-fold count).
- **Cố định ngẫu nhiên (Seed Setting):** Hàm `dat_seed` thiết lập hạt giống khởi tạo cho các hệ thống: `random`, `numpy`, `torch` và `torch.cuda` nhằm đảm bảo khả năng tái tạo (reproducibility).

## Bước 2: Nạp và Tiền xử lý Dữ liệu (Data Loading & Preprocessing)
- **Tải các tệp ma trận:** Chương trình đọc nội dung từ 3 luồng tệp CSV:
  - Tập các Liên kết (Cạnh tích cực): `DrugDiseaseAssociationNumber.csv`
  - Khuôn mẫu đặc trưng của Thuốc: `DrugFingerprint.csv`
  - Khuôn mẫu đặc trưng của Bệnh: `DiseaseFeature.csv`
- **Căn chỉnh và Chuẩn hoá (Normalization):** Biến đổi chiều của các ma trận để quy chuẩn về ma trận 2D thống nhất. Đặc trưng của thuốc và bệnh được đi qua `StandardScaler` giúp dữ liệu mang tính cân bằng thang đo nhằm tối ưu độ dốc gradient lúc huấn luyện.
- **Xây dựng Mẫu Âm (Negative Sampling):** Hàm `tao_canh_am` tổng hợp tạo rác những tập dữ liệu những cạnh liên kết giữa thuốc và bệnh **không tồn tại** thật sự theo 1 tỷ lệ nhất định (`ti_le_am` mặc định 1.2 x Lượng mẫu dương).
- **Gộp Dataset:** Tổng hợp mẫu Dương và Âm thành 1 ma trận Liên Kết Toàn Bộ chung để thiết lập quy mô phân loại nhị phân.

## Bước 3: Tạo Đồ thị Không đồng nhất (Heterogeneous Graph Creation)
Hàm `tao_do_thi` trực tiếp xử lý dữ liệu qua kiến trúc *PyTorch Geometric* (`HeteroData`):
- **Khởi tạo Nodes (Các Nút):** Nút Thuốc gán nhãn `drug` với features nạp từ ma trận chuẩn hóa. Nút Bệnh được gán bộ nhận dạng `disease`.
- **Khởi tạo Edges (Cạnh Liên Kết):** Sinh ra chuỗi liên kết có định hướng kép: `[drug, interacts, disease]` và `[disease, rev_interacts, drug]`. 
  > **Quan trọng:** Tiến trình cấu trúc này chỉ áp dụng tạo cấu trúc cho các Cạnh Dương của tệp để huấn luyện, nhằm tránh hiện tượng "tiết lộ trước thông tin" ở dữ liệu kiểm thử.

## Bước 4: Thiết lập K-Fold Cross Validation
- Để ngăn sự phụ thuộc/học lệch vào một lần phân tách ngẫu nhiên duy nhất, quá trình được đặt trên vòng lặp của **Stratified K-Fold** (mặc định 10 phần). 
- Chia đảm bảo việc cân bằng nhãn phân phối giữa các nhánh kiểm tra và huấn luyện tại mỗi vòng là đồng tỷ lệ.

## Bước 5: Quá trình Huấn luyện Cốt lõi trên mỗi Fold (Training Loop)
Tại mỗi lần gấp lại (Fold), mô hình tiến hành:
1. **Khởi tạo Kiến trúc GNN:** Gây dựng nhân GNN (FuzzyGCN).
2. **Optimizer & Loss:** Khởi chạy thuật toán tối ưu `Adam` và Hệ số lịch trình độ học `ReduceLROnPlateau`. Đặt `BCEWithLogitsLoss` dùng tính toán Lỗi mất mát nhị phân.
3. **Epoch Loop:** Đi vào vòng lặp của từng Epochs:
   - **Thực Hiện Forward Pass:**  Gửi dữ liệu qua các khối GNN để rút trích những Nhúng Ẩn (Embeddings). Đưa embeddings chấm tích vô hướng (Dot Product) ở hàm `giai_ma_diem` để chấm ra điểm Tương tác ước tính bằng Logits.
   - **Áp Dụng AMP:** Nếu thiết bị hỗ trợ, thuật toán tự thực hiện huấn luyện ở chế độ độ chính xác hỗn hợp nửa phao (`torch.float16`) giúp tốc độ tối ưu nhanh hơn.
   - **Tính Toán Backward:** Cắt đạo hàm tràn (`clip_grad`) theo mức 0.8 và đi ngược backpropagation cập nhật tham số mô hình.

## Bước 6: Đánh giá, Tìm Ngưỡng & Early Stopping (Evaluation)
Trong cùng lúc với mỗi Epoch Training:
- Quá trình chạy điểm của tập Train nhằm tìm điểm cắt Threshold của F1 một cách tối ưu (`tim_nguong_toi_uu_f1`) chứ không ngây ngô dùng ngưỡng 0.5 thuần.
- Chấm điểm cho tập Validation/Test để đo lường 7 tiêu chí: **AUC, AUPR, Accuracy, Precision, Recall, F1, MCC**.
- **Early Stopping & Checkpoint:** Nếu mô hình ghi nhận AUC ở Fold tốt nhất sẽ Lưu Trọng Số Model (`best_fold_i.pth`). Nếu qua `patience` mốc (35 Epochs) mà AUC không cải thiện sẽ gọi cờ **Dừng Sớm** chống Overfitting và thoát vòng lặp của Fold hiện tại.

## Bước 7: Kết Sơ và Nộp Kết Quả (Aggregation)
Sau khi vòng 10 Fold đã kết thúc thành công:
- Thực hiện cộng dồn 7 chỉ số và chia trung bình tất cả những số trên 10 Fold đó ra thành tích báo cáo chuẩn.
- In xuất kết quả cuối cùng bên cửa sổ lệnh.
- Xuất kết xuất dữ kiện đó thành file lưu tự động trong ổ theo định dạng `kfold_metrics.json` nằm tại thư mục `weights/`.
