# Kiến Trúc Các Lớp (Layers) và Quy Trình Huấn Luyện Của Mô Hình FuzzyGCN

Tài liệu này tập trung giải thích mô hình AI theo góc độ luồng chảy của dữ liệu (Data Flow) qua từng Lớp Nơ-ron (Layers) và chi tiết từng bước mà mô hình "học" (Training Loop) trong mã nguồn.

---

## PHẦN 1: CẤU TRÚC CÁC LỚP (LAYERS) TRONG MẠNG NƠ-RON

Mô hình được khai báo bằng PyTorch và đi qua tuần tự 5 khối Layer chính:

### 1. Lớp Đầu Vào (Input Layer)
Dữ liệu thô ban đầu bao gồm 2 ma trận rời rạc:
- Ma trận đặc trưng Thuốc $X_d$: Kích thước `[Số lượng thuốc, Số chiều đặc trưng thuốc]`.
- Ma trận đặc trưng Bệnh $X_p$: Kích thước `[Số lượng bệnh, Số chiều đặc trưng bệnh]`.

### 2. Lớp Logic Mờ (Fuzzy Layer)
- **Code implementation:** Lớp `LopFuzzy` trong `fuzzy_layer.py`.
- **Cấu trúc nơ-ron:** Không sử dụng phép nhân ma trận $W \cdot x + b$ như mạng nơ-ron thường. Lớp này sử dụng **2 Cụm hàm thành viên (Membership functions)**:
  - *Hệ số Gaussian:* $\exp\left(-0.5 \cdot \left(\frac{x - c_{gauss}}{\sigma_{gauss}}\right)^2\right)$
  - *Hệ số Tam giác (Triangular):* Hàm `clamp` giới hạn biên độ.
- **Nhiệm vụ:** Ánh xạ dữ liệu thô (rất nhiễu) thành không gian mờ, giúp mô hình mềm dẻo hơn. Output có cùng kích thước với Input.

### 3. Lớp Chiếu Tuyến Tính (Homogenization / Linear Projection Layer)
- **Cấu trúc nơ-ron:** Các lớp `nn.Linear` (Dense layer) thông thường.
- **Nhiệm vụ:** Thuốc và Bệnh có số chiều đặc trưng khác nhau (ví dụ: Thuốc 881 chiều, Bệnh 300 chiều). Lớp này nén hoặc nội suy các chiều đó về **cùng một kích thước ẩn chung** (`kich_thuoc_an`, mặc định là 512).
- **Kết quả:** Xây dựng xong một không gian "Đồng nhất", Thuốc và Bệnh giờ đây đã có thể "nói chung một ngôn ngữ".

### 4. Khối Tích Chập Đồ Thị (GCN Blocks - Thường có 4 Lớp)
- **Code implementation:** Hàm `truyen_qua_cac_lop_gcn()` trong `gnn_algorithm.py`.
- **Cấu trúc 1 Block GCN:**
  - Tính trọng số cạnh động (Cos Similarity + Gaussian RBF).
  - Tích chập GCN (Gom nhóm thông tin từ hàng xóm).
  - Hàm kích hoạt `ELU(x)` (Tốt hơn ReLU để tránh chết nơ-ron).
  - `LayerNorm(x)` (Chuẩn hóa từng lớp để hội tụ nhanh).
  - Kết nối thặng dư (Residual Add): Lấy đầu ra cộng ngược lại với đầu vào ban đầu.
- **Nhiệm vụ:** Trích xuất thông tin topology của mạng. Đặc trưng của mỗi nút sau khi đi qua 4 block này sẽ chứa thêm thông tin của hàng xóm cách nó tối đa 4 "bước nhảy" (4-hops).

### 5. Bộ Giải Mã (MLP Decoder Layer)
- **Code implementation:** Lớp `GiaiMaMLPN` trong `gcn_flow.py`.
- **Cấu trúc:** Nhận 2 vectơ Embedding (một của Thuốc, một của Bệnh) sau khi đã qua GCN.
  - Phép ghép: `Concat(Vectơ_Thuốc, Vectơ_Bệnh, Vectơ_Thuốc * Vectơ_Bệnh)`.
  - Đi qua mạng MLP: `Linear` $\rightarrow$ `ELU` $\rightarrow$ `Dropout (0.2)` $\rightarrow$ `Linear (1 nơ-ron)`.
- **Đầu ra:** Trả về một con số duy nhất (Logit score). Nếu đưa qua Sigmoid, con số này sẽ nằm trong khoảng `[0, 1]` thể hiện xác suất Thuốc chữa được Bệnh.

---

## PHẦN 2: CÁCH MÔ HÌNH HUẤN LUYỆN (TRAINING PROCESS)

Quá trình "học" (Training) được thiết kế cực kỳ chặt chẽ trong file `huan_luyen.py` để tránh Overfitting và tối ưu hóa tối đa đồ thị mất cân bằng nhãn.

### Bước 1: Tiền Xử Lý & Lấy Mẫu (Preprocessing & Sampling)
- Toàn bộ dữ liệu được chuẩn hóa qua `StandardScaler`.
- **Negative Sampling:** Chạy hàm `tao_canh_am()`. Vì chúng ta chỉ biết các cặp (Thuốc - Bệnh) có liên kết (Nhãn 1), hệ thống sẽ chọn ngẫu nhiên các cặp không liên kết để gán Nhãn 0. Tỉ lệ sinh mặc định là 1:1.

### Bước 2: Khởi tạo Vòng lặp K-Fold (Cross-Validation)
Để đảm bảo kết quả không ăn may, dữ liệu được chia theo `StratifiedKFold` (thường là 10 phần). Mô hình sẽ chạy độc lập 10 lần, mỗi lần dùng 9 phần để học (Train) và 1 phần để kiểm tra (Test).

### Bước 3: Trong 1 Epoch Học (Vòng lặp Forward & Backward)

Mỗi Epoch sẽ lặp lại các bước sau:

**1. Forward Pass (Chạy tiến):** 
Dữ liệu đi qua mạng. Hệ thống tính ra tập điểm số (Logits) cho các cặp Thuốc - Bệnh trong tập Train. 
*(Hệ thống sử dụng kỹ thuật AMP - Automatic Mixed Precision (FP16) để tăng tốc độ tính toán trên Card đồ họa NVIDIA).*

**2. Tính Mất Mát (Loss Computation):**
Thay vì dùng 1 Loss cơ bản, mô hình kết hợp:
- `BCE Loss` với `Label Smoothing (0.05)`: Phạt các sai số dự đoán, bóp méo nhãn (1 thành 0.95) để tránh overconfident.
- `Margin Ranking Loss (0.3)`: Ép mô hình học cách đẩy điểm của cặp đúng (Positive) cao hơn điểm của cặp sai (Negative) ngẫu nhiên ít nhất 0.3 đơn vị. Giúp tối ưu hóa ROC-AUC.

**3. Backward Pass (Lan truyền ngược):**
- Tính đạo hàm (Gradients).
- **Gradient Clipping:** Giới hạn đạo hàm tối đa (`grad_clip = 1.0`) để mạng không bị "sốc" (bùng nổ gradient) trong quá trình cập nhật.

**4. Cập nhật Trọng số (Optimization):**
- Sử dụng thuật toán `AdamW` (tốt hơn Adam truyền thống) kèm với Weight Decay (`5e-5`) để giới hạn các trọng số không phình quá to, giúp chống Overfitting.

### Bước 4: Tìm Ngưỡng & Đánh Giá Validation

Sau khi học xong 1 Epoch, làm sao biết điểm Logit bao nhiêu là "Có liên kết"? (Ngưỡng không phải luôn là 0.5).
1.  **Tìm Threshold:** Hàm `tim_nguong_toi_uu_f1()` sẽ dò 61 ngưỡng (từ 0.2 đến 0.8) ngay trên **Tập Train**. Ngưỡng nào cho ra chỉ số F1 tốt nhất sẽ được lưu lại.
2.  **Đánh giá Test:** Dùng ngưỡng vừa tìm được áp dụng lên **Tập Test** (Tập mô hình chưa từng được thấy) để tính ra các chỉ số thực tế: `AUC`, `AUPR`, `Accuracy`, `F1-Score`, `MCC`.

### Bước 5: Giám Sát Hội Tụ (Scheduler & Early Stopping)
- **Scheduler (ReduceLROnPlateau):** Giám sát điểm `AUC`. Nếu sau 10 Epoch mà AUC không tăng, tốc độ học (Learning Rate) sẽ bị nhân với hệ số $0.65$ (giảm tốc độ để học kỹ hơn).
- **Early Stopping:** Nếu sau 150 Epoch mà AUC vẫn không hề tăng lên (đã chạm ngưỡng cực đại), mô hình sẽ Tự Động Dừng (Early Stop) để không lãng phí thời gian và tránh Overfitting.
- Trọng số tại Epoch có `AUC` cao nhất sẽ được lưu thành file `best_fold_N.pth`.

$\Rightarrow$ Kết thúc quá trình, mô hình sẵn sàng để suy luận (Inference) cho bất kỳ cặp Thuốc-Bệnh mới nào trên giao diện người dùng.
