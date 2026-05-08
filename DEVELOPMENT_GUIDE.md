# 🛠️ Hướng Dẫn Phát Triển (Development Guide)

Tài liệu này dành cho các developer muốn hiểu rõ cấu trúc code, phát triển thêm tính năng, hoặc debug các vấn đề.

---

## 📂 Cấu Trúc Code Chi Tiết

### 1. `backend/app/ai/gcn_model.py`

**Trách nhiệm**: Định nghĩa kiến trúc mô hình neural network.

#### Các Class chính:

##### `FuzzyLayer`
```python
class FuzzyLayer(nn.Module):
    def __init__(self, init_sigma: float = 1.0)
    def forward(self, x: torch.Tensor) -> torch.Tensor
```

- **Mục đích**: Khử nhiễu feature bằng hàm membership Gaussian
- **Input**: Tensor hình dạng `[N, D]` (N nodes, D dimensions)
- **Output**: Tensor cùng hình dạng nhưng các đặc trưng lệch được down-weight
- **Tham số học**:
  - `mu`: Trung bình của Gaussian (khởi tạo = 0.0)
  - `sigma`: Độ lệch chuẩn (khởi tạo = 1.0)

##### `FuzzyGCN`
```python
class FuzzyGCN(nn.Module):
    def __init__(
        self,
        drug_in_channels: int,        # Số features ban đầu của drug
        disease_in_channels: int,     # Số features ban đầu của disease
        hidden_channels: int = 64,    # Dimension của hidden state
        out_channels: int = 32,       # Dimension của output embedding
        num_layers: int = 2,          # Số GCN layers
        weights_path: str = "weights/fuzzy_gcn.pth"
    )
    def forward(self, data: HeteroData) -> torch.Tensor
    def _build_homogeneous_data(self, data: HeteroData) -> HeteroData
```

**Kiến trúc tầng:**

```
Input:
  Drug Features: [num_drugs, drug_in_channels]
  Disease Features: [num_diseases, disease_in_channels]

↓

Linear Encoder:
  Drug: [num_drugs, drug_in_channels] → [num_drugs, hidden_channels]
  Disease: [num_diseases, disease_in_channels] → [num_diseases, hidden_channels]

↓

Fuzzy Layer:
  Áp dụng Gaussian membership cho cả drug và disease

↓

Convert to Homogeneous:
  Gộp drug + disease nodes, cạnh drug→disease + disease→drug

↓

GCN Layers (2 hoặc 3 lớp):
  Input: [num_drugs + num_diseases, hidden_channels]
  Output: [num_drugs + num_diseases, hidden_channels]
  
  Lớp cuối:
  Input: [num_drugs + num_diseases, hidden_channels]
  Output: [num_drugs + num_diseases, out_channels]

↓

Output:
  [num_drugs + num_diseases, out_channels]
  (Chia ra: disease_embeddings = output[:num_diseases], drug_embeddings = output[num_diseases:])
```

**Edge Weight Calculation** (trong forward):
```python
cos_sim = F.cosine_similarity(x[src], x[dst])  # cosine similarity
edge_weight = torch.exp(-((1.0 - cos_sim) ** 2) / 2.0)  # fuzzy confidence
```

---

### 2. `backend/app/ai/train_gcn.py`

**Trách nhiệm**: Script huấn luyện mô hình trên các datasets.

#### Các hàm chính:

##### `load_dataset_bundle(dataset_dir: Path) -> DatasetBundle`
- Load tất cả dữ liệu từ một dataset folder
- Auto-align feature matrices nếu cần
- Filter out invalid edges
- Trả về `DatasetBundle` chứa HeteroData, edges, số node

##### `sample_negative_edges(...) -> torch.Tensor`
- Lấy mẫu các cặp (drug, disease) không có tương tác
- Sử dụng rejection sampling để đảm bảo chất lượng
- Trả về negative edges tensor

##### `decode_scores(embeddings, pairs, disease_offset) -> torch.Tensor`
- Tính điểm tương tác = dot product của embeddings
- `score = drug_emb · disease_emb`

##### `train_one_dataset(...) -> List[float]`
- Huấn luyện model trên 1 dataset
- Trả về loss history

##### Hàm `main()`
- Xử lý arguments
- Load tất cả datasets
- Huấn luyện tuần tự trên B → C → F
- Lưu weights

#### Training Loop Logic:

```python
for epoch in range(1, epochs + 1):
    model.train()
    optimizer.zero_grad()
    
    # Forward pass
    embeddings = model(data)  # Lấy node embeddings
    
    # Tính scores
    pos_scores = decode_scores(embeddings, pos_edges, ...)
    neg_scores = decode_scores(embeddings, neg_edges, ...)
    
    # Tạo binary classification problem
    logits = cat([pos_scores, neg_scores])
    labels = cat([ones(...), zeros(...)])
    
    # Loss: BCEWithLogits (tương đương sigmoid + BCE)
    loss = F.binary_cross_entropy_with_logits(logits, labels)
    
    # Backward pass
    loss.backward()
    optimizer.step()
```

---

### 3. `backend/app/ai/test_model.py`

**Trách nhiệm**: CLI inference script để dự đoán Top-K.

#### Luồng:

1. Parse arguments
2. Load weights từ file `.pth`
3. Infer input dimensions từ dataset (hoặc từ weights)
4. Load dataset
5. Khởi tạo model
6. Forward pass → node embeddings
7. Tính điểm cho drug_id với tất cả diseases
8. Lấy Top-K
9. In kết quả

#### Hàm chính:

```python
def infer_feature_dims(dataset_dir: Path) -> tuple[int, int]
    # Đọc số cột từ DrugFingerprint.csv và DiseaseFeature.csv

def infer_feature_dims_from_weights(weights_path: Path) -> tuple[int, int]
    # Đọc dimension từ weight tensor

def infer_meta(weights_path: Path) -> dict
    # Đọc metadata từ file .json kèm theo

def main() -> None
    # Main inference logic
```

---

### 4. `backend/app/ai/test_gui.py`

**Trách nhiệm**: Web GUI sử dụng Streamlit.

#### Các hàm Streamlit cache:

```python
@st.cache_data(show_spinner=False)
def load_drug_table(dataset_dir: Path) -> pd.DataFrame
    # Load drug info với caching

@st.cache_data(show_spinner=False)
def load_disease_table(dataset_dir: Path) -> pd.DataFrame
    # Load disease names từ index của feature file

@st.cache_data(show_spinner=False)
def load_associations(dataset_dir: Path) -> pd.DataFrame
    # Load known drug-disease associations
```

#### Các hàm utility:

```python
def find_matches(df: pd.DataFrame, query: str) -> pd.DataFrame
    # Tìm drug/disease khớp với query (exact hoặc contains)

def get_drugs_for_disease(
    disease_ids: list[int],
    assoc: pd.DataFrame,
    drugs: pd.DataFrame,
    top_k: int
) -> pd.DataFrame
    # Tìm Top-K drugs có tương tác với diseases
```

#### UI Layout:

```
┌─────────────────────────────────────────┐
│ 🔬 Drug-Disease Interaction Predictor   │
├─────────────────────────────────────────┤
│                                         │
│ 🔍 Search Drug: [input box]             │
│ → Dropdown: Select drug                 │
│                                         │
│ [Predict] button                        │
│                                         │
│ ─────────────────────────────────────   │
│ Results:                                │
│ Top-K Diseases for selected drug        │
│                                         │
│ Rank | Disease Name | Score | Status   │
│ ────────────────────────────────────    │
│      |              |       |           │
│                                         │
└─────────────────────────────────────────┘
```

---

### 5. `backend/app/models.py`

**Trách nhiệm**: SQLAlchemy ORM models cho database.

#### ORM Classes:

```python
class User(Base):
    id: int (PK)
    username: str (unique)
    password_hash: str
    role: str
    predictions: List[PredictionHistory] (relationship)

class Drug(Base):
    id: int (PK)
    name: str (unique)
    features: str (JSON serialized)

class Disease(Base):
    id: int (PK)
    name: str (unique)
    features: str (JSON serialized)

class PredictionHistory(Base):
    id: int (PK)
    user_id: int (FK → User.id)
    drug_name: str
    disease_name: str
    score: float
    timestamp: datetime
```

---

## 🔄 Data Flow

### Training Flow

```
┌─────────────────┐
│ Raw CSV Files   │
├─────────────────┤
│ - DrugXXX.csv   │
│ - DiseaseXXX.csv│
│ - Edges CSV     │
│ (B, C, F)       │
└────────┬────────┘
         │
         ↓
┌──────────────────────────────┐
│ load_dataset_bundle()        │
│ - Load features              │
│ - Load edges                 │
│ - Align matrices             │
│ - Build HeteroData           │
└────────┬─────────────────────┘
         │
         ↓
┌──────────────────────────────┐
│ train_one_dataset()          │
│ - Sample negative edges      │
│ - Forward pass (FuzzyGCN)    │
│ - Compute loss (BCE)         │
│ - Backward pass              │
│ - Update weights             │
└────────┬─────────────────────┘
         │
         ↓
┌──────────────────────────────┐
│ Trained Weights              │
│ - fuzzy_gcn_*.pth            │
│ - fuzzy_gcn_*.json (meta)    │
└──────────────────────────────┘
```

### Inference Flow

```
┌──────────────────────┐
│ test_model.py        │
│ drug_id=10, top_k=5  │
└──────────┬───────────┘
           │
           ↓
┌──────────────────────────┐
│ Load weights from .pth   │
└──────────┬───────────────┘
           │
           ↓
┌──────────────────────────┐
│ Load dataset             │
│ (for feature alignment)  │
└──────────┬───────────────┘
           │
           ↓
┌──────────────────────────┐
│ Create HeteroData        │
└──────────┬───────────────┘
           │
           ↓
┌──────────────────────────┐
│ model(data)              │
│ → Embeddings [N, D]      │
└──────────┬───────────────┘
           │
           ↓
┌──────────────────────────┐
│ embeddings[drug_id] ·    │
│ embeddings[diseases]     │
│ → scores [num_diseases]  │
└──────────┬───────────────┘
           │
           ↓
┌──────────────────────────┐
│ Top-K scores             │
│ + disease names/info     │
└──────────┬───────────────┘
           │
           ↓
┌──────────────────────────┐
│ Print/Display results    │
└──────────────────────────┘
```

---

## 🧪 Testing Guidelines

### 1. Unit Testing

Để test individual components:

```python
# test_fuzzy_layer.py
import torch
from backend.app.ai.gcn_model import FuzzyLayer

def test_fuzzy_layer():
    layer = FuzzyLayer(init_sigma=1.0)
    x = torch.randn(10, 64)  # 10 nodes, 64 dims
    output = layer(x)
    
    assert output.shape == x.shape
    assert torch.all(output <= x)  # Fuzzy reduces values
    print("✓ FuzzyLayer test passed")

# test_gcn_forward.py
from backend.app.ai.gcn_model import FuzzyGCN
from torch_geometric.data import HeteroData

def test_gcn_forward():
    model = FuzzyGCN(
        drug_in_channels=128,
        disease_in_channels=100,
        hidden_channels=64,
        out_channels=32,
        num_layers=2
    )
    
    # Create dummy HeteroData
    data = HeteroData()
    data["drug"].x = torch.randn(50, 128)
    data["disease"].x = torch.randn(100, 100)
    data["drug", "interacts", "disease"].edge_index = torch.tensor(
        [[0, 1, 2], [5, 10, 15]], dtype=torch.long
    )
    data["disease", "rev_interacts", "drug"].edge_index = torch.tensor(
        [[5, 10, 15], [0, 1, 2]], dtype=torch.long
    )
    
    output = model(data)
    
    assert output.shape == (150, 32)  # 50 drugs + 100 diseases, 32 dims
    print("✓ FuzzyGCN forward test passed")
```

### 2. Integration Testing

Test toàn bộ pipeline:

```bash
# Huấn luyện trên dataset nhỏ
python backend/app/ai/train_gcn.py \
    --datasets B-dataset \
    --epochs 5 \
    --hidden-dim 32 \
    --out-dim 16

# Test inference
python backend/app/ai/test_model.py \
    --dataset B-dataset \
    --weights ./weights/fuzzy_gcn_B_dataset.pth \
    --drug-id 0 \
    --top-k 3
```

### 3. Performance Benchmarking

```python
import time
import torch

# Benchmark forward pass
model = FuzzyGCN(...)
model.eval()

data = load_dataset_bundle(...)

# Warmup
for _ in range(3):
    with torch.no_grad():
        _ = model(data.hetero_data)

# Timing
start = time.time()
for _ in range(100):
    with torch.no_grad():
        _ = model(data.hetero_data)
elapsed = time.time() - start

print(f"Average forward pass: {elapsed/100*1000:.2f}ms")
```

---

## 🔧 Debugging Tips

### 1. Shape Mismatches

Thêm print statements trong forward pass để kiểm tra shapes:

```python
def forward(self, data):
    homo = self._build_homogeneous_data(data)
    x, edge_index = homo.x, homo.edge_index
    print(f"[DEBUG] x shape: {x.shape}")
    print(f"[DEBUG] edge_index shape: {edge_index.shape}")
    
    src, dst = edge_index
    cos_sim = F.cosine_similarity(x[src], x[dst])
    print(f"[DEBUG] cos_sim shape: {cos_sim.shape}")
    ...
```

### 2. NaN/Inf Checking

```python
def check_tensor_health(x, name="tensor"):
    if torch.isnan(x).any():
        print(f"⚠️  {name} contains NaN!")
    if torch.isinf(x).any():
        print(f"⚠️  {name} contains Inf!")
    if (x == 0).all():
        print(f"⚠️  {name} is all zeros!")
    print(f"Stats for {name}: min={x.min():.4f}, max={x.max():.4f}, mean={x.mean():.4f}")
```

### 3. Gradient Flow

```python
def check_gradients(model):
    for name, param in model.named_parameters():
        if param.grad is None:
            print(f"✗ {name}: no gradient")
        else:
            print(f"✓ {name}: grad mean={param.grad.mean():.4f}, grad max={param.grad.max():.4f}")
```

---

## 📈 Mở Rộng Dự Án

### 1. Thêm Attention Mechanism

```python
class AttentionGCNCov(nn.Module):
    def __init__(self, ...):
        super().__init__()
        self.attention = torch.nn.MultiheadAttention(...)
        self.gcn = GCNConv(...)
    
    def forward(self, x, edge_index):
        # Compute attention weights over edge features
        attn_out, _ = self.attention(x, x, x)
        x = self.gcn(attn_out, edge_index)
        return x
```

### 2. Thêm Knowledge Graph Integration

```python
# Load từ external knowledge graph (e.g., DrugBank)
def load_external_knowledge(kb_path):
    # Tích hợp thêm edges từ knowledge base
    return additional_edges

# Merge vào main graph
def build_enriched_hetero_data(...):
    ...
    # Thêm external edges
    external = load_external_knowledge(...)
    ...
```

### 3. Thêm Explainability

```python
def get_edge_importance(model, data, edge_index):
    """Compute edge importance score."""
    edge_importance = torch.abs(model.get_edge_weights(data, edge_index))
    return edge_importance

def plot_influential_paths(drug_id, disease_id, top_k=3):
    """Show top-K influential paths."""
    ...
```

### 4. REST API (FastAPI)

```python
# backend/app/main.py
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

class PredictionRequest(BaseModel):
    drug_id: int
    top_k: int = 5

@app.post("/predict")
async def predict(request: PredictionRequest):
    # Load model
    # Inference
    # Return results
    return {"predictions": [...]}

# Run: uvicorn backend.app.main:app --reload
```

---

## 📊 Performance Optimization

### 1. Batch Processing Inference

```python
def batch_infer(model, data, drug_ids, batch_size=32):
    """Infer for multiple drugs at once."""
    embeddings = model(data)
    
    all_scores = []
    for i in range(0, len(drug_ids), batch_size):
        batch_ids = drug_ids[i:i+batch_size]
        drug_embs = embeddings[batch_ids]
        disease_embs = embeddings[num_drugs:]
        
        scores = torch.matmul(drug_embs, disease_embs.T)  # [batch_size, num_diseases]
        all_scores.append(scores)
    
    return torch.cat(all_scores, dim=0)
```

### 2. Model Quantization

```python
# Quantize trained model for inference
model.eval()
quantized_model = torch.quantization.quantize_dynamic(
    model, {torch.nn.Linear}, dtype=torch.qint8
)
```

### 3. Caching Embeddings

```python
# Cache embeddings sau khi compute 1 lần
class CachedInference:
    def __init__(self, model, data):
        with torch.no_grad():
            self.embeddings = model(data)
    
    def predict(self, drug_id, top_k):
        drug_emb = self.embeddings[drug_id]
        disease_embs = self.embeddings[num_drugs:]
        scores = torch.matmul(drug_emb, disease_embs.T)
        return torch.topk(scores, top_k)
```

---

## 🐛 Common Issues & Solutions

| Issue | Cause | Solution |
|-------|-------|----------|
| CUDA out of memory | Model quá lớn | Giảm hidden_dim, batch size |
| NaN loss | Learning rate quá cao | Giảm lr từ 1e-3 → 1e-4 |
| Overfitting | Không có regularization | Thêm dropout, giảm neg_ratio |
| Slow inference | Toàn bộ model trên GPU | Cache embeddings, chỉ forward 1 lần |
| Poor accuracy | Tuyệt đối | Kiểm tra data quality, thử hyperparameters khác |

---

## 📚 Further Reading

- PyTorch Geometric Docs: https://pytorch-geometric.readthedocs.io/
- GCN Paper: Kipf & Welling (2016)
- Fuzzy Neural Networks: Nguyen et al. (2023)

---

**Được cập nhật**: Tháng 4, 2026
