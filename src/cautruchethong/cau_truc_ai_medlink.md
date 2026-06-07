# Cẩm Nang Chi Tiết Về Kiến Trúc AI (FuzzyGCN) Trong Hệ Thống MedLink

Tài liệu này được biên soạn để giúp bạn nắm bắt **tận gốc rễ** logic, toán học và cách thức cài đặt mã nguồn của hệ thống Trí Tuệ Nhân Tạo (AI) trong dự án. 

Hệ thống AI này giải quyết bài toán: **Dự đoán liên kết Thuốc - Bệnh (Drug-Disease Association Prediction)** dựa trên Mạng Nơ-ron Đồ thị (GNN) kết hợp Logic Mờ (Fuzzy Logic).

---

## PHẦN 1: DỮ LIỆU ĐẦU VÀO & TIỀN XỬ LÝ (DATA PIPELINE)

Để AI có thể hiểu được Thuốc và Bệnh, chúng ta phải "số hóa" chúng thành các vectơ đặc trưng (Feature vectors). Quá trình này nằm trong file `src/backend/app/ai/huan_luyen.py`.

### 1. Nguồn Đặc Trưng Của Thuốc (Drug Features)
Một loại thuốc không chỉ được biểu diễn bằng 1 con số, mà là sự ghép nối (concatenate) của 3 nguồn thông tin:
- **DrugFingerprint (Dấu vân tay hóa học):** Vectơ nhị phân (thường là 881 chiều PubChem) mô tả sự tồn tại của các nhóm chức hóa học trong phân tử thuốc.
- **DrugGIP (Gaussian Interaction Profile):** Đo lường cấu trúc mạng (topological). Thuốc A có "giống" thuốc B không dựa trên việc chúng có đang cùng chữa chung các bệnh nào đó hay không.
- **Drug_mol2vec:** Nhúng (Embedding) cấu trúc phân tử thành một không gian liên tục (tương tự thuật toán Word2Vec trong NLP).

$\Rightarrow$ Kết quả: Ta được một ma trận đặc trưng Thuốc khổng lồ $X_{drug} \in \mathbb{R}^{N_d \times D_d}$ ($N_d$: Số lượng thuốc, $D_d$: Số chiều đặc trưng sau khi ghép).

### 2. Nguồn Đặc Trưng Của Bệnh (Disease Features)
Tương tự, bệnh được biểu diễn qua:
- **DiseaseFeature:** Đặc trưng biểu hiện gen sinh học hoặc triệu chứng lâm sàng.
- **DiseaseGIP:** Cấu trúc mạng (hai bệnh có chung các thuốc điều trị không).
- **DiseasePS:** (Phonotype Similarity) Mức độ tương đồng về mặt kiểu hình triệu chứng giữa các bệnh.

$\Rightarrow$ Kết quả: Ma trận đặc trưng Bệnh $X_{disease} \in \mathbb{R}^{N_p \times D_p}$.

### 3. Chuẩn Hóa Đặc Trưng (StandardScaler)
Vì Fingerprint là số 0/1, trong khi GIP và mol2vec là các số thực liên tục có biên độ lớn nhỏ khác nhau, nếu đưa thẳng vào AI sẽ gây ra hiện tượng **Gradient Explosion** (bùng nổ gradient) hoặc khiến mô hình hội tụ rất chậm. 
- **Giải pháp:** Sử dụng hàm `chuan_hoa_dac_trung()`. Mỗi cột đặc trưng được chuẩn hóa về phân phối chuẩn (Mean = 0, Variance = 1).
- **Công thức:** $x_{new} = \frac{x_{old} - \mu}{\sigma}$

---

## PHẦN 2: XÂY DỰNG ĐỒ THỊ DỊ THỂ (HETEROGENEOUS GRAPH)

Vì Thuốc và Bệnh là hai loại thực thể hoàn toàn khác nhau ($D_d \neq D_p$), ta không thể xếp chúng chung vào một đồ thị đồng nhất bình thường.
Trong hàm `tao_do_thi()`, ta khởi tạo đối tượng `HeteroData` của PyTorch Geometric:

1.  **Nút (Nodes):** Có 2 kiểu là `drug` và `disease`.
2.  **Cạnh (Edges):** Chỉ sử dụng **cạnh dương** (những cặp thuốc - bệnh đã được y tế xác nhận) để làm xương sống cho đồ thị.
    - Chiều xuôi: `("drug", "interacts", "disease")`
    - Chiều ngược: `("disease", "rev_interacts", "drug")`
    *Tại sao phải có 2 chiều?* Để khi chạy GCN, thông tin không chỉ chảy từ Thuốc sang Bệnh, mà còn phản hồi từ Bệnh ngược lại Thuốc, giúp cả hai bên cùng "hiểu" về nhau.

---

## PHẦN 3: KIẾN TRÚC MẠNG NƠ-RON (FUZZY GCN ARCHITECTURE)

Luồng chạy chính của dữ liệu nằm ở hàm `forward()` trong file `mo_hinh_ai.py` và `gnn_algorithm.py`.

### Bước 3.1: Lớp Logic Mờ (Fuzzy Layer) - Chống Nhiễu
Dữ liệu sinh học rất nhiễu. Hàm `LopFuzzy` (trong `fuzzy_layer.py`) nhận dữ liệu thô và chuyển sang "Không gian mờ".
- Nó định nghĩa 2 tập mờ cho mỗi nơ-ron: Tập **Gaussian** (hình chuông) và Tập **Triangular** (hình tam giác).
- Thay vì nơ-ron xuất ra một giá trị tuyến tính $y = wx + b$, nơ-ron xuất ra **mức độ thuộc về (degree of membership)**.
- **Ý nghĩa:** Nếu dữ liệu bị nhiễu một chút (ví dụ nồng độ biểu hiện gen đo sai số), hàm Gaussian vẫn trả về một giá trị tương đồng (chống chấn động dữ liệu cực tốt).

### Bước 3.2: Chiếu Đồng Nhất (Homogenization)
Đặc trưng Thuốc và Bệnh ban đầu có số chiều khác nhau. Qua hàm `_chuyen_sang_dong_nhat()`, chúng bị ép qua các Linear Layer riêng biệt để chiếu về cùng một không gian nhúng (Ví dụ: Cùng có `kich_thuoc_an` = 512 chiều). Lúc này, Thuốc và Bệnh đã nói "chung một ngôn ngữ toán học".

### Bước 3.3: Tính Trọng Số Cạnh Động (Dynamic Edge Weighting)
Hàm `tinh_trong_so_canh()` trong `gnn_algorithm.py`.
- **Toán học:** Giữa nút $i$ và nút $j$ có cạnh nối, mô hình tính Cosine Similarity $S_{ij} = \frac{v_i \cdot v_j}{||v_i|| \cdot ||v_j||}$. Sau đó bọc qua hàm RBF (Radial Basis Function): 
  $W_{ij} = \exp\left(-\frac{(1 - S_{ij})^2}{2}\right)$
- **Ý nghĩa:** Trong thế giới thực, không phải Thuốc nào tác động lên Bệnh cũng có hiệu lực 100% giống nhau. Hàm này giúp mạng tự học được "Mức độ quan trọng" của mối quan hệ. Nút nào giống nhau nhiều thì truyền thông tin cho nhau nhiều.

### Bước 3.4: Tích Chập Đồ Thị Nhiều Lớp (Multi-layer GCN)
Nằm trong hàm `truyen_qua_cac_lop_gcn()`. 
- **Công thức tính 1 lớp GCN cơ bản:** Đặc trưng mới của nút là trung bình trọng số đặc trưng của các nút hàng xóm.
- **Sử dụng 4 lớp GCN:** Hệ thống dùng 4 lớp để thông tin được truyền xa 4 bước (4-hops). Nhờ đó Thuốc A có thể học được thông tin của Thuốc C thông qua Bệnh B (mạng lưới quan hệ gián tiếp).
- **Kết nối thặng dư (Residual Connection):** $h^{(l+1)} = LayerNorm( ELU( GCN(h^{(l)}) ) + h^{(l)} )$.
  - Phép cộng `$ + h^{(l)}$` giúp khắc phục hiện tượng **Oversmoothing** (Làm mịn quá mức). Nếu không cộng lại, sau 4 bước, tất cả các thuốc sẽ có vectơ giống hệt nhau.
  - `ELU`: Hàm kích hoạt giúp giảm hiện tượng chết nơ-ron (dying ReLU).
  - `LayerNorm`: Cân bằng phân phối dữ liệu, giúp mạng hội tụ nhanh.

---

## PHẦN 4: GIẢI MÃ VÀ DỰ ĐOÁN (DECODER & PREDICTION)

Sau khi chạy xong GCN, mỗi Thuốc ($e_d$) và mỗi Bệnh ($e_p$) có một vectơ cực kỳ giàu thông tin (chứa cả bản chất của nó và bản chất mạng lưới xung quanh nó).

Bây giờ ta có 1 cặp (Thuốc A, Bệnh B). Có liên kết hay không?
Nằm trong class `GiaiMaMLPN`.
- **Gộp đặc trưng:** Ghép $e_d$, $e_p$ và tích vô hướng (phần giao nhau) của chúng: $Z = [e_d \ ||\  e_p \ ||\  e_d \odot e_p]$.
- **Mạng nơ-ron nhỏ (MLP):** Đưa Z qua mạng đa tầng: $Linear \rightarrow ELU \rightarrow Dropout \rightarrow Linear \rightarrow L_{score}$.
- **Điểm số cuối (Logit):** Là một giá trị thực âm hoặc dương. Khi đi qua hàm Sigmoid $\sigma(x)$, nó sẽ trở thành xác suất $P \in [0, 1]$.

---

## PHẦN 5: CHIẾN LƯỢC HUẤN LUYỆN & HÀM MẤT MÁT (TRAINING PIPELINE)

Hệ thống thông minh nhất ở phần tính Loss (file `huan_luyen.py`, hàm `tinh_loss_ket_hop`).

### 5.1. Vấn Đề Lấy Mẫu Âm (Negative Sampling)
Trong dữ liệu gốc, ta chỉ biết Thuốc A có chữa Bệnh B (Nhãn = 1). Không ai rảnh đi ghi Thuốc A không chữa Bệnh C (Nhãn = 0). Nếu chỉ dạy AI bằng nhãn 1, nó sẽ đoán mọi thứ là 1.
$\Rightarrow$ Hàm `tao_canh_am()` sẽ sinh ra ngẫu nhiên các cặp Thuốc-Bệnh không có trong tập dương. Coi chúng là nhãn 0.

### 5.2. Hàm Mất Mát Kết Hợp (BCE + Margin Ranking)
AI tính tổng 2 loại "tiền phạt" (loss) nếu dự đoán sai:

**a) BCE Loss với Label Smoothing:**
- Thay vì ép mô hình học chính xác 100% (Nhãn = 1), ta bóp méo nhãn một chút thành Nhãn mờ $\tilde{y} = 0.95$ (Label smoothing $\epsilon = 0.05$). Nhãn 0 thành $0.025$.
- Điều này giúp mô hình không bị tự phụ (Overconfident), ngăn ngừa Overfitting (Học vẹt).

**b) Pairwise Margin Ranking Loss:**
- Yêu cầu AI: *"Không cần biết xác suất là bao nhiêu, nhưng tao muốn điểm của Cặp Dương phải LỚN HƠN điểm của Cặp Âm ngẫu nhiên ít nhất là 0.3 (Margin = 0.3)"*.
- $L_{rank} = \max(0, \ \gamma - Score_{pos} + Score_{neg})$
- Việc dùng Ranking Loss giúp mô hình đẩy vọt trực tiếp các chỉ số đánh giá đồ thị khó tính như **AUC** và **AUPR**.

### 5.3. Tìm Ngưỡng Động (Dynamic Thresholding)
Mô hình xuất ra xác suất từ 0 đến 1. Điểm cắt (Threshold) để kết luận "CÓ LIÊN KẾT" là bao nhiêu? Không phải là 0.5.
Hàm `tim_nguong_toi_uu_f1()` sẽ quét từ 0.2 đến 0.8 trên tập Train, xem ngưỡng nào cho chỉ số F1-Score cao nhất (Cân bằng giữa việc Bắt nhầm và Bỏ sót). Sau đó mới dùng ngưỡng đó áp dụng cho tập Test.

---

## TỔNG KẾT
1. **Dữ liệu thô** $\rightarrow$ **Chuẩn hóa** (Chống tràn số)
2. **Dữ liệu chuẩn hóa** $\rightarrow$ **Fuzzy Layer** (Chống nhiễu loạn sinh học)
3. **Đồ thị Dị thể** $\rightarrow$ **GCN 4 lớp có Residual** (Khai phá tri thức ngầm, liên kết bắc cầu mà không bị bão hòa)
4. **Decoder MLP** $\rightarrow$ **BCE + Margin Ranking Loss** (Tối ưu hóa bảng xếp hạng thay vì chỉ phân loại nhị phân).

Kiến trúc này giải quyết triệt để 3 bài toán lớn nhất của tin sinh học: **Nhiễu dữ liệu**, **Quan hệ phức hợp**, và **Mất cân bằng nhãn**. Đảm bảo MedLink AI có khả năng khám phá ra các chỉ định thuốc mới cực kỳ hiệu quả.
