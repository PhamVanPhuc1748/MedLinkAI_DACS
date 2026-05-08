from __future__ import annotations

# =============================================================================
# CHUYỂN ĐỒ THỊ DỊ ĐỒNG NHẤT → ĐỒNG NHẤT VỚI FUZZY RIÊNG THEO LOẠI NÚT
# =============================================================================
#
# CÔNG THỨC:
#   Thuốc:  z_drug    = LopFuzzy_thuoc( Linear_drug(x_drug) )
#   Bệnh:   z_disease = LopFuzzy_benh( Linear_disease(x_disease) )
#
#   Mỗi loại nút có LopFuzzy riêng (μ_thuoc, σ_thuoc ≠ μ_benh, σ_benh),
#   cho phép mô hình học ngưỡng nhiễu khác nhau cho thuốc và bệnh.
# =============================================================================

import torch
import torch.nn.functional as F
from torch_geometric.data import HeteroData


def chuyen_sang_dong_nhat(
    data: HeteroData,
    ma_hoa_thuoc: torch.nn.Module,
    ma_hoa_benh: torch.nn.Module,
    lop_fuzzy_thuoc: torch.nn.Module,
    lop_fuzzy_benh: torch.nn.Module,
) -> HeteroData:
    """Mã hóa từng loại nút qua Linear + LopFuzzy riêng, chuyển về đồ thị đồng nhất.

    Tại sao mã hóa riêng và sau đó mới gom lại?
    - Thuốc và bệnh có không gian đặc trưng rất khác nhau:
        + Thuốc: fingerprint nhị phân (Morgan, ECFP), mol2vec, GIP
        + Bệnh: OMIM phenotype similarity, GIP, ES features
    - Mã hóa riêng trước đưa vào không gian chung giúp mỗi loại học
      biểu diễn đặc trưng hợp lý cho loại của mình.
    - LopFuzzy riêng: ngưỡng membership khác nhau cho thuốc/bệnh (phù hợp).

    Sau khi mã hóa, to_homogeneous() gom tất cả nút thành 1 tensor x duy nhất,
    thuốc đặt trước (index 0..N_drug-1), bệnh sau (index N_drug..N_total-1).

    Công thức:
        z_drug    = LopFuzzy_thuoc( W_drug · x_drug )    ∈ ℝ^{N_d × d_hidden}
        z_disease = LopFuzzy_benh( W_disease · x_disease ) ∈ ℝ^{N_p × d_hidden}

    Args:
        data           : HeteroData với 2 loại nút ('drug', 'disease')
        ma_hoa_thuoc   : Linear(D_drug, d_hidden)
        ma_hoa_benh    : Linear(D_disease, d_hidden)
        lop_fuzzy_thuoc: LopFuzzy(n_features=d_hidden) cho thuốc
        lop_fuzzy_benh : LopFuzzy(n_features=d_hidden) cho bệnh
    Returns:
        Data đồng nhất với x ∈ ℝ^{N_total × d_hidden} và edge_index đã chuyển đổi
    """
    data = data.clone()
    # z_drug    = LopFuzzy_thuoc( W_drug · x_drug )
    data["drug"].x = lop_fuzzy_thuoc(ma_hoa_thuoc(data["drug"].x))
    # z_disease = LopFuzzy_benh( W_disease · x_disease )
    data["disease"].x = lop_fuzzy_benh(ma_hoa_benh(data["disease"].x))
    return data.to_homogeneous(node_attrs=["x"])


def tinh_trong_so_canh(x: torch.Tensor, edge_index: torch.Tensor) -> torch.Tensor:
    """Tính trọng số cạnh bằng Gaussian RBF trên cosine similarity.

    Công thức:
        cos_ij = cosine_similarity(h_i, h_j)   ∈ [-1, 1]
        w_ij   = exp( -(1 - cos_ij)² / 2 )    ∈ (0, 1]

    Ý nghĩa:
    - cos_ij = 1  (cùng hướng)  → w = exp(0) = 1.0  (cạnh mạnh nhất)
    - cos_ij = 0  (vuông góc)   → w = exp(-0.5) ≈ 0.61
    - cos_ij = -1 (ngược hướng) → w = exp(-2) ≈ 0.14 (cạnh yếu nhất)

    Tại sao dùng cosine thay Euclidean?
    - Cosine bất biến với độ dài vector → đo đ là hướng quan trọng hơn độ lớn.
    - Phù hợp cho embedding học từ minhim đã được chuẩn hóa.

    Args:
        x         : embedding tất cả nút, shape [N, d]
        edge_index: cạnh [2, E] (hàng 0: src, hàng 1: dst)
    Returns:
        Tensor trọng số [E], giá trị ∈ (0, 1]
    """
    # Gaussian RBF trên cosine similarity: w_ij = exp(-(1 - cos_ij)² / 2)
    src, dst = edge_index
    cos_sim = F.cosine_similarity(x[src], x[dst])
    return torch.exp(-((1.0 - cos_sim) ** 2) / 2.0)


def truyen_qua_cac_lop_gcn(
    x: torch.Tensor,
    edge_index: torch.Tensor,
    edge_weight: torch.Tensor,
    cac_lop_gcn: torch.nn.ModuleList,
    cac_layer_norm: torch.nn.ModuleList,
    dang_huan_luyen: bool,
) -> torch.Tensor:
    """Residual GCN: h^(l+1) = LayerNorm( ELU(GCN(h^(l))) + h^(l) ).

    Chi tiết công thức:
    - Lớp ẩn (l < L-1):
        h̃^(l)   = GCNConv(h^(l), E, w)             # message passing có trọng số
        h^(l+1) = LayerNorm( ELU(h̃^(l)) + h^(l) ) # residual nếu same dim
    - Lớp cuối (l = L-1):
        h^(L)   = GCNConv(h^(L-1), E, w)             # không có residual / activation

    Tại sao Residual?
    - GCN nhiều lớp bị over-smoothing: tất cả nút hội tụ về cùng vector.
    - Skip-connection giúp giữ thông tin lớp trước, tránh gradient vanishing.

    Tại sao LayerNorm (không phải BatchNorm)?
    - BatchNorm nhạy cảm với batch size nhỏ (batch trên đồ thị thường nhỏ).
    - LayerNorm chuẩn hóa theo chiều feature → ổn định hơn với graph.

    Args:
        x              : embedding ban đầu [N, d]
        edge_index     : [2, E]
        edge_weight    : [E] trọng số cạnh
        cac_lop_gcn    : L GCNConv layers
        cac_layer_norm : (L-1) LayerNorm layers
        dang_huan_luyen: bật Dropout khi train
    Returns:
        Embedding sau L lớp GCN [N, d_out]
    """
    n_layers = len(cac_lop_gcn)
    for i, lop in enumerate(cac_lop_gcn):
        h = lop(x, edge_index, edge_weight=edge_weight)
        if i < n_layers - 1:
            h = F.elu(h)
            h = F.dropout(h, p=0.3, training=dang_huan_luyen)
            if h.shape == x.shape:
                h = h + x
            h = cac_layer_norm[i](h)
        x = h
    return x
