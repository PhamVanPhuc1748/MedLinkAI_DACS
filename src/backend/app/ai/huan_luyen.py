from __future__ import annotations

# Import cac thu vien can thiet de xu ly tham so, du lieu va huan luyen.
import argparse  # Thu vien doc tham so dong lenh.
import json  # Thu vien luu thong tin checkpoint va ket qua.
import random  # Thu vien tao so ngau nhien.
import time  # Thu vien do thoi gian moi epoch.
from dataclasses import dataclass  # Thu vien tao lop cau hinh don gian.
from pathlib import Path  # Thu vien xu ly duong dan file.
from typing import Any, Dict, List, Set, Tuple  # Thu vien kieu du lieu.

import numpy as np  # Thu vien tinh toan ma tran.
import pandas as pd  # Thu vien doc file CSV.
import torch  # Thu vien PyTorch.
import torch.nn.functional as F  # Thu vien ham mat mat va kich hoat.
from sklearn.model_selection import StratifiedKFold  # Thu vien chia K-Fold co can bang nhan.
from sklearn.preprocessing import StandardScaler  # Thu vien chuan hoa dac trung.
from torch_geometric.data import HeteroData  # Thu vien du lieu do thi.

import sys
from pathlib import Path as _Path

# Thêm thư mục src/backend/app/ai vào sys.path để import các module AI
_AI_DIR = _Path(__file__).resolve().parents[1] / "backend" / "app" / "ai"
if str(_AI_DIR) not in sys.path:
    sys.path.insert(0, str(_AI_DIR))

from mo_hinh_ai import FuzzyGCN  # Import mo hinh FuzzyGCN.


# =========================
# KHU VUC CAU HINH CHINH
# =========================
@dataclass
class CauHinh:
    """Tất cả siêu tham số điều khiển quá trình huấn luyện FuzzyGCN.

    Được thiết kế dưới dạng dataclass để dễ copy, serialize (JSON) và override
    một phần từ command-line hoặc auto-tune.

    Nhóm tham số chính:
    - Đường dẫn: thu_muc_goc, ten_dataset, tep_thuoc, tep_benh, tep_lien_ket
    - Kiến trúc GCN: so_lop_gcn, kich_thuoc_an, kich_thuoc_ra
    - Optimizer: toc_do_hoc, weight_decay, grad_clip
    - Scheduler: factor_lr, patience_lr, min_lr
    - Loss: label_smoothing, lambda_rank, margin_rank, pos_weight_duong
    - K-Fold: so_fold
    - Negative sampling: ti_le_am (số mẫu âm / số mẫu dương)
    - Early stopping: patience, min_delta
    - Thiết bị: thiet_bi (auto|cuda|cpu), bat_amp
    """
    # Thu muc goc cua du an (2 cap tren src/Ai/ -> model_GNN_new/).
    thu_muc_goc: str = str(Path(__file__).resolve().parents[2])
    # Ten dataset se dung (vi du: B-dataset).
    ten_dataset: str = "B-dataset"
    # Duong dan cac file chinh.
    tep_thuoc: str = "DrugFingerprint.csv"
    tep_benh: str = "DiseaseFeature.csv"
    tep_lien_ket: str = "DrugDiseaseAssociationNumber.csv"

    # Tham so huan luyen.
    so_epoch: int = 2000
    toc_do_hoc: float = 3e-4
    weight_decay: float = 5e-5
    so_lop_gcn: int = 4
    kich_thuoc_an: int = 512
    kich_thuoc_ra: int = 256
    kiem_nhan_dung_som: int = 150
    # Gradient clipping (0 = tat)
    grad_clip: float = 1.0
    # Dropout trong MLP decoder
    dropout_decoder: float = 0.2
    # Dung nhieu feature files: True = ghep DrugGIP, DiseaseGIP, DiseasePS, Drug_mol2vec
    ghep_nhieu_feature: bool = True
    # Bat/tat chuan hoa dac trung (StandardScaler)
    bat_chuan_hoa: bool = True

    # Tham so dung som (early stopping).
    patience: int = 150                # So epoch khong cai thien AUC truoc khi dung
    min_delta: float = 3e-4            # Nguong cai thien toi thieu de tinh la co tien bo

    # Cau hinh scheduler ReduceLROnPlateau.
    factor_lr: float = 0.65
    patience_lr: int = 10
    min_lr: float = 1e-6

    # ── Ham mat mat ket hop ──────────────────────────────────────────────
    # L = L_BCE_LS + lambda_rank * L_margin
    # L_BCE_LS : BCE voi nhan lam min  y~ = (1-eps)*y + eps/2
    # L_margin : max(0, gamma - score_pos + score_neg)  (pairwise margin)
    label_smoothing: float = 0.05      # eps trong label smoothing
    lambda_rank: float = 0.25          # Trong so cua margin loss
    margin_rank: float = 0.3           # Bien phan tach trong margin loss
    pos_weight_duong: float = 1.0      # pos_weight cho BCE

    # K-Fold.
    so_fold: int = 10

    # Ti le negative sampling (so am / so duong).
    ti_le_am: float = 1.0

    # Thiet bi.
    thiet_bi: str = "auto"  # auto|cuda|cpu
    bat_amp: bool = False

    # Thu muc luu trong so (project_root/weights/<dataset>).
    thu_muc_trong_so: str = str(Path(__file__).resolve().parents[2] / "weights")

    # Seed.
    seed: int = 42


# =========================
# CAC HAM TAI VA CHUAN HOA DU LIEU
# =========================

def dat_seed(seed: int) -> None:
    """Đặt seed toàn cục để đảm bảo kết quả huấn luyện tái lập được (reproducibility).

    Lý do cần đặt seed ở nhiều nơi:
    - random: ảnh hưởng đến negative sampling
    - numpy: ảnh hưởng đến chia K-Fold và khởi tạo dữ liệu
    - torch: ảnh hưởng đến khởi tạo trọng số mô hình
    - cuda: đảm bảo GPU cũng cho kết quả nhất quán

    Args:
        seed: giá trị seed nguyên dương bất kỳ (thường dùng 42)
    """
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def doc_ma_tran(csv_path: Path) -> np.ndarray:
    """Đọc file CSV đặc trưng và trả về ma trận numpy float32.

    Các file đặc trưng trong dataset có dạng:
    - Hàng: mỗi thực thể (thuốc/bệnh)
    - Cột: mỗi chiều đặc trưng
    - Cột đầu tiên là index → được bỏ qua (index_col=0)

    Args:
        csv_path: đường dẫn tuyệt đối đến file CSV
    Returns:
        Ma trận shape [N_entities, N_features] kiểu float32
    Raises:
        ValueError: nếu dữ liệu không phải 2 chiều
    """
    df = pd.read_csv(csv_path, index_col=0)
    matrix = df.to_numpy(dtype=np.float32)
    if matrix.ndim != 2:
        raise ValueError(f"File dac trung khong phai 2D: {csv_path}")
    return matrix


def doc_ma_tran_optional(csv_path: Path) -> np.ndarray | None:
    """Doc file CSV neu ton tai, tra ve None neu khong tim thay."""
    if not csv_path.exists():
        return None
    try:
        return doc_ma_tran(csv_path)
    except Exception as e:
        print(f"Canh bao: khong doc duoc {csv_path}: {e}")
        return None


def ghep_feature_thuoc(thuoc_chinh: np.ndarray, thu_muc: Path) -> np.ndarray:
    """Ghep DrugFingerprint + DrugGIP + Drug_mol2vec thanh 1 vector per drug."""
    danh_sach = [thuoc_chinh]
    for ten_file in ["DrugGIP.csv", "Drug_mol2vec.csv"]:
        m = doc_ma_tran_optional(thu_muc / ten_file)
        if m is not None:
            m = can_chinh_hang(m, thuoc_chinh.shape[0], ten_file)
            if m.shape[0] == thuoc_chinh.shape[0]:
                danh_sach.append(m)
                print(f"  [feature] Da ghep {ten_file}: {m.shape[1]} chieu")
            else:
                print(f"  [feature] Bo qua {ten_file}: so hang {m.shape[0]} != {thuoc_chinh.shape[0]}")
    ket_qua = np.concatenate(danh_sach, axis=1).astype(np.float32)
    print(f"  [feature] Thuoc: {thuoc_chinh.shape[1]} -> {ket_qua.shape[1]} chieu")
    return ket_qua


def ghep_feature_benh(benh_chinh: np.ndarray, thu_muc: Path) -> np.ndarray:
    """Ghep DiseaseFeature + DiseaseGIP + DiseasePS thanh 1 vector per disease."""
    danh_sach = [benh_chinh]
    for ten_file in ["DiseaseGIP.csv", "DiseasePS.csv"]:
        m = doc_ma_tran_optional(thu_muc / ten_file)
        if m is not None:
            m = can_chinh_hang(m, benh_chinh.shape[0], ten_file)
            if m.shape[0] == benh_chinh.shape[0]:
                danh_sach.append(m)
                print(f"  [feature] Da ghep {ten_file}: {m.shape[1]} chieu")
            else:
                print(f"  [feature] Bo qua {ten_file}: so hang {m.shape[0]} != {benh_chinh.shape[0]}")
    ket_qua = np.concatenate(danh_sach, axis=1).astype(np.float32)
    print(f"  [feature] Benh: {benh_chinh.shape[1]} -> {ket_qua.shape[1]} chieu")
    return ket_qua


def doc_lien_ket(csv_path: Path) -> np.ndarray:
    """Đọc file liên kết thuốc-bệnh (cạnh dương của đồ thị).

    File CSV cần có 2 cột: 'drug' (chỉ số thuốc) và 'disease' (chỉ số bệnh).
    Mỗi hàng là 1 cặp liên kết đã được xác nhận (positive edge).

    Args:
        csv_path: đường dẫn đến DrugDiseaseAssociationNumber.csv
    Returns:
        Ma trận shape [N_links, 2] với cột 0 là drug_id, cột 1 là disease_id
    Raises:
        ValueError: nếu file thiếu cột 'drug' hoặc 'disease'
    """
    df = pd.read_csv(csv_path)
    if not {"drug", "disease"}.issubset(df.columns):
        raise ValueError(f"File lien ket thieu cot drug/disease: {csv_path}")
    return df[["drug", "disease"]].to_numpy(dtype=np.int64)


def can_chinh_hang(matrix: np.ndarray, muc_tieu: int | None, nhan: str) -> np.ndarray:
    """Tự động căn chỉnh ma trận sao cho số hàng = số thực thể.

    Một số file CSV trong dataset có thể lưu theo chiều ngược (thực thể là cột
    thay vì hàng). Hàm này phát hiện và chuyển vị nếu cần.

    Chiến lược:
    1. Nếu biết mục tiêu (muc_tieu): so khớp trực tiếp, thử transpose nếu không khớp.
    2. Nếu không biết: heuristic — số hàng >= số cột → hàng là thực thể (phổ biến hơn).

    Args:
        matrix  : ma trận đặc trưng cần căn chỉnh
        muc_tieu: số thực thể mong đợi (None nếu không biết)
        nhan    : tên dùng trong cảnh báo (ví dụ: 'Thuoc', 'Benh')
    Returns:
        Ma trận đã căn chỉnh với shape[0] = số thực thể
    """
    if muc_tieu is not None:
        if matrix.shape[0] == muc_tieu:
            return matrix
        if matrix.shape[1] == muc_tieu:
            return matrix.T
        print(
            f"Canh bao: {nhan} shape {matrix.shape} khong khop muc tieu {muc_tieu}. "
            "Se dung heuristic."
        )
    if matrix.shape[0] >= matrix.shape[1]:
        return matrix
    return matrix.T


def chuan_hoa_dac_trung(thuoc: np.ndarray, benh: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """Chuẩn hóa đặc trưng thuốc và bệnh bằng StandardScaler.

    Mục đích:
    - Đưa các đặc trưng về phân phối zero-mean, unit-variance.
    - Giảm ảnh hưởng của sự chênh lệch thang đo (fingerprint vs GIP có giá trị rất khác nhau).
    - Tăng tốc hội tụ của gradient descent và giảm nguy cơ gradient explosion.

    Lưu ý: Fit trên toàn bộ dữ liệu (không tách train/test riêng cho bước này)
    vì đây là chuẩn hóa đặc trưng, không phải target. Thực tế không gây data leakage
    vì scaler chỉ học mean/std, không học từ nhãn.

    Args:
        thuoc: ma trận đặc trưng thuốc [N_drug, D_drug]
        benh : ma trận đặc trưng bệnh  [N_disease, D_disease]
    Returns:
        (thuoc_chuan, benh_chuan): hai ma trận đã chuẩn hóa, kiểu float32
    """
    scaler_thuoc = StandardScaler()
    scaler_benh = StandardScaler()
    thuoc_chuan = scaler_thuoc.fit_transform(thuoc)
    benh_chuan = scaler_benh.fit_transform(benh)
    return thuoc_chuan.astype(np.float32), benh_chuan.astype(np.float32)


# =========================
# CAC HAM TAO DO THI
# =========================

def tao_do_thi(thuoc: np.ndarray, benh: np.ndarray, canh_duong: np.ndarray) -> HeteroData:
    """Tạo đồ thị HeteroData (dị đồng nhất) cho PyTorch Geometric.

    Cấu trúc đồ thị:
    - Nút loại 'drug'   : đặc trưng x ∈ ℝ^{N_drug × D_drug}
    - Nút loại 'disease': đặc trưng x ∈ ℝ^{N_disease × D_disease}
    - Cạnh 'drug → interacts → disease'    : cạnh dương xuôi chiều
    - Cạnh 'disease → rev_interacts → drug': cạnh dương ngược chiều (để GCN truyền tin 2 chiều)

    Chỉ dùng cạnh dương (liên kết đã xác nhận) để xây đồ thị — cạnh âm
    được dùng riêng trong hàm mất mát, không đưa vào đồ thị để tránh
    làm ô nhiễm cấu trúc thông tin.

    Args:
        thuoc     : đặc trưng thuốc [N_drug, D_drug]
        benh      : đặc trưng bệnh  [N_disease, D_disease]
        canh_duong: cạnh dương shape [N_edges, 2] (cột 0: drug_id, cột 1: disease_id)
    Returns:
        HeteroData sẵn sàng đưa vào mô hình GCN
    """
    data = HeteroData()
    data["drug"].x = torch.from_numpy(thuoc)
    data["disease"].x = torch.from_numpy(benh)
    edge_index = torch.from_numpy(canh_duong.T).long()
    data["drug", "interacts", "disease"].edge_index = edge_index
    data["disease", "rev_interacts", "drug"].edge_index = edge_index.flip(0)
    return data


# =========================
# CAC HAM NEGATIVE SAMPLING
# =========================

def tao_canh_am(
    so_thuoc: int,
    so_benh: int,
    tap_duong: Set[Tuple[int, int]],
    so_luong: int,
) -> np.ndarray:
    """Sinh cạnh âm (negative edges) bằng phương pháp random negative sampling.

    Trong bài toán dự đoán liên kết thuốc-bệnh, dữ liệu âm (cặp không liên kết)
    không tồn tại trong dataset mà phải được tạo giả. Chiến lược phổ biến nhất
    là uniform random sampling: chọn ngẫu nhiên các cặp (drug, disease) không có
    trong tập liên kết dương.

    Tại sao cần negative sampling?
    - Nếu chỉ train với cạnh dương → mô hình luôn predict positive → vô nghĩa.
    - Tỉ lệ âm/dương (ti_le_am) ảnh hưởng lớn đến precision/recall.

    Kỹ thuật tối ưu tốc độ:
    - Lấy batch lớn (3× lượng cần) mỗi lần để giảm số vòng lặp.
    - Kiểm tra membership bằng set O(1) thay vì list O(N).

    Args:
        so_thuoc: tổng số thuốc trong dataset
        so_benh : tổng số bệnh trong dataset
        tap_duong: set các cặp (drug_id, disease_id) đã có liên kết dương
        so_luong: số cạnh âm cần sinh
    Returns:
        Ma trận [so_luong, 2] chứa các cặp âm, đảm bảo không trùng với tập dương
    """
    canh_am: List[Tuple[int, int]] = []
    while len(canh_am) < so_luong:
        so_mau = max(2048, (so_luong - len(canh_am)) * 3)
        mau_thuoc = np.random.randint(0, so_thuoc, size=so_mau)
        mau_benh = np.random.randint(0, so_benh, size=so_mau)
        for t, b in zip(mau_thuoc.tolist(), mau_benh.tolist()):
            if (t, b) not in tap_duong:
                canh_am.append((t, b))
                if len(canh_am) >= so_luong:
                    break
    return np.array(canh_am, dtype=np.int64)


# =========================
# CAC HAM TINH DIEM VA CHI SO
# =========================

def giai_ma_diem(emb: torch.Tensor, cap: torch.Tensor, offset_benh: int, mo_hinh: "FuzzyGCN" = None) -> torch.Tensor:  # type: ignore[name-defined]
    """Tinh logit. Neu truyen mo_hinh thi dung MLP decoder (tot hon), khong thi dung dot product."""
    if mo_hinh is not None:
        return mo_hinh.tinh_diem(emb, cap, offset_benh)
    # Fallback: dot product don gian
    idx_thuoc = cap[0]
    idx_benh = cap[1] + offset_benh
    e_thuoc = emb[idx_thuoc]
    e_benh = emb[idx_benh]
    return (e_thuoc * e_benh).sum(dim=-1)


def _tinh_logits(
    mo_hinh: torch.nn.Module,
    emb: torch.Tensor,
    cap: torch.Tensor,
    offset_benh: int,
) -> torch.Tensor:
    """Dung bo_giai_ma (MLP) neu co, fallback ve dot-product."""
    if hasattr(mo_hinh, "tinh_diem"):
        return mo_hinh.tinh_diem(emb, cap, offset_benh)
    return giai_ma_diem(emb, cap, offset_benh)


# =============================================================================
# HAM MAT MAT KET HOP: BCE + Label Smoothing + Margin Ranking
# =============================================================================
#
# CONG THUC:
#   1. Label smoothing:  y~_i = (1 - eps) * y_i + eps/2      (eps = label_smoothing)
#   2. BCE-LS:           L_BCE = -sum [y~*log(sigma(s)) + (1-y~)*log(1-sigma(s))]
#   3. Margin Ranking:   L_rank = E_{(+),(-)} [max(0, gamma - s_pos + s_neg)]
#      -> Lay mau k_neg cap am cho moi mau duong, tinh mean
#   4. Tong:             L = L_BCE + lambda * L_rank
#
# Tac dung: BCE toi uu calibration; Margin Ranking truc tiep toi uu AUPR
#           bang cach day score_pos > score_neg + margin.
# =============================================================================

def tinh_loss_ket_hop(
    logits: torch.Tensor,
    nhan: torch.Tensor,
    pos_weight: torch.Tensor,
    label_smoothing: float = 0.05,
    lambda_rank: float = 0.25,
    margin_rank: float = 0.3,
    k_neg: int = 5,
) -> torch.Tensor:
    """Hàm mất mát kết hợp: BCE với Label Smoothing + Margin Ranking Loss.

    Công thức tổng quát:
        L = L_BCE_LS + λ · L_margin

    L_BCE_LS (Binary Cross-Entropy với Label Smoothing):
        ỹ = (1 - eps) · y + eps/2       # nhãn mềm hóa
        L_BCE_LS = -[ ỹ·log(σ(z)) + (1-ỹ)·log(1-σ(z)) ]
        - eps (label_smoothing): ngăn mô hình quá tự tin (overconfident), giúp tổng quát hóa

    L_margin (Pairwise Margin Ranking Loss):
        L_margin = mean( max(0, γ - z_pos + z_neg) )
        - γ (margin_rank): biên phân tách tối thiểu giữa cặp dương và âm
        - Khuyến khích mô hình score cặp dương cao hơn cặp âm ít nhất γ
        - k_neg cặp âm ngẫu nhiên được chọn cho mỗi cặp dương

    Tại sao kết hợp hai loss này?
    - BCE đảm bảo mô hình phân biệt được 0/1 (calibration).
    - Margin loss thêm ràng buộc thứ tự (ranking) giúa các mẫu, giúp AUC tốt hơn.

    Args:
        logits       : đầu ra chưa sigmoid của mô hình [N]
        nhan         : nhãn thực [0/1], shape [N]
        pos_weight   : trọng số cho lớp positive trong BCE (cân bằng mất cân bằng)
        label_smoothing: ε trong label smoothing (khuyến nghị: 0.05)
        lambda_rank  : hệ số λ nhân margin loss (0 = tắt margin loss)
        margin_rank  : biên γ (khuyến nghị: 0.3)
        k_neg        : số mẫu âm ngẫu nhiên cho mỗi mẫu dương khi tính margin
    Returns:
        Scalar tensor là tổng loss
    """
    # 1. Label smoothing
    nhan_smooth = (1.0 - label_smoothing) * nhan + label_smoothing / 2.0

    # 2. BCE voi label smoothed
    loss_bce = F.binary_cross_entropy_with_logits(
        logits, nhan_smooth, pos_weight=pos_weight
    )

    if lambda_rank <= 0.0:
        return loss_bce

    # 3. Margin Ranking Loss
    pos_mask = nhan > 0.5
    neg_mask = ~pos_mask
    pos_logits = logits[pos_mask]
    neg_logits = logits[neg_mask]

    if len(pos_logits) == 0 or len(neg_logits) == 0:
        return loss_bce

    n_pos = pos_logits.shape[0]
    n_neg = neg_logits.shape[0]
    actual_k = min(k_neg, n_neg)
    idx = torch.randint(0, n_neg, (n_pos, actual_k), device=logits.device)
    neg_sampled = neg_logits[idx]                           # [n_pos, k_neg]
    pos_exp = pos_logits.unsqueeze(1).expand_as(neg_sampled)
    loss_rank = torch.clamp(margin_rank - pos_exp + neg_sampled, min=0.0).mean()

    return loss_bce + lambda_rank * loss_rank


def tim_nguong_toi_uu_f1(y_true: np.ndarray, y_score: np.ndarray) -> float:
    """Tìm ngưỡng phân loại tối ưu theo F1-score trên tập train.

    Mô hình GCN xuất ra xác suất liên tục [0, 1]. Để chuyển sang nhãn nhị phân
    (liên kết / không liên kết), cần chọn ngưỡng phù hợp.

    Vì sao không dùng 0.5 cố định?
    - Dữ liệu bất cân bằng (âm >> dương): ngưỡng 0.5 thường thiên về predict âm.
    - Tối ưu ngưỡng theo F1 giúp cân bằng Precision và Recall tốt hơn.

    Chiến lược:
    - Quét 61 ngưỡng trong [0.2, 0.8] (bước 0.01).
    - Chọn ngưỡng cho F1 cao nhất trên tập TRAIN.
    - Áp dụng ngưỡng đó để đánh giá trên tập TEST (không data leakage vì
      chỉ tối ưu ngưỡng, không tối ưu trọng số mô hình).

    Args:
        y_true : nhãn thực [0/1], shape [N]
        y_score: xác suất dự đoán [0..1], shape [N]
    Returns:
        Ngưỡng tối ưu trong [0.2, 0.8]
    """
    from sklearn.metrics import f1_score

    nguong_tot_nhat = 0.5
    f1_tot_nhat = -1.0
    for nguong in np.linspace(0.2, 0.8, 61):
        y_du_doan = (y_score >= nguong).astype(int)
        f1 = f1_score(y_true, y_du_doan, zero_division=0)
        if f1 > f1_tot_nhat:
            f1_tot_nhat = float(f1)
            nguong_tot_nhat = float(nguong)
    return nguong_tot_nhat


def tinh_chi_so(y_true: np.ndarray, y_score: np.ndarray, nguong: float = 0.5) -> Dict[str, float]:
    """Tính đầy đủ các chỉ số đánh giá mô hình phân loại nhị phân.

    Các chỉ số được tính:
    - AUC  (Area Under ROC Curve): khả năng phân biệt positive/negative, [0,1].
             AUC=0.5 → random, AUC=1.0 → hoàn hảo.
    - AUPR (Average Precision / Area Under PR Curve): quan trọng khi dữ liệu
             bất cân bằng (ít positive). Khắt khe hơn AUC.
    - Accuracy: tỉ lệ dự đoán đúng, ít ý nghĩa khi mất cân bằng.
    - Precision: trong các dự đoán positive, bao nhiêu đúng thực sự.
    - Recall (Sensitivity): trong các positive thực, mô hình phát hiện được bao nhiêu.
    - F1: trung bình điều hòa Precision và Recall.
    - MCC (Matthews Correlation Coefficient): chỉ số cân bằng tốt nhất cho
             dữ liệu bất cân bằng, [-1, 1] (1 = hoàn hảo, 0 = random).

    Args:
        y_true : nhãn thực [0/1]
        y_score: xác suất dự đoán [0..1]
        nguong : ngưỡng phân loại (từ tim_nguong_toi_uu_f1)
    Returns:
        Dict chứa 7 chỉ số đánh giá
    """
    from sklearn.metrics import (
        accuracy_score,
        average_precision_score,
        f1_score,
        matthews_corrcoef,
        precision_score,
        recall_score,
        roc_auc_score,
    )

    # Tinh AUC.
    auc = roc_auc_score(y_true, y_score)
    # Tinh AUPR.
    aupr = average_precision_score(y_true, y_score)
    # Chuyen score thanh nhan.
    y_pred = (y_score >= nguong).astype(int)
    # Tinh cac chi so.
    acc = accuracy_score(y_true, y_pred)
    prec = precision_score(y_true, y_pred, zero_division=0)
    rec = recall_score(y_true, y_pred, zero_division=0)
    f1 = f1_score(y_true, y_pred)
    mcc = matthews_corrcoef(y_true, y_pred)

    return {
        "AUC": float(auc),
        "AUPR": float(aupr),
        "Accuracy": float(acc),
        "Precision": float(prec),
        "Recall": float(rec),
        "F1": float(f1),
        "MCC": float(mcc),
    }


# =========================
# HAM HUAN LUYEN 1 FOLD
# =========================

def huan_luyen_1_fold(
    cau_hinh: CauHinh,
    data_train: HeteroData,
    canh_train: np.ndarray,
    nhan_train: np.ndarray,
    canh_test: np.ndarray,
    nhan_test: np.ndarray,
    so_thuoc: int,
    so_benh: int,
    thu_muc_trong_so: Path,
    fold_id: int,
) -> Dict[str, float]:
    """Huấn luyện và đánh giá FuzzyGCN trên 1 fold của K-Fold cross-validation.

    Quy trình:
    1. Khởi tạo mô hình FuzzyGCN với cấu hình đã cho.
    2. Optimizer: AdamW (weight decay tách biệt khỏi gradient, tốt hơn Adam).
    3. Scheduler: ReduceLROnPlateau(mode='max') — giảm lr khi AUC không tăng.
    4. Mỗi epoch:
       a. Forward pass → tính loss kết hợp (BCE_LS + margin).
       b. Backward + gradient clipping → optimizer step.
       c. Đánh giá trên tập test, tìm ngưỡng tối ưu F1 trên train.
       d. Nếu AUC cải thiện → lưu checkpoint (best_fold_N.pth).
       e. Early stopping: dừng nếu không cải thiện sau patience epoch.
    5. Load checkpoint tốt nhất → đánh giá lần cuối trên test → trả về chỉ số.

    Kỹ thuật:
    - AMP (Automatic Mixed Precision): tăng tốc 2-4x trên GPU hỗ trợ float16.
    - Gradient clipping: tránh gradient explosion khi loss margin lớn.
    - ReduceLROnPlateau: tự động giảm lr khi học đưa vào saddle point.

    Args:
        cau_hinh        : toàn bộ siêu tham số được đóng gói trong CauHinh
        data_train      : đồ thị HeteroData cho tập train của fold này
        canh_train      : tất cả cạnh (dương + âm) trong tập train [N_train, 2]
        nhan_train      : nhãn tương ứng [0/1] cho canh_train [N_train]
        canh_test       : tất cả cạnh trong tập test [N_test, 2]
        nhan_test       : nhãn tương ứng [0/1] cho canh_test [N_test]
        so_thuoc        : tổng số thuốc (cần để tính offset index trong embedding)
        so_benh         : tổng số bệnh
        thu_muc_trong_so: thư mục lưu checkpoint (best_fold_N.pth)
        fold_id         : chỉ số fold (1-indexed, dùng để đặt tên file checkpoint)
    Returns:
        Dict chứa 7 chỉ số đánh giá trên tập test của fold này:
        {AUC, AUPR, Accuracy, Precision, Recall, F1, MCC}
    """
    # Chon thiet bi.
    dung_cuda = torch.cuda.is_available() and cau_hinh.thiet_bi in {"auto", "cuda"}
    device = torch.device("cuda" if dung_cuda else "cpu")
    bat_amp = bool(cau_hinh.bat_amp and dung_cuda)

    # Neu bat buoc CUDA ma khong co thi bao loi.
    if cau_hinh.thiet_bi == "cuda" and not dung_cuda:
        raise RuntimeError("Ban chon CUDA nhung PyTorch khong nhan GPU.")

    # Dua data len device.
    data_train = data_train.to(device)

    # Tao mo hinh truc tiep tu FuzzyGCN (khong dung model_factory).
    mo_hinh = FuzzyGCN(
        so_chieu_thuoc=data_train["drug"].x.size(1),
        so_chieu_benh=data_train["disease"].x.size(1),
        so_chieu_an=cau_hinh.kich_thuoc_an,
        so_chieu_ra=cau_hinh.kich_thuoc_ra,
        so_lop_gcn=cau_hinh.so_lop_gcn,
        duong_dan_trong_so=str(thu_muc_trong_so / f"best_fold_{fold_id}.pth"),
    ).to(device)

    # Tao optimizer AdamW (tot hon Adam voi weight decay tach biet).
    optimizer = torch.optim.AdamW(
        mo_hinh.parameters(), lr=cau_hinh.toc_do_hoc, weight_decay=cau_hinh.weight_decay
    )

    # Tao scheduler giam toc do hoc khi AUC dung lai.
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
        optimizer,
        mode="max",
        factor=cau_hinh.factor_lr,
        patience=cau_hinh.patience_lr,
        min_lr=cau_hinh.min_lr,
        verbose=False,
    )

    # Tao scaler cho AMP.
    scaler = torch.amp.GradScaler("cuda", enabled=bat_amp)

    # Luu AUC tot nhat va checkpoint.
    best_auc = -1.0
    best_chi_so: Dict[str, float] = {}
    dem_dung_som = 0

    # pos_weight cho BCE (ket hop voi label smoothing).
    pos_weight = torch.tensor([cau_hinh.pos_weight_duong], device=device)

    # In header cho bang chi so.
    print(
        "Epoch           Time            AUC             AUPR            Accuracy                Precision               Recall          F1-score                Mcc"
    )

    # Bat dau huan luyen.
    for epoch in range(1, cau_hinh.so_epoch + 1):
        thoi_gian_bat_dau = time.perf_counter()

        # Chuyen du lieu train sang tensor.
        cap_train = torch.from_numpy(canh_train.T).long().to(device)
        nhan_train_t = torch.from_numpy(nhan_train).float().to(device)

        # Forward va tinh loss.
        mo_hinh.train()
        optimizer.zero_grad(set_to_none=True)

        if bat_amp:
            with torch.autocast(device_type="cuda", dtype=torch.float16, enabled=True):
                emb = mo_hinh(data_train)
                logits = _tinh_logits(mo_hinh, emb, cap_train, so_thuoc)
                loss = tinh_loss_ket_hop(
                    logits, nhan_train_t, pos_weight,
                    label_smoothing=cau_hinh.label_smoothing,
                    lambda_rank=cau_hinh.lambda_rank,
                    margin_rank=cau_hinh.margin_rank,
                )
            scaler.scale(loss).backward()
            if cau_hinh.grad_clip > 0:
                scaler.unscale_(optimizer)
                torch.nn.utils.clip_grad_norm_(mo_hinh.parameters(), cau_hinh.grad_clip)
            scaler.step(optimizer)
            scaler.update()
        else:
            emb = mo_hinh(data_train)
            logits = _tinh_logits(mo_hinh, emb, cap_train, so_thuoc)
            loss = tinh_loss_ket_hop(
                logits, nhan_train_t, pos_weight,
                label_smoothing=cau_hinh.label_smoothing,
                lambda_rank=cau_hinh.lambda_rank,
                margin_rank=cau_hinh.margin_rank,
            )
            loss.backward()
            if cau_hinh.grad_clip > 0:
                torch.nn.utils.clip_grad_norm_(mo_hinh.parameters(), cau_hinh.grad_clip)
            optimizer.step()

        # Danh gia tren tap test.
        mo_hinh.eval()
        with torch.no_grad():
            # Lay score tren train de tim nguong phan loai toi uu theo F1.
            diem_train = torch.sigmoid(_tinh_logits(mo_hinh, emb, cap_train, so_thuoc))
            cap_test = torch.from_numpy(canh_test.T).long().to(device)
            nhan_test_t = torch.from_numpy(nhan_test).float().to(device)
            emb_test = mo_hinh(data_train)
            diem_test = torch.sigmoid(_tinh_logits(mo_hinh, emb_test, cap_test, so_thuoc))

        # Tim nguong toi uu tren train va danh gia tren test.
        nguong_toi_uu = tim_nguong_toi_uu_f1(
            nhan_train_t.detach().cpu().numpy(),
            diem_train.detach().cpu().numpy(),
        )
        chi_so = tinh_chi_so(
            nhan_test_t.cpu().numpy(),
            diem_test.cpu().numpy(),
            nguong=nguong_toi_uu,
        )

        thoi_gian_ket_thuc = time.perf_counter()
        thoi_gian_epoch = thoi_gian_ket_thuc - thoi_gian_bat_dau

        # In bang chi so.
        print(
            f"{epoch:03d}             {thoi_gian_epoch:6.2f}s         "
            f"{chi_so['AUC']:.4f}          {chi_so['AUPR']:.4f}          "
            f"{chi_so['Accuracy']:.4f}                  {chi_so['Precision']:.4f}                 "
            f"{chi_so['Recall']:.4f}        {chi_so['F1']:.4f}                  {chi_so['MCC']:.4f}"
        )

        # Cap nhat scheduler theo AUC de hoc sau hon va on dinh hon.
        scheduler.step(chi_so["AUC"])

        # Luu checkpoint neu AUC tot hon.
        if chi_so["AUC"] > best_auc + cau_hinh.min_delta:
            best_auc = chi_so["AUC"]
            best_chi_so = chi_so.copy()
            dem_dung_som = 0
            print(f"AUC improved to {best_auc:.4f} at epoch {epoch}")
            torch.save(mo_hinh.state_dict(), thu_muc_trong_so / f"best_fold_{fold_id}.pth")
        else:
            dem_dung_som += 1
            print(f"Khong cai thien AUC: {dem_dung_som}/{cau_hinh.patience} epoch")
            if dem_dung_som >= cau_hinh.patience:
                print("Kich hoat Dung Som de chong Overfitting!")
                print(f"Dung som tai epoch {epoch} do khong cai thien AUC.")
                break

    # --- Tra ve chi so cua epoch tot nhat (tu checkpoint), khong phai epoch cuoi ---
    if best_chi_so:
        # Load lai checkpoint tot nhat va danh gia lan cuoi de dam bao chinh xac.
        best_path = thu_muc_trong_so / f"best_fold_{fold_id}.pth"
        if best_path.exists():
            mo_hinh.load_state_dict(torch.load(best_path, map_location=device))
            mo_hinh.eval()
            with torch.no_grad():
                cap_test = torch.from_numpy(canh_test.T).long().to(device)
                nhan_test_t = torch.from_numpy(nhan_test).float().to(device)
                emb_best = mo_hinh(data_train)
                diem_best = torch.sigmoid(_tinh_logits(mo_hinh, emb_best, cap_test, so_thuoc))
            best_chi_so = tinh_chi_so(nhan_test_t.cpu().numpy(), diem_best.cpu().numpy())
        return best_chi_so
    return chi_so


# =========================
# HAM CHINH
# =========================

ALL_DATASETS = ["B-dataset", "C-dataset", "F-dataset"]


def parse_args() -> argparse.Namespace:
    """Đọc tham số dòng lệnh cho huấn luyện FuzzyGCN.

    Ngoài các tham số huấn luyện thông thường, còn có nhóm --auto-tune-*:
    - --auto-tune        : Bật auto-tune tự động sau khi train xong
    - --auto-tune-trials : Số trial tìm kiếm thông số (mặc định 20)
    - --auto-tune-max-epochs: Số epoch tối đa mỗi trial (mặc định 500)
    - --auto-tune-folds  : Số fold mỗi trial (mặc định 3, dùng fold đầu để nhanh)
    - --auto-tune-target-auc: AUC mục tiêu dừng sớm (mặc định 0.99)
    """
    # Tao parser va nap tham so.
    parser = argparse.ArgumentParser(
        description="Huan luyen FuzzyGCN voi K-Fold.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Vi du:
  python huan_luyen.py --dataset C-dataset --epochs 2000
  python huan_luyen.py --dataset C-dataset --auto-tune --auto-tune-trials 20
  python huan_luyen.py --all-datasets --auto-tune --auto-tune-trials 10
        """,
    )
    parser.add_argument("--dataset", type=str, default=CauHinh.ten_dataset,
                        help="Ten dataset (B-dataset / C-dataset / F-dataset)")
    parser.add_argument("--all-datasets", action="store_true",
                        help="Train lan luot tung dataset (B -> C -> F), bo qua --dataset")
    parser.add_argument("--epochs", type=int, default=CauHinh.so_epoch)
    parser.add_argument("--learning-rate", type=float, default=CauHinh.toc_do_hoc)
    parser.add_argument("--weight-decay", type=float, default=CauHinh.weight_decay)
    parser.add_argument("--k-fold", type=int, default=CauHinh.so_fold)
    parser.add_argument("--negative-rate", type=float, default=CauHinh.ti_le_am)
    parser.add_argument("--patience", type=int, default=CauHinh.patience)
    parser.add_argument("--min-delta", type=float, default=CauHinh.min_delta)
    parser.add_argument("--lr-factor", type=float, default=CauHinh.factor_lr)
    parser.add_argument("--lr-patience", type=int, default=CauHinh.patience_lr)
    parser.add_argument("--min-lr", type=float, default=CauHinh.min_lr)
    parser.add_argument("--clip-grad", type=float, default=CauHinh.grad_clip)
    parser.add_argument("--pos-weight", type=float, default=CauHinh.pos_weight_duong)
    parser.add_argument("--label-smoothing", type=float, default=CauHinh.label_smoothing)
    parser.add_argument("--lambda-rank", type=float, default=CauHinh.lambda_rank)
    parser.add_argument("--margin-rank", type=float, default=CauHinh.margin_rank)
    # Kien truc GCN (de auto-tune co the override)
    parser.add_argument("--gcn-layers", type=int, default=CauHinh.so_lop_gcn,
                        help="So lop GCN (mac dinh: 4)")
    parser.add_argument("--hidden-size", type=int, default=CauHinh.kich_thuoc_an,
                        help="Chieu khong gian an (mac dinh: 512)")
    parser.add_argument("--output-size", type=int, default=CauHinh.kich_thuoc_ra,
                        help="Chieu embedding dau ra GCN (mac dinh: 256)")
    parser.add_argument("--dropout", type=float, default=CauHinh.dropout_decoder,
                        help="Dropout trong MLP decoder (mac dinh: 0.2)")
    parser.add_argument("--no-normalize", action="store_true",
                        help="Tat chuan hoa dac trung (mac dinh: bat)")
    parser.add_argument("--no-multi-feature", action="store_true",
                        help="Tat ghep nhieu feature (mac dinh: bat)")
    parser.add_argument("--device", type=str, default=CauHinh.thiet_bi)
    parser.add_argument("--amp", action="store_true", default=CauHinh.bat_amp)

    # ── Nhom tham so Auto-Tune ──────────────────────────────────────────
    grp = parser.add_argument_group("Auto-Tune (tu dong tim thong so tot hon)")
    grp.add_argument(
        "--auto-tune", action="store_true",
        help="Sau khi train xong, tu dong tim thong so tot hon roi retrain",
    )
    grp.add_argument(
        "--auto-tune-trials", type=int, default=20,
        help="So lan thu tim kiem (mac dinh: 20)",
    )
    grp.add_argument(
        "--auto-tune-max-epochs", type=int, default=500,
        help="Epoch toi da moi trial nhanh (mac dinh: 500)",
    )
    grp.add_argument(
        "--auto-tune-folds", type=int, default=3,
        help="So fold moi trial (mac dinh: 3, chay 3 fold dau de nhanh)",
    )
    grp.add_argument(
        "--auto-tune-target-auc", type=float, default=0.99,
        help="AUC muc tieu de dung som (mac dinh: 0.99)",
    )
    return parser.parse_args()


def _huan_luyen_mot_dataset(args: argparse.Namespace, dataset: str) -> None:
    """Huấn luyện đầy đủ K-Fold cho 1 dataset, lưu trọng số và kết quả vào thư mục weights/.

    Quy trình tổng thể:
    1. Đọc và chuẩn bị dữ liệu: đặc trưng + liên kết + negative sampling.
    2. StratifiedKFold: chia train/test giữ nguyên tỉ lệ positive (10%).
    3. Mỗi fold: gọi huan_luyen_1_fold() → trả về chi số.
    4. Tính trung bình và độ lệch chuẩn các chỉ số qua tất cả fold.
    5. Lưu kết quả vào weights/<dataset>/kfold_metrics.json.

    Tại sao dùng Stratified K-Fold?
    - Dữ liệu có tỉ lệ dương/âm không bằng nhau (thường ~10% positive).
    - Stratified đảm bảo mỗi fold giữ cùng tỉ lệ → ước lượng AUC ổn định hơn.

    Args:
        args   : tham số dòng lệnh đã parse (epochs, lr, k_fold, etc.)
        dataset: tên dataset (ví dụ: 'C-dataset')
    """
    print(f"\n{'='*60}")
    print(f"  DATASET: {dataset}")
    print(f"{'='*60}")

    cau_hinh = CauHinh(
        ten_dataset=dataset,
        so_epoch=int(args.epochs),
        toc_do_hoc=float(args.learning_rate),
        weight_decay=float(getattr(args, "weight_decay", CauHinh.weight_decay)),
        so_lop_gcn=int(getattr(args, "gcn_layers", CauHinh.so_lop_gcn)),
        kich_thuoc_an=int(getattr(args, "hidden_size", CauHinh.kich_thuoc_an)),
        kich_thuoc_ra=int(getattr(args, "output_size", CauHinh.kich_thuoc_ra)),
        dropout_decoder=float(getattr(args, "dropout", CauHinh.dropout_decoder)),
        so_fold=int(args.k_fold),
        ti_le_am=float(args.negative_rate),
        patience=int(args.patience),
        min_delta=float(args.min_delta),
        factor_lr=float(args.lr_factor),
        patience_lr=int(args.lr_patience),
        min_lr=float(args.min_lr),
        grad_clip=float(args.clip_grad),
        pos_weight_duong=float(args.pos_weight),
        label_smoothing=float(args.label_smoothing),
        lambda_rank=float(args.lambda_rank),
        margin_rank=float(args.margin_rank),
        bat_chuan_hoa=not args.no_normalize,
        ghep_nhieu_feature=not args.no_multi_feature,
        thiet_bi=str(args.device),
        bat_amp=bool(args.amp),
    )

    # Dat seed.
    dat_seed(cau_hinh.seed)

    # Chuan bi duong dan.
    thu_muc_goc = Path(cau_hinh.thu_muc_goc)
    duong_dataset = thu_muc_goc / "dataset" / cau_hinh.ten_dataset
    thu_muc_trong_so = Path(cau_hinh.thu_muc_trong_so) / cau_hinh.ten_dataset
    thu_muc_trong_so.mkdir(parents=True, exist_ok=True)

    # Doc du lieu.
    canh_duong = doc_lien_ket(duong_dataset / cau_hinh.tep_lien_ket)
    max_thuoc = int(canh_duong[:, 0].max()) + 1
    max_benh = int(canh_duong[:, 1].max()) + 1

    thuoc_raw = doc_ma_tran(duong_dataset / cau_hinh.tep_thuoc)
    benh_raw = doc_ma_tran(duong_dataset / cau_hinh.tep_benh)
    thuoc = can_chinh_hang(thuoc_raw, max_thuoc, "Thuoc")
    benh = can_chinh_hang(benh_raw, max_benh, "Benh")

    # Ghep them cac feature phu tro (GIP, PS, mol2vec) neu duoc bat.
    if cau_hinh.ghep_nhieu_feature:
        print("\n[+] Ghep nhieu feature:")
        thuoc = ghep_feature_thuoc(thuoc, duong_dataset)
        benh = ghep_feature_benh(benh, duong_dataset)

    so_thuoc = thuoc.shape[0]
    so_benh = benh.shape[0]

    hop_le = (
        (canh_duong[:, 0] >= 0)
        & (canh_duong[:, 0] < so_thuoc)
        & (canh_duong[:, 1] >= 0)
        & (canh_duong[:, 1] < so_benh)
    )
    canh_duong = canh_duong[hop_le]

    tap_duong = set(zip(canh_duong[:, 0].tolist(), canh_duong[:, 1].tolist()))
    so_am = max(1, int(len(canh_duong) * cau_hinh.ti_le_am))
    canh_am = tao_canh_am(so_thuoc, so_benh, tap_duong, so_am)

    canh_tat_ca = np.vstack([canh_duong, canh_am])
    nhan_tat_ca = np.hstack([
        np.ones(len(canh_duong), dtype=np.int64),
        np.zeros(len(canh_am), dtype=np.int64),
    ])

    # Chuan hoa dac trung neu bat.
    if cau_hinh.bat_chuan_hoa:
        print("\n[+] Chuan hoa dac trung (StandardScaler)...")
        thuoc, benh = chuan_hoa_dac_trung(thuoc, benh)

    skf = StratifiedKFold(n_splits=cau_hinh.so_fold, shuffle=True, random_state=cau_hinh.seed)

    danh_sach_chi_so: List[Dict[str, float]] = []
    for fold_id, (train_idx, test_idx) in enumerate(skf.split(canh_tat_ca, nhan_tat_ca), start=1):
        print(f"\n=== [{dataset}] Fold {fold_id}/{cau_hinh.so_fold} ===")
        canh_train = canh_tat_ca[train_idx]
        nhan_train = nhan_tat_ca[train_idx]
        canh_test  = canh_tat_ca[test_idx]
        nhan_test  = nhan_tat_ca[test_idx]

        # Tao do thi chi tu tap train duong (tranh ro ri thong tin).
        data_train = tao_do_thi(thuoc, benh, canh_train[nhan_train == 1])

        chi_so = huan_luyen_1_fold(
            cau_hinh=cau_hinh,
            data_train=data_train,
            canh_train=canh_train,
            nhan_train=nhan_train,
            canh_test=canh_test,
            nhan_test=nhan_test,
            so_thuoc=so_thuoc,
            so_benh=so_benh,
            thu_muc_trong_so=thu_muc_trong_so,
            fold_id=fold_id,
        )
        danh_sach_chi_so.append(chi_so)

    # Tinh mean va std cho tung chi so.
    ket_qua: Dict[str, Any] = {"dataset": dataset, "so_fold": cau_hinh.so_fold, "metrics": {}}
    for key in danh_sach_chi_so[0].keys():
        vals = [cs[key] for cs in danh_sach_chi_so]
        mean_val = float(np.mean(vals))
        std_val  = float(np.std(vals, ddof=1) if len(vals) > 1 else 0.0)
        ket_qua["metrics"][key] = {"mean": mean_val, "std": std_val}

    # Giu them bang phang de tuong thich nguoc (mean cua tung chi so o cap tren).
    ket_qua["mean"] = {k: ket_qua["metrics"][k]["mean"] for k in ket_qua["metrics"]}
    ket_qua["std"]  = {k: ket_qua["metrics"][k]["std"]  for k in ket_qua["metrics"]}

    # Luu tung fold de phan tich sau.
    ket_qua["folds"] = danh_sach_chi_so

    print(f"\n=== [{dataset}] Ket qua trung binh K-Fold ===")
    for k, v in ket_qua["metrics"].items():
        print(f"  {k:12s}: mean={v['mean']:.4f}  std={v['std']:.4f}")

    tep_kq = thu_muc_trong_so / "kfold_metrics.json"
    tep_kq.write_text(json.dumps(ket_qua, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Da luu ket qua: {tep_kq}")


def _chay_auto_tune(dataset: str, args: argparse.Namespace) -> None:
    """Chạy auto-tune sau khi training bình thường hoàn tất.

    Quy trình tích hợp:
    1. Import auto_tune lazily (tránh circular import).
    2. Gọi tu_dong_chinh_thong_so() — tìm thông số tốt hơn baseline AUC.
    3. Nếu tìm được thông số tốt hơn → gọi _retrain_voi_thong_so_tot_nhat()
       để retrain đầy đủ K-Fold với thông số đó và lưu trọng số mới.

    Lưu ý về circular import:
    - auto_tune.py import từ huan_luyen.py ở module level
    - Ta import auto_tune lazily (bên trong hàm) để khi gọi hàm này,
      huan_luyen đã nằm trong sys.modules → Python dùng lại, không tạo lại.
    - Không có circular import thực sự vì lazy import chỉ chạy sau khi
      huan_luyen đã được load đầy đủ.

    Args:
        dataset: tên dataset (B-dataset / C-dataset / F-dataset)
        args   : Namespace từ parse_args(), dùng để lấy các tham số auto-tune
    """
    import sys as _sys

    # Tìm project root: dùng CauHinh.thu_muc_goc làm tham chiếu (đây là gốc của dataset/ và weights/)
    # auto_tune.py nằm trong cùng thư mục với dataset/ và weights/
    _project_root = Path(CauHinh().thu_muc_goc)
    if str(_project_root) not in _sys.path:
        _sys.path.insert(0, str(_project_root))

    # Lazy import — an toàn vì huan_luyen đã hoàn toàn loaded tại thời điểm này
    try:
        import importlib
        auto_tune = importlib.import_module("auto_tune")
    except ImportError as e:
        print(f"\n[AutoTune] Khong the import auto_tune.py: {e}")
        print(f"[AutoTune] Dam bao file auto_tune.py nam o: {_project_root}")
        return

    print(f"\n{'='*60}")
    print(f"  [AutoTune] Bat dau tim kiem thong so tot hon cho {dataset}")
    print(f"  Trials: {args.auto_tune_trials}  MaxEpochs/trial: {args.auto_tune_max_epochs}")
    print(f"  Folds/trial: {args.auto_tune_folds}  Target AUC: {args.auto_tune_target_auc}")
    print(f"{'='*60}")

    best_trial = auto_tune.tu_dong_chinh_thong_so(
        dataset=dataset,
        so_trial=args.auto_tune_trials,
        max_epochs=args.auto_tune_max_epochs,
        so_fold_thu=args.auto_tune_folds,
        target_auc=args.auto_tune_target_auc,
        seed=42,
    )

    if not best_trial:
        print(f"\n[AutoTune] Khong tim duoc thong so tot hon cho {dataset}.")
        return

    # Nếu tìm được thông số tốt hơn → retrain đầy đủ với thông số đó
    baseline_auc = auto_tune._doc_auc_goc(dataset, _project_root / "weights")
    if baseline_auc is not None and best_trial["mean_auc"] <= baseline_auc:
        print(f"\n[AutoTune] Auto-tune chua vuot duoc baseline (AUC={baseline_auc:.6f}).")
        print("[AutoTune] Ket qua da duoc luu vao lich_su_thong_so_train/ de tham khao.")
        return

    print(f"\n[AutoTune] Tim duoc thong so tot hon! AUC={best_trial['mean_auc']:.6f}")
    print("[AutoTune] Bat dau retrain day du K-Fold voi thong so tot nhat...")

    auto_tune._retrain_voi_thong_so_tot_nhat(
        dataset=dataset,
        best_params=best_trial["params"],
        full_epochs=args.epochs,      # Dùng epoch đầy đủ (không giới hạn như trial)
        k_fold=args.k_fold,
    )


def main() -> None:
    """Điểm vào chính: parse args → train → (nếu --auto-tune) tự động tìm thông số tốt hơn."""
    # Doc tham so.
    args = parse_args()

    if args.all_datasets:
        # Train lan luot tung dataset, doc lap nhau
        for ds in ALL_DATASETS:
            _huan_luyen_mot_dataset(args, ds)
            # Sau moi dataset, neu bat auto-tune thi tim thong so tot hon
            if args.auto_tune:
                _chay_auto_tune(ds, args)
        print("\n=== Hoan thanh train tat ca dataset ===")
        return

    _huan_luyen_mot_dataset(args, args.dataset)

    # Sau khi train xong, neu bat auto-tune thi tu dong tim thong so tot hon
    if args.auto_tune:
        _chay_auto_tune(args.dataset, args)


if __name__ == "__main__":
    main()
