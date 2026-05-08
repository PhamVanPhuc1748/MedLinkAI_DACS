# 🧬 MedLink AI — Hệ Thống Dự Đoán Tương Tác Thuốc–Bệnh (Drug–Disease Association)

> **Tài liệu bàn giao kỹ thuật** · Dành cho thành viên mới tiếp nhận dự án  
> Phiên bản: 1.0 · Cập nhật: 2026

---

## Mục Lục

1. [Tổng Quan Dự Án](#1-tổng-quan-dự-án)
2. [Kiến Trúc & Công Nghệ](#2-kiến-trúc--công-nghệ)
3. [Bản Đồ Thư Mục](#3-bản-đồ-thư-mục)
4. [Mô Hình AI — FuzzyGCN](#4-mô-hình-ai--fuzzygcn)
5. [Cơ Chế Hoạt Động Của Web](#5-cơ-chế-hoạt-động-của-web)
6. [Hướng Dẫn Cài Đặt & Chạy](#6-hướng-dẫn-cài-đặt--chạy)
7. [Cơ Sở Dữ Liệu](#7-cơ-sở-dữ-liệu)
8. [Kết Quả Huấn Luyện](#8-kết-quả-huấn-luyện)
9. [Định Hướng Tương Lai](#9-định-hướng-tương-lai)
10. [Ghi Chú Cho Nhóm](#10-ghi-chú-cho-nhóm)

---

## 1. Tổng Quan Dự Án

### 1.1 Bài Toán: Tại Sao Cần Dự Đoán Tương Tác Thuốc–Bệnh?

Trong nghiên cứu y dược, việc tìm ra một loại thuốc mới có thể mất **10–15 năm và hàng tỷ USD**. Tuy nhiên, một sự thật thú vị là: rất nhiều loại thuốc đang lưu hành **có thể điều trị thêm nhiều bệnh khác** mà chúng ta chưa biết đến — hiện tượng này gọi là **Drug Repurposing (Tái Sử Dụng Thuốc)**.

Hệ thống này giải quyết hai bài toán thực tiễn cụ thể:

| Bài Toán | Ý Nghĩa Thực Tiễn |
|---|---|
| **Khám phá công dụng mới của thuốc** | Một thuốc điều trị ung thư có thể có tiềm năng chống viêm khớp — AI có thể phát hiện điều này |
| **Cảnh báo tác dụng phụ tiềm ẩn** | Nếu thuốc A có liên kết mạnh với bệnh B mà chưa được ghi nhận, đó là tín hiệu cần nghiên cứu thêm |
| **Hỗ trợ bác sĩ & dược sĩ** | Tra cứu nhanh danh sách thuốc liên quan theo bệnh lý và ngược lại |

### 1.2 Luồng Hoạt Động Tổng Thể

```
┌───────────────────┐     ┌──────────────────────┐     ┌─────────────────────┐
│   File CSV thô    │────▶│  Xây dựng Đồ thị     │────▶│   Mô hình FuzzyGCN  │
│  (Thuốc, Bệnh,    │     │  Heterogeneous Graph  │     │  (3 lớp GCN +       │
│   Liên kết)       │     │  Drug ←→ Disease      │     │   Fuzzy Layer)      │
└───────────────────┘     └──────────────────────┘     └──────────┬──────────┘
                                                                   │ Embedding vectors
                                                         ┌─────────▼──────────┐
                                                         │  Điểm Tương Đồng   │
                                                         │  (Cosine Similarity │
                                                         │   → Probability)   │
                                                         └─────────┬──────────┘
                                                                   │
                                          ┌────────────────────────▼──────────────────────┐
                                          │              FastAPI Backend                   │
                                          │   /api/predict/drug  |  /api/predict/disease  │
                                          └────────────────────────┬──────────────────────┘
                                                                   │
                                          ┌────────────────────────▼──────────────────────┐
                                          │           Streamlit Frontend (MedLink AI)      │
                                          │   Tra cứu Thuốc→Bệnh  |  Bệnh→Thuốc          │
                                          │   Badge ✅ Đã biết  |  🔬 AI Dự đoán mới     │
                                          └───────────────────────────────────────────────┘
```

### 1.3 Ba Bộ Dataset

Hệ thống sử dụng **3 bộ dữ liệu chuẩn** trong nghiên cứu DDA:

| Dataset | Thuốc | Bệnh | Liên kết |
|---------|-------|------|---------|
| **B-dataset** | 269 | 598 | 18,416 |
| **C-dataset** | 663 | 409 | 2,532 (tăng thêm) |
| **F-dataset** | 593 | 313 | 1,598 (tăng thêm) |
| **Gộp (Merged)** | **757** | **1,013** | **22,546** |

---

## 2. Kiến Trúc & Công Nghệ

### 2.1 Tech Stack

```
┌─────────────────────────────────────────────────────────┐
│                     FRONTEND LAYER                       │
│   Streamlit 1.20+  ·  Python  ·  HTML/CSS tùy chỉnh     │
├─────────────────────────────────────────────────────────┤
│                      API LAYER                           │
│   FastAPI 0.110+  ·  Uvicorn  ·  JWT-style Tokens       │
├─────────────────────────────────────────────────────────┤
│                    AI / MODEL LAYER                      │
│   PyTorch 2.0+  ·  PyTorch Geometric 2.3+               │
│   FuzzyGCN (3-layer GCN + Gaussian Fuzzy)               │
├─────────────────────────────────────────────────────────┤
│                   DATA LAYER                             │
│   Pandas  ·  NumPy  ·  scikit-learn  ·  SciPy           │
├─────────────────────────────────────────────────────────┤
│                  DATABASE LAYER                          │
│   SQL Server Express  ·  SQLAlchemy 2.0  ·  pyodbc      │
└─────────────────────────────────────────────────────────┘
```

### 2.2 Tại Sao Dùng GCN (Graph Convolutional Network)?

**Câu trả lời ngắn gọn:** Vì mối quan hệ thuốc–bệnh **vốn dĩ là một mạng lưới**, không phải một bảng dữ liệu thông thường.

Hãy tưởng tượng:
- **Thuốc A** điều trị **Bệnh X** và **Bệnh Y**
- **Thuốc B** cũng điều trị **Bệnh Y** và **Bệnh Z**
- → Điều đó ngụ ý Thuốc A và Thuốc B có *điểm tương đồng*, và Thuốc A *có thể* liên quan đến Bệnh Z

Đây chính xác là thứ mà GCN khai thác: **thông tin lan truyền qua các cạnh kết nối** trong đồ thị. Sau mỗi lớp GCN, mỗi node (thuốc/bệnh) tích lũy thông tin từ hàng xóm của nó — giống như tin đồn lan trong mạng xã hội.

Mạng thông thường (MLP) không thể làm điều này vì nó chỉ xử lý từng node độc lập.

### 2.3 Logic Mờ (Fuzzy Logic) Đóng Vai Trò Gì?

Dữ liệu sinh học **vốn dĩ nhiễu và không chắc chắn**. Cùng một loại thuốc trong các nghiên cứu khác nhau có thể cho kết quả khác nhau. `LopFuzzy` trong dự án này là một lớp **lọc nhiễu thông minh**:

```python
# Công thức hàm thành viên Gaussian (Fuzzy Membership Function):
membership = exp( -( (x - μ)² ) / (2σ²) )
output = x * membership
```

- **Ý nghĩa:** Các đặc trưng *xa quá* so với trung bình μ sẽ bị "mờ đi" (nhân với giá trị gần 0)
- **Kết quả:** Mô hình robust hơn với dữ liệu nhiễu, không bị overffit với các outlier
- **μ và σ** đều là **tham số học được** (learnable parameters) — mô hình tự tìm ra ngưỡng lọc tối ưu

---

## 3. Bản Đồ Thư Mục

```
model_GNN/
│
├── 📁 B-dataset/           ← Dataset chính (B, C, F tương tự)
│   ├── DrugInformation.csv         Tên & ID của từng thuốc
│   ├── DrugFingerprint.csv         ⭐ Vector đặc trưng hóa học của thuốc (Morgan Fingerprint)
│   ├── Drug_mol2vec.csv            Vector đặc trưng mol2vec của thuốc
│   ├── DiseaseFeature.csv          ⭐ Vector đặc trưng phenotype của bệnh
│   ├── DiseaseGIP.csv              Ma trận tương đồng Gaussian Interaction Profile
│   ├── DiseasePS.csv               Ma trận tương đồng phenotype bệnh
│   ├── DrugGIP.csv                 Ma trận tương đồng GIP của thuốc
│   ├── DrugDiseaseAssociationNumber.csv  🦴 XƯƠNG SỐNG — danh sách cạnh đồ thị
│   ├── DrugProteinAssociationNumber.csv  Liên kết thuốc–protein
│   ├── ProteinInformation.csv      Thông tin protein
│   ├── Protein_ESM.csv             Vector đặc trưng ESM của protein
│   ├── ProteinDiseaseAssociationNumber.csv  Liên kết protein–bệnh
│   └── adj.csv / Alledge.csv / Allnode.csv  Ma trận kề đồ thị
│
├── 📁 C-dataset/           ← Dataset bổ sung C
├── 📁 F-dataset/           ← Dataset bổ sung F
│
├── 📁 weights/             ← Trọng số mô hình đã huấn luyện
│   ├── best_fold_1.pth ~ best_fold_10.pth   Trọng số tốt nhất mỗi fold
│   └── kfold_metrics.json                   ⭐ Kết quả đánh giá tổng hợp 10-fold
│
├── 📁 backend/             ← FastAPI server
│   ├── main.py                     Điểm khởi động backend (uvicorn)
│   └── app/
│       ├── __init__.py
│       ├── database.py             ⭐ Kết nối SQL Server (SQLAlchemy)
│       ├── models.py               ORM models (User, Drug, Disease, Link...)
│       ├── schemas.py              Pydantic schemas cho API request/response
│       ├── security.py             Hash password, tạo/xác thực token
│       ├── api/
│       │   └── routes.py           ⭐ Toàn bộ API endpoints
│       └── ai/
│           ├── mo_hinh_ai.py       ⭐ Định nghĩa class FuzzyGCN
│           ├── fuzzy_layer.py      ⭐ Lớp Gaussian Fuzzy
│           ├── gcn_flow.py         ⭐ Luồng tính toán GCN
│           ├── gnn_algorithm.py    ⭐ Chuyển đổi HeteroData → Homogeneous
│           ├── inference_service.py ⭐ Dịch vụ dự đoán (lookup CSV + model)
│           ├── huan_luyen.py       Script huấn luyện 10-Fold Cross Validation
│           └── model_factory.py    Factory tạo mô hình theo cấu hình
│
├── 📁 frontend/            ← Streamlit UI
│   ├── streamlit_app.py            Điểm vào giao diện web
│   └── app/
│       ├── config.py               Cấu hình URL backend
│       ├── state.py                Quản lý session state Streamlit
│       ├── pages/
│       │   ├── auth.py             Trang đăng nhập
│       │   ├── user.py             ⭐ Trang tra cứu thuốc/bệnh
│       │   └── admin.py            Trang quản trị
│       ├── services/
│       │   └── api_client.py       HTTP client gọi FastAPI
│       └── ui/
│           ├── theme.py            CSS toàn cục
│           └── components.py       ⭐ Component bảng kết quả, metric cards
│
├── 📁 docs/                ← Tài liệu bổ sung
├── seed_sqlserver.py       Script đẩy dữ liệu CSV vào SQL Server
├── clear_db.py             Script xóa dữ liệu để seed lại
├── requirements.txt        Danh sách thư viện
└── README.md               ← File này
```

### 3.1 File Xương Sống: `DrugDiseaseAssociationNumber.csv`

File này là **trái tim của toàn bộ hệ thống**. Nó định nghĩa các **cạnh (edges)** của đồ thị:

```
drug,disease
0,5
0,12
1,3
...
```

- Mỗi hàng = một liên kết đã được xác nhận lâm sàng hoặc qua thực nghiệm
- Đây là **nhãn dương (positive label)** trong quá trình huấn luyện
- Trong inference: dùng để phân biệt "Liên kết đã biết ✅" vs "AI dự đoán mới 🔬"

---

## 4. Mô Hình AI — FuzzyGCN

### 4.1 Kiến Trúc Chi Tiết

```
Input: Drug Features (DrugFingerprint.csv)    Input: Disease Features (DiseaseFeature.csv)
       [N_drugs × D_drug]                              [N_diseases × D_disease]
              │                                                 │
      ┌───────▼───────┐                          ┌─────────────▼───────────┐
      │  Linear Layer  │  ma_hoa_thuoc            │     Linear Layer        │  ma_hoa_benh
      │ D_drug → 64   │                          │   D_disease → 64        │
      └───────┬───────┘                          └─────────────┬───────────┘
              │                                                 │
              └──────────────────┬──────────────────────────────┘
                                 │ Concat → [N_total × 64]
                        ┌────────▼────────┐
                        │   LopFuzzy      │  Gaussian membership filter
                        │  x * exp(...)   │  Lọc nhiễu, học được μ và σ
                        └────────┬────────┘
                                 │ [N_total × 64]
                        ┌────────▼────────┐
                        │  GCNConv (1/3)  │  Lan truyền thông tin qua đồ thị
                        │  ReLU + Dropout │
                        └────────┬────────┘
                        ┌────────▼────────┐
                        │  GCNConv (2/3)  │
                        │  ReLU + Dropout │
                        └────────┬────────┘
                        ┌────────▼────────┐
                        │  GCNConv (3/3)  │  Lớp cuối: 64 → 32
                        └────────┬────────┘
                                 │ Embedding [N_total × 32]
                        ┌────────▼────────┐
                        │  Dot Product /  │
                        │  Cosine Sim.    │  Tính điểm tương đồng drug-disease
                        └────────┬────────┘
                                 │
                        ┌────────▼────────┐
                        │   Sigmoid       │  → Probability [0, 1]
                        └─────────────────┘
```

### 4.2 Trọng Số Cạnh Cosine

Thay vì coi tất cả các cạnh đều như nhau, hệ thống tính **trọng số cạnh dựa trên độ tương đồng cosine**:

```
edge_weight = exp( -(1 - cosine_similarity(u, v))² / 2 )
```

- Hai node **rất giống nhau** → cosine_sim ≈ 1 → edge_weight ≈ 1 (truyền nhiều thông tin)
- Hai node **khác biệt** → cosine_sim ≈ 0 → edge_weight ≈ 0.6 (truyền ít thông tin)

Điều này giúp GCN **phân biệt mức độ quan trọng** của từng mối liên hệ.

### 4.3 Quy Trình Huấn Luyện (10-Fold Cross Validation)

```python
# Cấu hình mặc định (CauHinh dataclass)
so_epoch        = 1000
toc_do_hoc      = 5e-4      # Learning rate
weight_decay    = 2e-4      # L2 regularization
so_lop_gcn      = 3
kich_thuoc_an   = 192       # Hidden dimension
kich_thuoc_ra   = 96        # Output embedding size
kiem_nhan_dung_som = 50     # Early stopping patience
so_fold         = 10
ti_le_am        = 1.2       # Negative sampling ratio
```

**Negative sampling**: Với mỗi cạnh dương (drug-disease có liên kết), hệ thống tạo ra 1.2 cạnh âm ngẫu nhiên (drug-disease không có liên kết) để cân bằng tập huấn luyện.

**Early stopping**: Nếu validation AUC không cải thiện sau 50 epoch liên tiếp, dừng sớm để tránh overfitting.

---

## 5. Cơ Chế Hoạt Động Của Web

### 5.1 Tổng Quan Giao Diện

Giao diện web **MedLink AI** có 3 role:

| Role | Quyền |
|------|-------|
| **Guest** | Chỉ thấy trang đăng nhập |
| **user** | Tra cứu Thuốc→Bệnh, Bệnh→Thuốc, xem lịch sử |
| **admin** | Toàn bộ + quản lý dữ liệu, xem logs |

Tài khoản mặc định:
- `admin` / `admin123`
- `user` / `user123`

### 5.2 Luồng Tra Cứu: Thuốc → Bệnh

```
Người dùng nhập tên thuốc (vd: "Aspirin")
        │
        ▼
frontend/app/services/api_client.py
  POST /api/predict  { "query": "Aspirin", "direction": "drug_to_disease" }
        │
        ▼
backend/app/api/routes.py  →  predict_diseases_by_drug_name()
        │
        ├─── 1. Tìm drug_id trong DrugInformation.csv (fuzzy match theo tên)
        ├─── 2. Gọi model.du_doan_top_k(drug_id, k=top_k)
        │        └── GCN tính embedding → dot product với mọi disease
        │            → Top K bệnh có probability cao nhất
        ├─── 3. So sánh với DrugDiseaseAssociationNumber.csv
        │        → known=True  nếu đã có trong training data
        │        → known=False nếu là dự đoán mới của AI
        └─── 4. Trả về JSON list PredictionItem
                  { name, probability, known, disease_id/drug_id }
        │
        ▼
frontend/app/ui/components.py  →  show_split_result_table()
  ┌───────────────────────────┬────────────────────────────────┐
  │  ✅ Nhóm Thuốc Điều Trị   │  ⚠️ Nhóm Nguy Cơ / Tác Dụng Phụ│
  │  (known=True)             │  (known=False)                  │
  │  Liên kết đã xác nhận     │  AI dự đoán mới — cần kiểm chứng│
  │  trong dataset huấn luyện │  lâm sàng trước khi sử dụng     │
  └───────────────────────────┴────────────────────────────────┘
  - Mỗi cột hiển thị bảng HTML với Progress Bar điểm xác suất
  - Nếu một nhóm rỗng → hiển thị st.info() thay vì bảng trống
```

### 5.3 Giao Diện Kết Quả 2 Cột Song Song

Kết quả được tự động phân loại và hiển thị thành **2 cột song song** dựa trên trường `known`:

| Cột | Nguồn dữ liệu | Màu sắc | Ý nghĩa |
|-----|--------------|---------|---------|
| **✅ Nhóm Điều Trị** (trái) | `known=True` — có trong `DrugDiseaseAssociationNumber.csv` | Xanh lá | Liên kết đã được xác nhận qua nghiên cứu |
| **⚠️ Nguy Cơ / Tác Dụng Phụ** (phải) | `known=False` — AI suy luận từ cấu trúc đồ thị | Cam | Phát hiện mới, cần kiểm chứng lâm sàng |

**Hàm thực thi:** `show_split_result_table()` trong `frontend/app/ui/components.py`

```python
# Phân loại nội bộ
df_tri_benh = [r for r in results if r.get("known", False)]      # ✅ Đã xác nhận
df_canh_bao = [r for r in results if not r.get("known", False)]  # ⚠️ Dự đoán mới

col1, col2 = st.columns(2)
with col1:
    st.subheader("✅ Nhóm Thuốc Điều Trị")
    _render_group_table(df_tri_benh, entity_label)   # hoặc st.info() nếu rỗng

with col2:
    st.subheader("⚠️ Nhóm Nguy Cơ / Tác Dụng Phụ")
    _render_group_table(df_canh_bao, entity_label)   # hoặc st.info() nếu rỗng
```

> ⚠️ **Lưu ý quan trọng:** Nhóm Nguy Cơ **không phải là khuyến cáo y tế**. Đây là gợi ý cho nghiên cứu, không phải chẩn đoán hay đơn thuốc.

### 5.4 Luồng API

```
POST /api/login           → Đăng nhập, nhận token
POST /api/predict         → Tra cứu thuốc/bệnh (cần token)
GET  /api/history         → Lịch sử tra cứu của user
GET  /api/stats           → Thống kê tổng quan (admin)
GET  /api/drugs           → Danh sách thuốc (admin)
GET  /api/diseases        → Danh sách bệnh (admin)
POST /api/drugs           → Thêm thuốc mới (admin)
POST /api/diseases        → Thêm bệnh mới (admin)
POST /api/links           → Thêm liên kết mới (admin)
```

---

## 6. Hướng Dẫn Cài Đặt & Chạy

### 6.1 Yêu Cầu Hệ Thống

- **Python** 3.11+
- **SQL Server Express** (hoặc SQL Server bất kỳ)
- **ODBC Driver 17 for SQL Server** (tải từ Microsoft)
- **Git**
- RAM tối thiểu: 8GB (để load mô hình GCN)

### 6.2 Cài Đặt

```bash
# 1. Clone repository
git clone <repo-url>
cd model_GNN

# 2. Tạo virtual environment
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate

# 3. Cài đặt thư viện
pip install -r requirements.txt

# 4. Cài đặt PyTorch Geometric (cần cài riêng theo version CUDA)
# CPU only:
pip install torch-scatter torch-sparse torch-cluster torch-geometric

# Hoặc theo hướng dẫn tại: https://pytorch-geometric.readthedocs.io/en/latest/install/installation.html
```

### 6.3 Cấu Hình Database

Mở file `backend/app/database.py` và chỉnh sửa connection string:

```python
_DEFAULT_URL = (
    "mssql+pyodbc://TEN_SERVER\\SQLEXPRESS/He_Thong_Du_Doan_Thuoc"
    "?driver=ODBC+Driver+17+for+SQL+Server"
    "&trusted_connection=yes"
    "&TrustServerCertificate=yes"
)
```

Thay `TEN_SERVER` bằng tên máy tính của bạn (xem trong SQL Server Management Studio).

Hoặc set biến môi trường:

```bash
set MODEL_GNN_DB_URL=mssql+pyodbc://SERVER\INSTANCE/DATABASE?driver=...
```

### 6.4 Khởi Tạo & Seed Dữ Liệu

```bash
# Lần đầu: Tạo bảng và đẩy toàn bộ dữ liệu từ 3 dataset
python seed_sqlserver.py

# Nếu cần xóa và seed lại từ đầu:
python clear_db.py
python seed_sqlserver.py
```

Kết quả mong đợi sau seed:
```
Users    : 2
Drugs    : 757
Diseases : 1.013
Links    : 22.546
```

### 6.5 Chạy Ứng Dụng

Dự án dùng **một file launcher duy nhất** (`main.py`) để khởi động toàn bộ hệ thống:

```bash
cd model_GNN_new
venv\Scripts\activate
```

#### Chế Độ Mặc Định (Backend + Modern UI)
```bash
python main.py
```
- FastAPI backend chạy tại: `http://127.0.0.1:8000`
- Streamlit UI chạy tại:    `http://localhost:8502`
- Giao diện: `app_modern.py` (Dark neon, Glassmorphism)

#### Chỉ Chạy UI Demo (Không Cần Database)
```bash
python main.py --modern-only
# hoặc
python main.py --ui-only
```
Dùng khi chưa có SQL Server hoặc muốn demo nhanh giao diện.

#### Giao Diện Cũ (Classic UI)
```bash
python main.py --classic
```
Chạy `streamlit_app.py` (giao diện cũ) thay vì `app_modern.py`.

#### Chỉ Chạy Backend API
```bash
python main.py --api-only
```

#### Đổi Cổng (Nếu Bị Xung Đột)
```bash
python main.py --api-port 8080 --ui-port 8503
```
Hoặc chỉnh thẳng trong `main.py`:
```python
DEFAULT_API_PORT = 8000   # ← đổi cổng FastAPI
DEFAULT_UI_PORT  = 8502   # ← đổi cổng Streamlit
```

#### Tóm Tắt Tất Cả Lệnh
| Lệnh | Mô tả |
|------|-------|
| `python main.py` | Backend + Modern UI *(mặc định)* |
| `python main.py --modern-only` | Chỉ Modern UI, không backend |
| `python main.py --ui-only` | Chỉ Modern UI, không backend |
| `python main.py --classic` | Backend + giao diện cũ |
| `python main.py --api-only` | Chỉ FastAPI backend |
| `python main.py --api-port P1 --ui-port P2` | Đổi cổng tuỳ ý |

> **Lưu ý:** Sau khi khởi động, backend sẽ tự động đồng bộ dữ liệu từ SQL Server ra file JSON trong `src/data/`. Nếu không có DB, UI vẫn chạy được với dữ liệu JSON đã có sẵn.

### 6.6 Huấn Luyện Lại Mô Hình (Tùy Chọn)

```bash
cd backend/app/ai
python huan_luyen.py --dataset B-dataset --epochs 1000 --folds 10
# Trọng số sẽ lưu vào weights/best_fold_*.pth
# Kết quả đánh giá lưu vào weights/kfold_metrics.json
```

---

## 7. Cơ Sở Dữ Liệu

### 7.1 Sơ Đồ Bảng (ERD)

```
┌─────────┐          ┌───────────────────┐         ┌──────────┐
│  users  │          │  drug_disease_links│         │  drugs   │
├─────────┤    ┌────▶├───────────────────┤◀────┐   ├──────────┤
│ id (PK) │    │     │ id (PK)           │     │   │ id (PK)  │
│ username│    │     │ drug_id (FK)      │─────┘   │ name     │
│ password│    │     │ disease_id (FK)   │         │ external_id│
│ role    │    │     └───────────────────┘         │ smiles   │
└────┬────┘    │                                   └──────────┘
     │         │     ┌───────────────────┐
     │         │     │     diseases      │
     │         │────▶├───────────────────┤
     │               │ id (PK)           │
     │               │ name              │
     │               └───────────────────┘
     │
     │         ┌─────────────────────────┐
     └────────▶│   predictions_history   │
               ├─────────────────────────┤
               │ id (PK)                 │
               │ user_id (FK)            │
               │ query_name              │
               │ direction               │
               │ top_k                   │
               │ dataset                 │
               │ results (JSON text)     │
               │ created_at              │
               └─────────────────────────┘
```

### 7.2 Kết Nối SQL Server

- **Server:** `LAPTOP-GNCAN9C4\SQLEXPRESS`
- **Database:** `He_Thong_Du_Doan_Thuoc`
- **Auth:** Windows Authentication (trusted_connection)
- **Driver:** ODBC Driver 17 for SQL Server

---

## 8. Kết Quả Huấn Luyện

Mô hình được đánh giá bằng **10-Fold Cross Validation** trên B-dataset:

| Chỉ Số | Giá Trị | Ý Nghĩa |
|--------|---------|---------|
| **AUC** | **0.8021** | Diện tích dưới đường ROC — mô hình phân loại tốt |
| **AUPR** | **0.7751** | Diện tích dưới đường Precision-Recall |
| **Accuracy** | 0.7166 | Tỷ lệ phân loại đúng |
| **Precision** | 0.6606 | Trong số dự đoán dương, bao nhiêu đúng |
| **Recall** | 0.7762 | Trong số dương thực tế, bao nhiêu được tìm ra |
| **F1 Score** | 0.7135 | Trung bình điều hòa Precision và Recall |
| **MCC** | 0.4428 | Matthews Correlation Coefficient |

> **AUC = 0.80** được coi là **kết quả tốt** trong bài toán DDA, ngang với nhiều nghiên cứu xuất bản trên các tạp chí khoa học uy tín (Bioinformatics, BMC Bioinformatics).

---

## 9. Định Hướng Tương Lai

### 9.1 Nâng Cấp Mô Hình AI

| Ý Tưởng | Mô Tả | Độ Khó |
|---------|-------|--------|
| **Multi-class Classification** | Thay vì chỉ phân loại có/không liên kết, phân loại loại tương tác (điều trị, tác dụng phụ, chống chỉ định) | ⭐⭐⭐ |
| **Graph Attention Networks (GAT)** | Thay GCNConv bằng GATConv để học trọng số cạnh có chú ý (attention) | ⭐⭐⭐ |
| **Heterogeneous GNN** | Giữ nguyên đồ thị dị thể (Drug node ≠ Disease node), không cần chuyển về homogeneous | ⭐⭐⭐⭐ |
| **Knowledge Graph Embedding** | Tích hợp TransE/RotatE để kết hợp thông tin từ các knowledge graph như DrugBank, OMIM | ⭐⭐⭐⭐ |

### 9.2 Tích Hợp Dữ Liệu Mới

| Nguồn Dữ Liệu | Ý Nghĩa |
|---------------|---------|
| **Protein–Drug–Disease** | Thêm node Protein vào đồ thị (đã có file ProteinDiseaseAssociation, DrugProteinAssociation) |
| **Clinical Trial data** | Tích hợp dữ liệu từ ClinicalTrials.gov để cập nhật nhãn liên tục |
| **Molecular fingerprints 3D** | Dùng RDKit để tạo fingerprint 3D thay thế 2D Morgan hiện tại |

### 9.3 Tích Hợp Vision–Language Model (VLM)

> Đây là hướng nghiên cứu đột phá nhất cho tương lai:

```
Bác sĩ chụp ảnh đơn thuốc / kết quả xét nghiệm
        │
        ▼
VLM (GPT-4V / LLaVA)  →  Trích xuất tên thuốc, bệnh lý
        │
        ▼
FuzzyGCN  →  Dự đoán tương tác, cảnh báo
        │
        ▼
Giao diện cảnh báo thời gian thực cho bác sĩ
```

### 9.4 Nâng Cấp Hệ Thống

- **Containerization:** Docker Compose cho backend + db + frontend
- **CI/CD:** GitHub Actions tự động chạy test khi push code
- **Model serving:** Triton Inference Server để phục vụ nhiều request đồng thời
- **Monitoring:** Prometheus + Grafana theo dõi latency, accuracy drift

---

## 10. Ghi Chú Cho Nhóm

### 10.1 Những Điều Cần Biết Trước Khi Chỉnh Code

1. **`inference_service.py`** là điểm trung tâm — mọi dự đoán đều đi qua đây. Không sửa hàm `get_model()` trừ khi hiểu rõ `@lru_cache`.

2. **Trọng số `weights/best_fold_*.pth`** là kết quả huấn luyện quý giá, **đừng xóa**. Nếu muốn huấn luyện lại, đổi tên backup trước.

3. **`DrugDiseaseAssociationNumber.csv`**: Nếu sửa file này, phải clear cache (`lru_cache`) và restart backend.

4. **`seed_sqlserver.py`** dedup theo *tên* (không phải ID). Nếu hai dataset có thuốc cùng tên, chúng được coi là **một thuốc** — đây là thiết kế có chủ đích.

### 10.2 Checklist Khi Gặp Lỗi

```
Backend không khởi động?
  → Kiểm tra SQL Server có đang chạy không
  → Kiểm tra tên server trong database.py
  → Chạy: python -c "import pyodbc; print(pyodbc.drivers())"

Prediction trả về rỗng?
  → Tên thuốc/bệnh có thể bị sai chính tả
  → Kiểm tra dataset đang dùng (mặc định: B-dataset)
  → File DrugInformation.csv có tồn tại không?

Streamlit không kết nối được backend?
  → Backend có đang chạy ở port 8000 không?
  → Kiểm tra API_URL trong frontend/app/config.py
```

### 10.3 Liên Hệ & Tài Liệu Tham Khảo

- **Tài liệu chi tiết:** Xem thư mục `docs/`
- **Hướng dẫn huấn luyện:** `docs/huan_luyen.md`
- **Thiết kế database:** `docs/database_design.md`
- **PyTorch Geometric docs:** https://pytorch-geometric.readthedocs.io
- **Streamlit docs:** https://docs.streamlit.io

---

<div align="center">

**MedLink AI v1.0** · FuzzyGCN Drug–Disease Association Prediction  
Dự án Tốt Nghiệp · Được xây dựng với PyTorch

</div>

## 🏗️ Cấu Trúc Dự Án

```
model_GNN/
├── backend/                    # Backend API & Model
│   └── app/
│       ├── __init__.py
│       ├── models.py           # Định nghĩa SQLAlchemy ORM
│       ├── ai/                 # AI Module
│       │   ├── __init__.py
│       │   ├── gcn_model.py    # Định nghĩa mô hình FuzzyGCN
│       │   ├── train_gcn.py    # Script huấn luyện
│       │   ├── test_model.py   # Script test CLI
│       │   └── test_gui.py     # GUI Streamlit
│       └── api/                # REST API endpoints (coming soon)
│
├── frontend/                   # Frontend (coming soon)
│
├── B-dataset/                  # Tập dữ liệu B
│   ├── adj.csv
│   ├── Alledge.csv
│   ├── Allnode.csv
│   ├── DiseaseFeature.csv
│   ├── DiseaseGIP.csv
│   ├── DiseasePS.csv
│   ├── Drug_mol2vec.csv
│   ├── DrugDiseaseAssociationNumber.csv
│   ├── DrugFingerprint.csv
│   ├── DrugGIP.csv
│   ├── DrugInformation.csv
│   ├── DrugProteinAssociationNumber.csv
│   ├── Protein_ESM.csv
│   ├── ProteinDiseaseAssociationNumber.csv
│   └── ProteinInformation.csv
│
├── C-dataset/                  # Tập dữ liệu C
│   └── [Cấu trúc giống B-dataset]
│
├── F-dataset/                  # Tập dữ liệu F
│   └── [Cấu trúc giống B-dataset]
│
├── weights/                    # Lưu trữ trọng số model đã huấn luyện
│   ├── fuzzy_gcn_all.pth
│   ├── fuzzy_gcn_all.json
│   ├── fuzzy_gcn_B_dataset.pth
│   ├── fuzzy_gcn_B_dataset.json
│   ├── fuzzy_gcn_C_dataset.pth
│   ├── fuzzy_gcn_C_dataset.json
│   ├── fuzzy_gcn_F_dataset.pth
│   └── fuzzy_gcn_F_dataset.json
│
├── docs/                       # Tài liệu dự án
│   ├── ai_model.md            # Chi tiết mô hình AI
│   └── database.md            # Chi tiết cơ sở dữ liệu
│
├── test_gui.py                 # Entry point cho GUI
├── test_model.py               # Entry point cho CLI test
├── train_gcn.py                # Entry point cho huấn luyện
│
└── venv/                       # Python virtual environment
```

---

## 💻 Yêu Cầu Hệ Thống

- **Hệ điều hành**: Windows, Linux, macOS
- **Python**: 3.8+
- **GPU** (tùy chọn nhưng được khuyến khích): NVIDIA GPU với CUDA support

---

## 📦 Cách Cài Đặt

### 1. Clone hoặc tải về dự án

```bash
cd e:\code\model_GNN
```

### 2. Tạo virtual environment (khuyến khích)

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/macOS
python3 -m venv venv
source venv/bin/activate
```

### 3. Cài đặt các thư viện phụ thuộc

Tất cả các thư viện cần thiết được liệt kê dưới đây. Cài đặt bằng pip:

```bash
pip install --upgrade pip
pip install torch torch-geometric
pip install scikit-learn pandas numpy scipy
pip install streamlit
pip install sqlalchemy

# Hoặc cài đặt từ file requirements (nếu có)
pip install -r requirements.txt
```

### 4. (Tùy chọn) Cài đặt CUDA cho GPU acceleration

Nếu bạn muốn sử dụng GPU:

```bash
# Cài đặt PyTorch với CUDA support (ví dụ cho CUDA 11.8)
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
```

---

## 📚 Thư Viện Chính Cần Thiết

| Thư viện | Phiên bản | Mục đích |
|---------|----------|---------|
| **torch** | >= 2.0 | Deep Learning framework chính |
| **torch_geometric** | >= 2.3 | Graph Neural Networks |
| **pandas** | >= 1.5 | Xử lý dữ liệu CSV |
| **numpy** | >= 1.21 | Tính toán số học |
| **scikit-learn** | >= 1.0 | Các hàm utility ML |
| **sqlite3** | (built-in) | Cơ sở dữ liệu |
| **streamlit** | >= 1.20 | Web GUI interface |
| **sqlalchemy** | >= 2.0 | ORM cho database |

---

## 🚀 Cách Sử Dụng

### A. Huấn Luyện Mô Hình

Để huấn luyện mô hình trên tập dữ liệu B, C, F:

#### Lệnh cơ bản:
```bash
cd e:\code\model_GNN
python backend/app/ai/train_gcn.py
```

#### Với các tùy chọn tùy chỉnh:
```bash
python backend/app/ai/train_gcn.py \
    --project-root . \
    --datasets B-dataset C-dataset F-dataset \
    --epochs 100 \
    --hidden-dim 64 \
    --out-dim 32 \
    --gcn-layers 3 \
    --lr 0.001 \
    --seed 42 \
    --device auto \
    --amp \
    --neg-ratio 1.0 \
    --weights-dir ./weights
```

**Giải thích các tham số:**

| Tham số | Mặc định | Mô tả |
|--------|---------|-------|
| `--project-root` | `.` | Đường dẫn thư mục gốc dự án |
| `--datasets` | `B-dataset C-dataset F-dataset` | Các tập dữ liệu để huấn luyện |
| `--epochs` | `50` | Số epoch huấn luyện cho mỗi tập |
| `--hidden-dim` | `64` | Số chiều hidden layer |
| `--out-dim` | `32` | Số chiều output embedding |
| `--gcn-layers` | `3` | Số lớp GCN |
| `--lr` | `0.001` | Learning rate |
| `--seed` | `42` | Random seed để tái tạo kết quả |
| `--device` | `auto` | Device để chạy: `auto`, `cuda`, hoặc `cpu` |
| `--amp` | `False` | Bật Mixed Precision Training (yêu cầu GPU) |
| `--neg-ratio` | `1.0` | Tỷ lệ negative samples/positive samples |
| `--weights-dir` | `./weights` | Thư mục lưu trọng số |

**Ví dụ huấn luyện chỉ trên B-dataset với 200 epoch:**
```bash
python backend/app/ai/train_gcn.py --datasets B-dataset --epochs 200 --hidden-dim 128
```

**Ví dụ huấn luyện trên GPU với AMP (Mixed Precision):**
```bash
python backend/app/ai/train_gcn.py --device cuda --amp --epochs 150
```

---

### B. Test/Dự Đoán qua CLI

Để test mô hình và dự đoán Top-K bệnh cho một thuốc nhất định:

#### Lệnh cơ bản:
```bash
python backend/app/ai/test_model.py
```

Mặc định sẽ dự đoán Top-5 bệnh cho thuốc ID 0 từ tập B-dataset.

#### Với các tùy chọn tùy chỉnh:
```bash
python backend/app/ai/test_model.py \
    --project-root . \
    --dataset B-dataset \
    --weights ./weights/fuzzy_gcn_B_dataset.pth \
    --drug-id 10 \
    --top-k 10 \
    --hidden-dim 64 \
    --out-dim 32 \
    --gcn-layers 3
```

**Giải thích các tham số:**

| Tham số | Mặc định | Mô tả |
|--------|---------|-------|
| `--project-root` | `.` | Đường dẫn thư mục gốc |
| `--dataset` | `B-dataset` | Tập dữ liệu để lấy kích thước |
| `--weights` | `./weights/fuzzy_gcn_all.pth` | Đường dẫn file trọng số `.pth` |
| `--drug-id` | `0` | ID của thuốc cần dự đoán |
| `--top-k` | `5` | Số lượng bệnh hàng đầu được trả về |
| `--from-weights` | `False` | Suy ra input dimensions từ file weights |
| `--hidden-dim` | `64` | Số chiều hidden layer |
| `--out-dim` | `32` | Số chiều output embedding |
| `--gcn-layers` | `2` | Số lớp GCN |

**Ví dụ dự đoán Top-20 bệnh cho thuốc ID 15:**
```bash
python backend/app/ai/test_model.py --drug-id 15 --top-k 20
```

**Ví dụ sử dụng weights từ C-dataset:**
```bash
python backend/app/ai/test_model.py \
    --weights ./weights/fuzzy_gcn_C_dataset.pth \
    --dataset C-dataset \
    --drug-id 5 \
    --top-k 8
```

---

### C. GUI Streamlit

Để chạy giao diện web interactive:

#### Lệnh cơ bản:
```bash
streamlit run backend/app/ai/test_gui.py
```

Trình duyệt sẽ tự động mở tại `http://localhost:8501`.

#### Các chức năng của GUI:

1. **Tìm kiếm thuốc**: Nhập tên hoặc ID thuốc
2. **Dự đoán tương tác**: Xem Top-K bệnh được dự đoán
3. **Xem thông tin**: Chi tiết về thuốc và bệnh
4. **Lịch sử truy vấn**: Xem các dự đoán trước đó

#### Chạy GUI với cấu hình tùy chỉnh:

```bash
# Chạy trên port khác
streamlit run backend/app/ai/test_gui.py --server.port 9000

# Chạy trên mọi interface (0.0.0.0)
streamlit run backend/app/ai/test_gui.py --server.address 0.0.0.0
```

---

## 🔍 Chi Tiết Về Mô Hình

### Kiến Trúc FuzzyGCN

Mô hình `FuzzyGCN` bao gồm các thành phần chính:

```
Input (Drug & Disease Features)
    ↓
[Encoder Tuyến Tính] → Chiếu về không gian ẩn chung
    ↓
[Fuzzy Layer] → Khử nhiễu với hàm Gaussian
    ↓
[Chuyển thành Homogeneous Graph]
    ↓
[GCN Layers] → 2-3 lớp tích chập đồ thị
    ↓
Output (Node Embeddings)
```

### Fuzzy Layer

Lớp mờ sử dụng hàm membership Gaussian:

$$\text{membership}(x) = \exp\left(-\frac{(x - \mu)^2}{2\sigma^2}\right)$$

Đầu ra: $x \cdot \text{membership}(x)$

**Mục đích**: Giảm ảnh hưởng của các đặc trưng lệch lạc/nhiễu.

### Training Strategy

- **Loss Function**: Binary Cross Entropy with Logits
- **Negative Sampling**: Lấy mẫu negative samples với tỷ lệ `neg_ratio : 1` so với positive samples
- **Optimizer**: Adam (mặc định lr=0.001)
- **Mixed Precision**: Hỗ trợ AMP trên GPU để tăng tốc độ

Để chi tiết hơn, xem [docs/ai_model.md](docs/ai_model.md)

---

## 📊 Về Tập Dữ Liệu

Dự án sử dụng 3 tập dữ liệu: B, C, F.

Mỗi tập chứa:

| File | Mô tả | Hàng | Cột |
|-----|-------|------|-----|
| `DrugFingerprint.csv` | Vector fingerprint của thuốc | #drugs | feature dimensions |
| `DiseaseFeature.csv` | Vector đặc trưng của bệnh | #diseases | feature dimensions |
| `DrugDiseaseAssociationNumber.csv` | Các cặp thuốc-bệnh có tương tác | #associations | 2 (drug_id, disease_id) |
| `DrugInformation.csv` | Thông tin metadata của thuốc | #drugs | metadata |
| `DiseaseGIP.csv` | Gaussian Interaction Profile | #diseases | #diseases |
| `Drug_mol2vec.csv` | Molecular embeddings | #drugs | embedding dim |
| `Protein_ESM.csv` | Protein embeddings | #proteins | embedding dim |
| Các file khác | Adjacency matrices, edges, nodes, v.v. | - | - |

**Yêu cầu**: Các file CSV phải có hàng đầu (header) và index column.

---

## 🧪 Testing & Validation

### Test Script

Chạy file test để kiểm tra xem mô hình hoạt động đúng:

```bash
python backend/app/ai/test_model.py --drug-id 0 --top-k 5
```

Expected output:
```
drugging disease_name score
-------- ------------ ------
0        Disease XYZ  0.8765
1        Disease ABC  0.8234
2        Disease DEF  0.7891
...
```

### Kiểm Tra Các Thành Phần

```bash
# Kiểm tra Python version
python --version

# Kiểm tra PyTorch installation
python -c "import torch; print(f'PyTorch: {torch.__version__}'); print(f'CUDA available: {torch.cuda.is_available()}')"

# Kiểm tra Torch Geometric
python -c "import torch_geometric; print(f'Torch Geometric: {torch_geometric.__version__}')"

# Kiểm tra Streamlit
streamlit --version
```

---

## ⚙️ Cấu Hình Nâng Cao

### Cấu Hình Device

**Chọn device tự động (nên dùng):**
```bash
python train_gcn.py --device auto
```

Nếu GPU khả dụng, sẽ sử dụng CUDA; ngược lại dùng CPU.

**Cố định sử dụng GPU:**
```bash
python train_gcn.py --device cuda
```

**Cố định sử dụng CPU:**
```bash
python train_gcn.py --device cpu
```

### Mixed Precision Training

Để tăng tốc độ huấn luyện trên GPU (yêu cầu NVIDIA GPU):

```bash
python train_gcn.py --amp
```

Tiết kiệm tối đa 50% bộ nhớ GPU và tăng tốc độ huấn luyện 1.5-2x.

### Hyperparameter Tuning

Để huấn luyện với hyperparameters tối ưu khác:

```bash
python train_gcn.py \
    --hidden-dim 128 \
    --out-dim 64 \
    --gcn-layers 4 \
    --lr 0.0005 \
    --epochs 200 \
    --neg-ratio 2.0
```

### Lưu Trọng Số Tùy Chỉnh

```bash
python train_gcn.py --weights-dir ./my_weights
```

Trọng số sẽ được lưu tại `./my_weights/fuzzy_gcn_*.pth`.

---

## 🐛 Troubleshooting

### 1. Lỗi: "No module named 'torch'"

**Giải pháp:**
```bash
pip install torch
```

### 2. Lỗi: "CUDA out of memory"

**Giải pháp:**
- Giảm `--hidden-dim` hoặc `--out-dim`
- Giảm `--neg-ratio`
- Sử dụng `--device cpu` để sử dụng RAM thay vì VRAM

```bash
python train_gcn.py --hidden-dim 32 --out-dim 16 --neg-ratio 0.5 --device cpu
```

### 3. Lỗi: "FileNotFoundError: Dataset missing required files"

**Giải pháp:**
- Kiểm tra các file CSV trong thư mục dataset
- Đảm bảo các file cần thiết đều có:
  - `DrugFingerprint.csv`
  - `DiseaseFeature.csv`
  - `DrugDiseaseAssociationNumber.csv`

### 4. Lỗi: "Module not found" khi chạy test_model.py

**Giải pháp:**
```bash
# Chạy từ thư mục gốc dự án
cd e:\code\model_GNN
python backend/app/ai/test_model.py
```

### 5. GUI Streamlit không hiển thị

**Giải pháp:**
```bash
# Xóa cache
streamlit cache clear

# Chạy lại
streamlit run backend/app/ai/test_gui.py
```

---

## 📝 Ghi Chú Quan Trọng

1. **Seed cho tái tạo kết quả**: Luôn sử dụng `--seed` giống nhau để có kết quả nhất quán
   ```bash
   python train_gcn.py --seed 42
   ```

2. **Tệp metadata cho weights**: Mỗi file `.pth` sẽ có file `.json` tương ứng chứa metadata
   - `fuzzy_gcn_B_dataset.pth` → `fuzzy_gcn_B_dataset.json`

3. **Virtual Environment**: Luôn kích hoạt venv trước khi chạy:
   ```bash
   venv\Scripts\activate  # Windows
   source venv/bin/activate  # Linux/macOS
   ```

4. **DataLoader Efficiency**: Dự án hiện không sử dụng PyTorch DataLoader vì toàn bộ dữ liệu đủ nhỏ để fit vào RAM/VRAM

5. **Model Architecture Compatibility**: Đảm bảo `--hidden-dim`, `--out-dim`, `--gcn-layers` trùng khớp giữa huấn luyện và test
   ```bash
   # Huấn luyện
   python train_gcn.py --hidden-dim 128 --out-dim 64 --gcn-layers 4
   
   # Test với cùng config
   python test_model.py --hidden-dim 128 --out-dim 64 --gcn-layers 4
   ```

---

## 📖 Tài Liệu Thêm

- **Chi tiết mô hình AI**: [docs/ai_model.md](docs/ai_model.md)
- **Chi tiết Database**: [docs/database.md](docs/database.md)

---

## 📧 Support

Nếu gặp vấn đề, vui lòng kiểm tra:
1. Phiên bản Python: `python --version` (nên ≥ 3.8)
2. Phiên bản PyTorch: `python -c "import torch; print(torch.__version__)"`
3. CUDA availability: `python -c "import torch; print(torch.cuda.is_available())"`
4. Tất cả file trong cấu trúc dự án đều tồn tại

---

## 📄 License

Dự án này được sử dụng cho mục đích nghiên cứu.

---

**Cập nhật lần cuối**: Tháng 4, 2026
