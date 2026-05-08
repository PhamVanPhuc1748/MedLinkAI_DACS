# ⚡ Quick Start Guide

Hướng dẫn nhanh để bắt đầu sử dụng dự án trong vài phút.

---

## 🎯 1. Cài Đặt Ban Đầu (5 phút)

### Bước 1: Kích hoạt Virtual Environment

**Windows:**
```bash
cd e:\code\model_GNN
venv\Scripts\activate
```

**Linux/macOS:**
```bash
cd /path/to/model_GNN
source venv/bin/activate
```

### Bước 2: Cài Đặt Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

✅ Xong! Giờ bạn đã sẵn sàng.

---

## 🚀 2. Sử Dụng Nhanh

### Option A: Sử Dụng GUI (Recommended for Beginners)

```bash
streamlit run backend/app/ai/test_gui.py
```

- Trình duyệt sẽ mở tự động
- Nhập tên hoặc ID của thuốc
- Nhấn "Predict" để xem Top-K bệnh được dự đoán
- Done! ✨

### Option B: Sử Dụng CLI

```bash
# Dự đoán Top-5 bệnh cho thuốc ID 0
python backend/app/ai/test_model.py

# Dự đoán Top-10 bệnh cho thuốc ID 15
python backend/app/ai/test_model.py --drug-id 15 --top-k 10

# Sử dụng dataset C thay vì B
python backend/app/ai/test_model.py --dataset C-dataset --drug-id 5
```

### Option C: Huấn Luyện Lại Mô Hình

```bash
# Mặc định huấn luyện trên B, C, F với 50 epochs
python backend/app/ai/train_gcn.py

# Huấn luyện chỉ trên B với 100 epochs
python backend/app/ai/train_gcn.py --datasets B-dataset --epochs 100

# Huấn luyện với hyperparameters tùy chỉnh
python backend/app/ai/train_gcn.py \
    --hidden-dim 128 \
    --out-dim 64 \
    --gcn-layers 4 \
    --lr 0.0005 \
    --epochs 200
```

---

## 📊 3. Hiểu Output

### Output từ CLI (test_model.py)

```
Drug ID: 0
Top 5 predicted diseases:

Rank  Disease Name          Score    
----  --------------------  -------  
1     Breast Cancer         0.8765   
2     Lung Carcinoma        0.8234   
3     Melanoma              0.7891   
4     Prostate Cancer       0.7654   
5     Colorectal Cancer     0.7432   
```

**Giải thích:**
- **Rank**: Thứ tự từ cao đến thấp
- **Disease Name**: Tên bệnh được dự đoán
- **Score**: Điểm tương tác (0-1, cao hơn = khả năng cao hơn)

### Output từ GUI

```
┌─────────────────────────────────────────┐
│ Search Results:                         │
│ Selected Drug: Aspirin (ID: 25)         │
├─────────────────────────────────────────┤
│ Top Predicted Diseases:                 │
│                                         │
│ 1. Fever [Score: 0.9234]                │
│ 2. Headache [Score: 0.8876]             │
│ 3. Pain [Score: 0.8234]                 │
│ 4. Inflammation [Score: 0.7654]         │
│ 5. Arthritis [Score: 0.6987]            │
└─────────────────────────────────────────┘
```

---

## 📚 4. Các Trường Hợp Sử Dụng Phổ Biến

### Trường Hợp 1: Kiểm Tra Mối Tương Tác Thuốc-Bệnh

```bash
# Bạn muốn biết bệnh nào có khả năng tương tác với Ibuprofen
python backend/app/ai/test_model.py --drug-id 10 --top-k 5
```

### Trường Hợp 2: So Sánh Các Datasets

```bash
# Huấn luyện trên tất cả 3 datasets
python backend/app/ai/train_gcn.py --epochs 50

# Test model từ B-dataset
python backend/app/ai/test_model.py \
    --dataset B-dataset \
    --weights ./weights/fuzzy_gcn_B_dataset.pth \
    --drug-id 42

# Test model từ C-dataset
python backend/app/ai/test_model.py \
    --dataset C-dataset \
    --weights ./weights/fuzzy_gcn_C_dataset.pth \
    --drug-id 42

# So sánh kết quả giữa hai model
```

### Trường Hợp 3: Fine-tuning Trên Dataset Tùy Chỉnh

```bash
# Huấn luyện lâu lâu với learning rate thấp hơn
python backend/app/ai/train_gcn.py \
    --datasets B-dataset \
    --epochs 500 \
    --lr 0.0001 \
    --seed 999
```

### Trường Hợp 4: Sử Dụng GPU để Tăng Tốc (Nếu có NVIDIA GPU)

```bash
# Huấn luyện nhanh hơn với GPU
python backend/app/ai/train_gcn.py \
    --device cuda \
    --amp \
    --epochs 100

# Nếu lỗi "CUDA out of memory"
python backend/app/ai/train_gcn.py \
    --device cuda \
    --hidden-dim 32 \
    --out-dim 16
```

---

## ❌ 5. Troubleshooting Nhanh

### Lỗi: "ModuleNotFoundError: No module named 'torch'"

```bash
# Giải pháp
pip install torch
```

### Lỗi: "FileNotFoundError: Dataset missing required files"

```bash
# Kiểm tra các file cần thiết có tồn tại:
# B-dataset/DrugFingerprint.csv ✓
# B-dataset/DiseaseFeature.csv ✓
# B-dataset/DrugDiseaseAssociationNumber.csv ✓
```

### Lỗi: "CUDA out of memory"

```bash
# Giải pháp: Dùng CPU thay vì GPU
python backend/app/ai/train_gcn.py --device cpu

# Hoặc giảm kích thước model
python backend/app/ai/train_gcn.py --hidden-dim 32 --out-dim 16
```

### Streamlit GUI không hiển thị

```bash
# Xóa cache
streamlit cache clear

# Chạy lại
streamlit run backend/app/ai/test_gui.py
```

---

## 🎓 6. Khái Niệm Cơ Bản

### FuzzyGCN là gì?

```
Fuzzy GCN = Graph Convolutional Network + Fuzzy Layer

┌─────────────────────────────────────────────────┐
│ Input: Drug Features + Disease Features        │
│        Connected by Drug-Disease Edges          │
├─────────────────────────────────────────────────┤
│ Step 1: Encode features ( Linear Layer )        │
│ Step 2: Denoise features ( Fuzzy Layer )        │
│ Step 3: Graph convolution ( GCN Layers )        │
├─────────────────────────────────────────────────┤
│ Output: Predictions of Drug-Disease             │
│         Interactions                            │
└─────────────────────────────────────────────────┘
```

### Điểm Score là gì?

Score (0-1) là xác suất của một mối tương tác:
- **0.9+**: Rất có khả năng có tương tác
- **0.7-0.9**: Có khả năng có tương tác
- **0.5-0.7**: Cần xem xét thêm
- **<0.5**: Ít có khả năng có tương tác

### Chế độ AMP là gì?

AMP (Automatic Mixed Precision) giúp:
- ✅ Tăng tốc độ huấn luyện (~1.5-2x)
- ✅ Giảm bộ nhớ GPU (~50%)
- ❌ Yêu cầu GPU NVIDIA

---

## 📖 7. Các Lệnh Thường Dùng

| Mục đích | Lệnh |
|---------|------|
| **Chạy GUI** | `streamlit run backend/app/ai/test_gui.py` |
| **Test T5 bệnh hàng đầu** | `python backend/app/ai/test_model.py` |
| **Test Top-20 bệnh** | `python backend/app/ai/test_model.py --top-k 20` |
| **Huấn luyện từ đầu** | `python backend/app/ai/train_gcn.py` |
| **Kiểm tra PyTorch** | `python -c "import torch; print(torch.__version__)"` |
| **Kiểm tra GPU** | `python -c "import torch; print(torch.cuda.is_available())"` |
| **Kích hoạt venv (Win)** | `venv\Scripts\activate` |
| **Kích hoạt venv (Mac/Linux)** | `source venv/bin/activate` |
| **Cài đặt dependencies** | `pip install -r requirements.txt` |

---

## 📚 8. Tài Liệu Liên Quan

- **Chi tiết**: Xem [README.md](README.md)
- **Phát triển**: Xem [DEVELOPMENT_GUIDE.md](DEVELOPMENT_GUIDE.md)
- **Mô hình AI**: Xem [docs/ai_model.md](docs/ai_model.md)
- **Database**: Xem [docs/database.md](docs/database.md)

---

## ⏱️ 9. Thời Gian Dự Kiến

| Tác vụ | Thời gian |
|--------|----------|
| Cài đặt dependencies | 5 phút |
| Chạy GUI lần đầu | 1 phút |
| Dự đoán 1 truy vấn | 0.5 giây |
| Huấn luyện trên B-dataset (50 epochs) | 5-10 phút (CPU) / 2-3 phút (GPU) |
| Huấn luyện trên 3 datasets | 20-60 phút (tùy thuộc CPU/GPU) |

---

## 🎯 10. Bước Tiếp Theo

1. **Nếu mới bắt đầu**: Chạy GUI (`streamlit run ...`)
2. **Nếu muốn explore**: Thử các CLI commands khác nhau
3. **Nếu muốn hiểu sâu**: Đọc [DEVELOPMENT_GUIDE.md](DEVELOPMENT_GUIDE.md)
4. **Nếu muốn mở rộng**: Xem phần "Mở rộng dự án" trong dev guide

---

**Happy coding! 🚀**

*Được cập nhật: Tháng 4, 2026*
