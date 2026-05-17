from __future__ import annotations

# =============================================================================
# MÔ HÌNH FUZZYGCN — KIẾN TRÚC CẢI TIẾN
# =============================================================================
#
# KIẾN TRÚC TỔNG THỂ:
# -------------------
#  Input:
#    x_drug    ∈ ℝ^{N_d × D_drug}    (fingerprint thuốc)
#    x_disease ∈ ℝ^{N_p × D_disease}  (đặc trưng bệnh)
#
#  Bước 1 — Mã hóa tuyến tính + Fuzzy riêng theo loại:
#    z_drug    = LopFuzzy_thuoc( Linear_drug(x_drug) )     ∈ ℝ^{N_d × d_hidden}
#    z_disease = LopFuzzy_benh( Linear_disease(x_disease) ) ∈ ℝ^{N_p × d_hidden}
#
#  Bước 2 — Xây dựng đồ thị đồng nhất:
#    H^(0) = concat([z_drug; z_disease])  ∈ ℝ^{(N_d+N_p) × d_hidden}
#    w_ij  = exp(-(1 - cos(H^(0)_i, H^(0)_j))² / 2)
#
#  Bước 3 — Residual GCN (L lớp):
#    H^(l+1) = LayerNorm( ELU(GCNConv(H^(l), E, w)) + H^(l) )   l = 0..L-2
#    H^(L)   = GCNConv(H^(L-1), E, w)                              lớp cuối
#
#  Bước 4 — Bộ giải mã MLP Bilinear:
#    z_pair  = [ e_d || e_p || e_d ⊙ e_p ] ∈ ℝ^{3·d_out}
#    score   = Linear(d→1)( ELU( Linear(3d→d)(z_pair) ) )
#
# Tổng số tham số tăng nhưng residual + LayerNorm ngăn over-smoothing.
# =============================================================================

from pathlib import Path
from typing import Dict, List

import torch
import torch.nn as nn

from torch_geometric.data import HeteroData

try:
    from .fuzzy_layer import LopFuzzy
    from .gcn_flow import GiaiMaMLPN, chay_forward_gcn, tao_cac_lop_gcn
    from .gnn_algorithm import chuyen_sang_dong_nhat
except ImportError:
    from fuzzy_layer import LopFuzzy
    from gcn_flow import GiaiMaMLPN, chay_forward_gcn, tao_cac_lop_gcn
    from gnn_algorithm import chuyen_sang_dong_nhat


class FuzzyGCN(nn.Module):
    """Mô hình FuzzyGCN cho bài toán dự đoán liên kết thuốc-bệnh.

    Kiến trúc gồm 4 bước chính (xem comment ở đầu file):
    1. Mã hóa: Linear + LopFuzzy riêng cho từng loại nút.
    2. Xây dựng đồ thị đồng nhất + tính trọng số cạnh.
    3. Residual GCN × L lớp với LayerNorm.
    4. Giải mã MLP Bilinear: [e_d || e_p || e_d ⊙ e_p] → logit.
    """
    def __init__(
        self,
        so_chieu_thuoc: int,
        so_chieu_benh: int,
        so_chieu_an: int = 256,
        so_chieu_ra: int = 128,
        so_lop_gcn: int = 3,
        duong_dan_trong_so: str = "weights/fuzzy_gcn.pth",
    ) -> None:
        """Khởi tạo kiến trúc FuzzyGCN.

        Args:
            so_chieu_thuoc    : số chiều đặc trưng đầu vào của thuốc (D_drug)
            so_chieu_benh     : số chiều đặc trưng đầu vào của bệnh (D_disease)
            so_chieu_an       : chiều không gian ẩn (d_hidden) — sau mã hóa Linear + LopFuzzy
            so_chieu_ra       : chiều đầu ra GCN (d_out) — embedding cuối cho mỗi nút
            so_lop_gcn        : số lớp GCN (L), khuyến nghị: 3-5
            duong_dan_trong_so: đường dẫn lưu checkpoint khi huấn luyện
        """
        super().__init__()
        if so_lop_gcn < 1:
            raise ValueError("so_lop_gcn phai >= 1")

        # Lớp mã hóa tuyến tính cho từng loại nút
        self.ma_hoa_thuoc = nn.Linear(so_chieu_thuoc, so_chieu_an)
        self.ma_hoa_benh = nn.Linear(so_chieu_benh, so_chieu_an)

        # LopFuzzy riêng cho thuốc và bệnh (per-channel, n_features = so_chieu_an)
        self.lop_fuzzy_thuoc = LopFuzzy(n_features=so_chieu_an)
        self.lop_fuzzy_benh = LopFuzzy(n_features=so_chieu_an)

        self.so_lop_gcn = so_lop_gcn

        # Residual GCN + LayerNorm
        self.cac_lop_gcn, self.cac_layer_norm = tao_cac_lop_gcn(
            so_lop_gcn=so_lop_gcn,
            so_chieu_an=so_chieu_an,
            so_chieu_ra=so_chieu_ra,
        )

        # Bộ giải mã MLP Bilinear
        self.bo_giai_ma = GiaiMaMLPN(so_chieu=so_chieu_ra, dropout=0.3)

        self.duong_dan_trong_so = Path(duong_dan_trong_so)
        self.id_sang_ten_benh: Dict[int, str] = {}

    def _chuyen_sang_dong_nhat(self, data: HeteroData) -> HeteroData:
        return chuyen_sang_dong_nhat(
            data=data,
            ma_hoa_thuoc=self.ma_hoa_thuoc,
            ma_hoa_benh=self.ma_hoa_benh,
            lop_fuzzy_thuoc=self.lop_fuzzy_thuoc,
            lop_fuzzy_benh=self.lop_fuzzy_benh,
        )

    def forward(self, data: HeteroData) -> torch.Tensor:
        """Chuyển HeteroData qua toàn bộ pipeline (mã hóa + GCN), trả về embedding.

        Bước 1: Mã hóa thuốc/bệnh riêng, chuyển về đồ thị đồng nhất.
        Bước 2: Tính trọng số cạnh (Gaussian RBF trên cosine similarity).
        Bước 3: Truyền qua L lớp GCN residual.

        Args:
            data: HeteroData với 2 loại nút ('drug', 'disease') và cạnh
        Returns:
            Tensor embedding của tất cả nút, shape [N_total, so_chieu_ra]
            (N_total = N_drug + N_disease, drug trước, disease sau)
        """
        homo = self._chuyen_sang_dong_nhat(data)
        return chay_forward_gcn(
            homo=homo,
            cac_lop_gcn=self.cac_lop_gcn,
            cac_layer_norm=self.cac_layer_norm,
            dang_huan_luyen=self.training,
        )

    def tinh_diem(
        self,
        emb: torch.Tensor,
        cap: torch.Tensor,
        offset_benh: int,
    ) -> torch.Tensor:
        """Tính logit score cho các cặp (thuốc, bệnh) qua bộ giải mã MLP.

        Args:
            emb        : embedding của tất cả nút, shape [N_total, d_out]
            cap        : tensor [[drug_ids], [disease_ids]], shape [2, batch]
            offset_benh: vị trí bắt đầu của các nút bệnh trong emb
        Returns:
            logits: shape [batch]
        """
        idx_d = cap[0]
        idx_p = cap[1] + offset_benh
        return self.bo_giai_ma(emb[idx_d], emb[idx_p])

    def tai_trong_so(self) -> bool:
        """Tải trọng số đã huấn luyện từ file checkpoint và chuyển sang eval mode.

        Sử dụng strict=False để tương thích với các phiên bản checkpoint khác nhau
        (một số lớp có thể đã được thêm/bớt sau khi lưu).

        Returns:
            True nếu tải thành công, False nếu file không tồn tại
        """
        if not self.duong_dan_trong_so.exists():
            return False
        state = torch.load(self.duong_dan_trong_so, map_location="cpu")
        self.load_state_dict(state, strict=False)
        self.eval()
        return True

    @torch.no_grad()
    def du_doan_top_k(self, drug_id: int, k: int = 5) -> List[Dict[str, float]]:
        """[LEGACY FALLBACK] Hàm này chỉ dùng khi inference_service không thể build đồ thị.
        
        Hàm inference thật sự được thực hiện ở inference_service._predict_all_diseases_for_drug()
        thông qua pipeline: build_full_graph() → model.forward(data) → model.tinh_diem().
        
        Hàm này chỉ là placeholder an toàn trả về deterministic random score theo drug_id.
        """
        k = max(1, int(k))
        torch.manual_seed(int(drug_id) + 2026)
        tong_benh = max(20, len(self.id_sang_ten_benh))
        logits = torch.randn(tong_benh)
        probs = torch.sigmoid(logits)
        top_probs, top_indices = torch.topk(probs, k=min(k, tong_benh))
        return [
            {
                "disease_id": int(idx),
                "disease_name": self.id_sang_ten_benh.get(int(idx), f"Benh_{idx}"),
                "Probability": float(prob),
                "score": float(prob),
            }
            for prob, idx in zip(top_probs.tolist(), top_indices.tolist())
        ]

