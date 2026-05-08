# Thuật toán cốt lõi và Chức năng Web — MedLink AI

---

## I. THUẬT TOÁN CỐT LÕI CỦA MÔ HÌNH

### 1. Tổng quan kiến trúc — FuzzyGCN

Mô hình `FuzzyGCN` kết hợp **Graph Convolutional Network (GCN)** với **Lớp Fuzzy Gaussian**, được thiết kế để dự đoán mối liên hệ giữa thuốc và bệnh trên đồ thị dị đồng nhất (Heterogeneous Graph).

```
[DrugFingerprint]  →  Linear(drug_dim → 192)  ─┐
                                                 ├─ LopFuzzy (Gaussian) → HeteroData → HomoGraph
[DiseaseFeature]   →  Linear(disease_dim → 192) ─┘
                                                             ↓
                                               GCNConv × 3 lớp (192 → 192 → 96)
                                                             ↓
                                               Embedding (drug + disease chung 96-d)
                                                             ↓
                                               Dot product → Score [0, 1]
```

---

### 2. Lớp Fuzzy Gaussian (`fuzzy_layer.py` — `LopFuzzy`)

**Mục đích:** Lọc nhiễu trên đặc trưng đầu vào trước khi đưa vào GCN.

**Công thức hàm thành viên Gaussian:**

$$\text{membership}(x) = e^{-\frac{(x - \mu)^2}{2\sigma^2}}$$

**Đầu ra:** $x' = x \times \text{membership}(x)$

**Đặc điểm:**
- Tham số $\mu$ (trung bình) và $\sigma$ (độ lệch chuẩn) đều **có thể học được** (`nn.Parameter`)
- $\sigma$ được clamp tại $10^{-6}$ để tránh chia 0
- Hoạt động như một bộ lọc thích nghi: đặc trưng nào càng gần $\mu$ thì càng được giữ nguyên; càng xa thì càng bị triệt tiêu

---

### 3. Chuyển đổi đồ thị dị đồng nhất → đồng nhất (`gnn_algorithm.py`)

Dữ liệu đầu vào gồm hai loại nút (`drug`, `disease`) và một loại cạnh (`interacts`). Trước khi đưa qua GCN:

1. Mã hóa đặc trưng thuốc: `Linear(drug_dim → 192)`
2. Mã hóa đặc trưng bệnh: `Linear(disease_dim → 192)`
3. Áp dụng `LopFuzzy` lên cả hai
4. Gọi `.to_homogeneous(node_attrs=["x"])` để gộp thành đồ thị đồng nhất

---

### 4. Trọng số cạnh theo Cosine Similarity (`gcn_flow.py`)

Mỗi cạnh trong đồ thị được gán trọng số dựa trên độ tương đồng cosine của hai nút đầu cuối:

$$w_{ij} = e^{-\frac{(1 - \cos(x_i, x_j))^2}{2}}$$

Trọng số này được truyền trực tiếp vào `GCNConv` qua tham số `edge_weight`, tạo ra sự lan truyền thông tin có chọn lọc theo mức độ liên quan giữa các nút.

---

### 5. Các lớp GCN (`gcn_flow.py` — `tao_cac_lop_gcn`)

**Cấu hình mặc định: 3 lớp GCN**

| Lớp | Input dim | Output dim | Kích hoạt |
|-----|-----------|------------|-----------|
| GCNConv 1 | 192 | 192 | ReLU + Dropout(0.2) |
| GCNConv 2 | 192 | 192 | ReLU + Dropout(0.2) |
| GCNConv 3 | 192 | 96 | — (lớp cuối) |

Embedding cuối có kích thước **96 chiều** cho cả thuốc và bệnh.

---

### 6. Tính điểm liên kết & Hàm mất mát

**Điểm liên kết** giữa thuốc $i$ và bệnh $j$:

$$\text{score}(i, j) = \sigma\left(\text{emb}_i \cdot \text{emb}_j\right)$$

Trong đó $\sigma$ là hàm sigmoid, $\text{emb}$ là embedding sau GCN.

**Hàm mất mát:** Binary Cross-Entropy with Logits:

$$\mathcal{L} = -\frac{1}{N}\sum_{k=1}^{N}\left[y_k \log(\hat{y}_k) + (1-y_k)\log(1-\hat{y}_k)\right]$$

---

### 7. Quy trình huấn luyện (`huan_luyen.py`)

| Tham số | Giá trị |
|---------|---------|
| Số epoch | 600 |
| Learning rate | 3×10⁻⁴ |
| Weight decay | 2×10⁻⁴ |
| K-Fold (Stratified) | 10 |
| Negative sampling ratio | 1.2× |
| Early stopping patience | 35 epoch |
| Min delta cải thiện | 5×10⁻⁴ |
| LR Scheduler factor | 0.7 (khi AUC không cải thiện 4 epoch) |
| Batch mode | Full-graph (không mini-batch) |
| AMP (Mixed Precision) | Tuỳ chọn (nếu có GPU) |

**Chuẩn hóa đặc trưng:** `StandardScaler` trên DrugFingerprint và DiseaseFeature trước khi đưa vào đồ thị.

---

### 8. Kết quả huấn luyện (trung bình 10-Fold)

| Chỉ số | Giá trị |
|--------|---------|
| **AUC** | **0.8021** |
| **AUPR** | 0.7751 |
| Accuracy | 71.66% |
| Precision | 66.06% |
| Recall | 77.62% |
| F1-Score | 71.35% |
| MCC | 0.4428 |

---

### 9. Phân loại kết quả dự đoán

Sau khi mô hình trả về điểm số, hệ thống phân loại kết quả theo trường `known`:

| Giá trị `known` | Ý nghĩa | Hiển thị |
|-----------------|---------|----------|
| `True` | Có trong `DrugDiseaseAssociationNumber.csv` | ✅ Điều trị (đã xác nhận) |
| `False` | Mô hình tự phát hiện mới | ⚠️ Dự đoán / Tác dụng phụ tiềm năng |

---

## II. CHỨC NĂNG CỦA WEB

### 1. Xác thực người dùng

| Chức năng | Mô tả |
|-----------|-------|
| Đăng nhập | Nhập username/password → nhận JWT token → session được lưu |
| Đăng xuất | Xóa token khỏi session, chuyển về trang login |
| Kiểm tra API | Ping `/api/health` từ sidebar để xác nhận backend đang chạy |

**Tài khoản mặc định:** `admin / admin123` · `user / user123`

---

### 2. Không gian người dùng (Tab 💊 Thuốc → Bệnh)

- Nhập tên thuốc (fuzzy search theo tên)
- Chọn Dataset (B / C / F), Top-K (1–50), Ngưỡng điểm (0.0–1.0)
- AI trả về danh sách bệnh tiềm năng, **hiển thị 2 cột song song:**
  - Cột trái — ✅ Thuốc điều trị (đã được xác nhận trong dữ liệu)
  - Cột phải — ⚠️ Tác dụng phụ / Cảnh báo rủi ro (phát hiện mới)
- Kết quả tự động **lưu vào SQL Server** (`predictions_history`)

---

### 3. Không gian người dùng (Tab 🦠 Bệnh → Thuốc)

- Nhập tên bệnh (fuzzy search theo tên)
- Tuỳ chỉnh Dataset, Top-K, Ngưỡng điểm
- AI trả về danh sách thuốc tiềm năng, **hiển thị 2 cột song song** theo `known`
- Tự động lưu lịch sử

---

### 4. Lịch sử tra cứu (Tab 📋)

- Hiển thị toàn bộ lịch sử dự đoán của người dùng hiện tại
- Cột thông tin: Hướng, Tên đầu vào, Tên kết quả, **Phân loại** (✅ Điều trị / ⚠️ Dự đoán), Điểm (%), Thời gian
- Cache được xóa sau mỗi lần predict để luôn hiển thị dữ liệu mới nhất

---

### 5. Admin Console — Tổng quan hệ thống (👑 Chỉ admin)

- 5 metric cards: Số Users, Thuốc, Bệnh, Liên kết, Predictions
- Bảng phân bổ lịch sử dự đoán theo hướng (Thuốc→Bệnh / Bệnh→Thuốc)

---

### 6. Admin Console — Quản lý Thuốc

- Form thêm / cập nhật thuốc: Drug ID, Tên, External ID (DrugBank), SMILES
- Xem danh sách 500 thuốc trong database

---

### 7. Admin Console — Quản lý Bệnh

- Form thêm / cập nhật bệnh: Disease ID, Tên bệnh
- Xem danh sách 500 bệnh trong database

---

### 8. Admin Console — Quản lý Liên kết

- Form thêm liên kết Thuốc–Bệnh: Drug ID + Disease ID
- Xem danh sách 1000 liên kết trong database

---

### 9. Admin Console — Prediction Logs

- Xem 400 bản ghi dự đoán gần nhất của **toàn bộ người dùng** hệ thống
- Thông tin hiển thị: Username, Hướng, Tên đầu vào, Kết quả, Điểm, Thời gian

---

## III. STACK CÔNG NGHỆ

| Thành phần | Công nghệ |
|-----------|-----------|
| Mô hình AI | PyTorch 2.x + PyTorch Geometric |
| Backend API | FastAPI + Uvicorn (port 8000) |
| Frontend UI | Streamlit (port 8501) |
| Cơ sở dữ liệu | SQL Server Express (SQLAlchemy 2.0 + pyodbc) |
| Xác thực | JWT token (in-memory, `TOKENS` dict) |
| Dữ liệu | 3 datasets (B/C/F): 757 thuốc, 1013 bệnh, 22.546 liên kết |
