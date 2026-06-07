from __future__ import annotations

# =============================================================================
# LUỒNG GCN: RESIDUAL + LAYERNORM + BỘ GIẢI MÃ MLP
# =============================================================================
#
# CÔNG THỨC TOÁN HỌC:
# -------------------
# A. Edge Weight (Gaussian RBF trên cosine similarity):
#       cos_ij = cosine_similarity(h_i, h_j) ∈ [-1, 1]
#       w_ij   = exp( -(1 - cos_ij)² / 2 )         ∈ (0, 1]
#
# B. Residual GCN với LayerNorm (cho mỗi lớp ẩn l = 0..L-2):
#       h̃^(l)   = GCNConv(h^(l), E, w)
#       h^(l+1) = LayerNorm( ELU(h̃^(l)) + h^(l) )   ← residual nếu dim bằng nhau
#   Lớp cuối (l = L-1):
#       h^(L)   = GCNConv(h^(L-1), E, w)            ← không residual / activation
#
#   Lưu ý: ELU thay ReLU → gradient âm có ích, hội tụ mượt hơn với GCN.
#
# C. Bộ giải mã MLP Bilinear (GiaiMaMLPN):
#       z       = [ e_d  ||  e_p  ||  e_d ⊙ e_p ] ∈ ℝ^{3·d_out}
#       s(d,p)  = Linear(d→1)( ELU( Linear(3d→d)(z) ) )
#
#   Dùng đặc trưng nối (concatenation) + tích element-wise → mô hình hóa
#   quan hệ phi tuyến giữa thuốc và bệnh tốt hơn tích vô hướng đơn thuần.
# =============================================================================

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch_geometric.data import Data
from torch_geometric.nn import GCNConv


# ── Bộ giải mã MLP Bilinear ──────────────────────────────────────────────────

class GiaiMaMLPN(nn.Module):
    """Bộ giải mã MLP: z = [e_d || e_p || e_d⊙e_p] → Linear → ELU → Linear → score.

    Tham số:
        so_chieu  : chiều của embedding đầu vào (d_out của GCN).
        dropout   : tỉ lệ dropout trong MLP (mặc định 0.3).
    """

    def __init__(self, so_chieu: int, dropout: float = 0.3) -> None:
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(3 * so_chieu, so_chieu),
            nn.ELU(),
            nn.Dropout(p=dropout),
            nn.Linear(so_chieu, 1),
        )

    def forward(self, e_d: torch.Tensor, e_p: torch.Tensor) -> torch.Tensor:
        # z = [e_d || e_p || e_d ⊙ e_p]
        z = torch.cat([e_d, e_p, e_d * e_p], dim=-1)
        return self.net(z).squeeze(-1)  # shape: [batch]


# ── Tạo layers GCN + LayerNorms ───────────────────────────────────────────────

def tao_cac_lop_gcn(
    so_lop_gcn: int,
    so_chieu_an: int,
    so_chieu_ra: int,
) -> tuple[nn.ModuleList, nn.ModuleList]:
    """Trả về (cac_lop_gcn, cac_layer_norm).

    Mỗi lớp ẩn (không phải lớp cuối) có một LayerNorm tương ứng để dùng sau
    skip-connection. Lớp cuối không có LayerNorm (kết quả embedding thô).
    """
    cac_lop_gcn = nn.ModuleList()
    cac_layer_norm = nn.ModuleList()

    if so_lop_gcn == 1:
        cac_lop_gcn.append(GCNConv(so_chieu_an, so_chieu_ra))
        return cac_lop_gcn, cac_layer_norm

    # Lớp đầu: an → an
    cac_lop_gcn.append(GCNConv(so_chieu_an, so_chieu_an))
    cac_layer_norm.append(nn.LayerNorm(so_chieu_an))

    # Các lớp ẩn giữa: an → an
    for _ in range(so_lop_gcn - 2):
        cac_lop_gcn.append(GCNConv(so_chieu_an, so_chieu_an))
        cac_layer_norm.append(nn.LayerNorm(so_chieu_an))

    # Lớp cuối: an → ra (không có LayerNorm/residual)
    cac_lop_gcn.append(GCNConv(so_chieu_an, so_chieu_ra))

    return cac_lop_gcn, cac_layer_norm


# ── Tính trọng số cạnh ───────────────────────────────────────────────────────

def tinh_trong_so_canh(x: torch.Tensor, edge_index: torch.Tensor) -> torch.Tensor:
    """Gaussian RBF trên cosine similarity: w_ij = exp(-(1 - cos_ij)² / 2)."""
    src, dst = edge_index
    cos_sim = F.cosine_similarity(x[src], x[dst])
    return torch.exp(-((1.0 - cos_sim) ** 2) / 2.0)


# ── Lan truyền qua các lớp GCN ────────────────────────────────────────────────

def truyen_qua_cac_lop_gcn(
    x: torch.Tensor,
    edge_index: torch.Tensor,
    edge_weight: torch.Tensor,
    cac_lop_gcn: nn.ModuleList,
    cac_layer_norm: nn.ModuleList,
    dang_huan_luyen: bool,
) -> torch.Tensor:
    """Chạy qua toàn bộ các lớp GCN với residual connection + LayerNorm.

    Công thức cho lớp ẩn l (l < L-1):
        h̃^(l)   = GCNConv(h^(l), E, w)
        h^(l+1) = LayerNorm( ELU(h̃^(l)) + h^(l) )

    Lớp cuối L-1:
        h^(L) = GCNConv(h^(L-1), E, w)
    """
    n_layers = len(cac_lop_gcn)
    for i, lop in enumerate(cac_lop_gcn):
        h = lop(x, edge_index, edge_weight=edge_weight)
        if i < n_layers - 1:  # Lớp ẩn: ELU + Dropout + Residual + LayerNorm
            h = F.elu(h)
            h = F.dropout(h, p=0.3, training=dang_huan_luyen)
            if h.shape == x.shape:  # Residual chỉ khi chiều khớp
                h = h + x
            h = cac_layer_norm[i](h)
        x = h
    return x


# ── Forward GCN tổng hợp ─────────────────────────────────────────────────────

def chay_forward_gcn(
    homo: Data,
    cac_lop_gcn: nn.ModuleList,
    cac_layer_norm: nn.ModuleList,
    dang_huan_luyen: bool,
) -> torch.Tensor:
    """Luồng forward GCN tổng hợp: tính trọng số cạnh → truyền qua các lớp GCN.

    Đây là hàm entry point cho GCN, kết hợp 2 bước:
    1. tinh_trong_so_canh: tính w_ij = Gaussian RBF(cosine_similarity(h_i, h_j))
    2. truyen_qua_cac_lop_gcn: L lớp GCNConv với residual + LayerNorm

    Args:
        homo            : đồ thị đồng nhất (HeteroData đã chuyển về Data)
                          cần có homo.x và homo.edge_index
        cac_lop_gcn     : ModuleList L GCNConv layers
        cac_layer_norm  : ModuleList (L-1) LayerNorm (cho lớp ẩn)
        dang_huan_luyen : True khi training (bật Dropout), False khi eval
    Returns:
        Tensor embedding [N_total, so_chieu_ra], đã trải qua toàn bộ GCN
    """
    x, edge_index = homo.x, homo.edge_index
    edge_weight = tinh_trong_so_canh(x, edge_index)
    return truyen_qua_cac_lop_gcn(
        x=x,
        edge_index=edge_index,
        edge_weight=edge_weight,
        cac_lop_gcn=cac_lop_gcn,
        cac_layer_norm=cac_layer_norm,
        dang_huan_luyen=dang_huan_luyen,
    )
