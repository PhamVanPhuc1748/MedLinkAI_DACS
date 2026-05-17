"""
auto_tune.py — Tự động điều chỉnh thông số huấn luyện và lưu lịch sử.
=======================================================================

CÁCH HOẠT ĐỘNG:
---------------
1. Đọc kết quả AUC gốc từ weights/<dataset>/kfold_metrics.json (nếu có).
   Nếu chưa có, chạy lượt gốc trước để có baseline.

2. Thực hiện tối ưu hóa siêu tham số theo chiến lược:
   - Mỗi vòng (trial): chọn ngẫu nhiên 1 bộ thông số từ không gian tìm kiếm
     đã định nghĩa (random search + local perturbation).
   - Chạy hàm `_huan_luyen_mot_dataset` với bộ thông số đó.
   - So sánh AUC trung bình K-Fold với best hiện tại.
   - Nếu tốt hơn: lưu thông số vào lich_su_thong_so_train/<dataset>_YYYYMMDD_HHMMSS.txt
     và cập nhật best.

3. Dừng khi đạt ngưỡng AUC mục tiêu hoặc hết số trial tối đa.

CÁCH DÙNG:
----------
  python auto_tune.py --dataset C-dataset --trials 20 --target-auc 0.95
  python auto_tune.py --dataset B-dataset --trials 30 --max-epochs 500
  python auto_tune.py --all-datasets --trials 15

CHIẾN LƯỢC TÌM KIẾM (Random Search + Perturbation):
-----------------------------------------------------
- Dùng random search thuần túy (không cần thư viện ngoài như Optuna).
- Sau mỗi trial tìm thấy kết quả tốt hơn, vòng kế tiếp sẽ perturbation
  (nhiễu nhỏ) xung quanh bộ tốt nhất (local search) để tinh chỉnh thêm.
- Xen kẽ giữa random toàn cục và local search để tránh bẫy cục bộ.
"""
from __future__ import annotations

import argparse
import copy
import json
import math
import random
import sys
import time
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, List, Optional, Tuple

# ── Thêm src/backend vào sys.path để import module AI ──────────────────────
_PROJECT_ROOT = Path(__file__).resolve().parent
_BACKEND = _PROJECT_ROOT / "src" / "backend"
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

# Import module huấn luyện
from app.ai.huan_luyen import (
    CauHinh,
    _huan_luyen_mot_dataset,
    can_chinh_hang,
    chuan_hoa_dac_trung,
    dat_seed,
    doc_lien_ket,
    doc_ma_tran,
    ghep_feature_benh,
    ghep_feature_thuoc,
    huan_luyen_1_fold,
    tao_canh_am,
    tao_do_thi,
)

import numpy as np
from sklearn.model_selection import StratifiedKFold

# Import TrainLogger — log mọi trial vào train_logs/
try:
    from train_logger import TrainLogger
    _LOGGER_AVAILABLE = True
except ImportError:
    _LOGGER_AVAILABLE = False

# ── Thư mục lưu lịch sử ────────────────────────────────────────────────────
LICH_SU_DIR = _PROJECT_ROOT / "lich_su_thong_so_train"
LICH_SU_DIR.mkdir(parents=True, exist_ok=True)

# ============================================================================
# KHÔNG GIAN THÔNG SỐ TÌM KIẾM
# ============================================================================
# Mỗi key là tên thông số trong CauHinh.
# "type": "float_log" → lấy mẫu trong không gian log (phù hợp lr, wd).
# "type": "float"     → lấy mẫu đều trong [low, high].
# "type": "int"       → lấy mẫu nguyên trong [low, high].
# "type": "choice"    → chọn 1 trong danh sách values.

KHONG_GIAN_TIM_KIEM: Dict[str, Dict[str, Any]] = {
    "toc_do_hoc": {
        "type": "float_log",
        "low": 1e-4,
        "high": 1e-2,
    },
    "weight_decay": {
        "type": "float_log",
        "low": 1e-5,
        "high": 1e-3,
    },
    "so_lop_gcn": {
        "type": "int",
        "low": 2,
        "high": 5,
    },
    "kich_thuoc_an": {
        "type": "choice",
        "values": [128, 192, 256, 384, 512],
    },
    "kich_thuoc_ra": {
        "type": "choice",
        "values": [64, 96, 128, 192, 256],
    },
    "ti_le_am": {
        "type": "float",
        "low": 0.8,
        "high": 2.0,
    },
    "dropout_decoder": {
        "type": "float",
        "low": 0.1,
        "high": 0.5,
    },
    "label_smoothing": {
        "type": "float",
        "low": 0.0,
        "high": 0.15,
    },
    "lambda_rank": {
        "type": "float",
        "low": 0.0,
        "high": 0.5,
    },
    "margin_rank": {
        "type": "float",
        "low": 0.1,
        "high": 0.6,
    },
    "factor_lr": {
        "type": "float",
        "low": 0.3,
        "high": 0.8,
    },
    "patience_lr": {
        "type": "int",
        "low": 5,
        "high": 25,
    },
    "grad_clip": {
        "type": "float",
        "low": 0.5,
        "high": 5.0,
    },
}

# Thông số cố định (không tune để tiết kiệm thời gian):
# - so_epoch: giới hạn bởi --max-epochs
# - so_fold: giữ nguyên (ảnh hưởng lớn đến thời gian)
# - bat_chuan_hoa, ghep_nhieu_feature: luôn True


def _lay_mau_ngau_nhien(khong_gian: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """Lấy ngẫu nhiên 1 bộ thông số từ không gian tìm kiếm.

    Với mỗi siêu tham số:
    - float_log: mẫu trong log-uniform [low, high] để phân phối đều hơn
    - float: mẫu đều trong [low, high]
    - int: nguyên ngẫu nhiên trong [low, high]
    - choice: chọn 1 phần tử ngẫu nhiên từ values
    """
    mau: Dict[str, Any] = {}
    for ten, cfg in khong_gian.items():
        loai = cfg["type"]
        if loai == "float_log":
            # Log-uniform: log(x) ~ Uniform(log(low), log(high))
            log_low = math.log(cfg["low"])
            log_high = math.log(cfg["high"])
            mau[ten] = math.exp(random.uniform(log_low, log_high))
        elif loai == "float":
            mau[ten] = random.uniform(cfg["low"], cfg["high"])
        elif loai == "int":
            mau[ten] = random.randint(cfg["low"], cfg["high"])
        elif loai == "choice":
            mau[ten] = random.choice(cfg["values"])
    return mau


def _perturbation(
    best_params: Dict[str, Any],
    khong_gian: Dict[str, Dict[str, Any]],
    cuong_do: float = 0.2,
) -> Dict[str, Any]:
    """Tạo bộ thông số mới bằng cách nhiễu nhỏ xung quanh best_params.

    Chiến lược:
    - float/float_log: nhân với e^(N(0, cuong_do)) để perturbation tương đối
    - int: ± random trong [0, max(1, range * cuong_do)]
    - choice: 50% giữ nguyên, 50% chọn ngẫu nhiên

    Args:
        best_params: bộ thông số tốt nhất hiện tại
        khong_gian : không gian tìm kiếm (để biết bounds)
        cuong_do   : mức độ nhiễu (0.2 = ±20% tương đối)
    Returns:
        Bộ thông số mới đã bị giới hạn trong không gian hợp lệ
    """
    mau = {}
    for ten, cfg in khong_gian.items():
        loai = cfg["type"]
        gia_tri_cu = best_params.get(ten)

        if loai in ("float", "float_log") and gia_tri_cu is not None:
            # Perturbation theo log-normal
            noise = math.exp(random.gauss(0, cuong_do))
            new_val = float(gia_tri_cu) * noise
            # Clip vào [low, high]
            mau[ten] = max(cfg["low"], min(cfg["high"], new_val))

        elif loai == "int" and gia_tri_cu is not None:
            pham_vi = cfg["high"] - cfg["low"]
            delta = random.randint(0, max(1, round(pham_vi * cuong_do)))
            delta = delta * random.choice([-1, 1])
            new_val = int(gia_tri_cu) + delta
            mau[ten] = max(cfg["low"], min(cfg["high"], new_val))

        elif loai == "choice":
            if random.random() < 0.5:
                mau[ten] = gia_tri_cu  # Giữ nguyên
            else:
                mau[ten] = random.choice(cfg["values"])
        else:
            mau[ten] = _lay_mau_ngau_nhien({ten: cfg})[ten]

    return mau


def _tao_cau_hinh(
    base_cfg: CauHinh,
    params: Dict[str, Any],
    max_epochs: int,
) -> CauHinh:
    """Tạo CauHinh mới từ base + params override.

    Args:
        base_cfg   : cấu hình gốc (giữ nguyên dataset, seed, etc.)
        params     : dict thông số cần override
        max_epochs : giới hạn epoch tối đa để trial chạy nhanh
    Returns:
        CauHinh mới với các thông số đã được cập nhật
    """
    cfg = copy.deepcopy(base_cfg)
    # Áp params
    for key, val in params.items():
        if hasattr(cfg, key):
            setattr(cfg, key, val)
    # Giới hạn epoch để tăng tốc trial
    cfg.so_epoch = min(cfg.so_epoch, max_epochs)
    # patience tương ứng để early stopping còn hiệu quả
    cfg.patience = min(cfg.patience, max(30, max_epochs // 5))
    cfg.patience_lr = min(cfg.patience_lr, max(5, cfg.patience // 5))
    return cfg


def _chay_kfold_nhanh(
    cfg: CauHinh,
    so_fold_thu: int,
) -> Tuple[float, float, List[Dict[str, float]]]:
    """Chạy K-Fold rút gọn (chỉ dùng so_fold_thu fold đầu) để ước lượng nhanh.

    Trả về (mean_auc, std_auc, danh_sach_chi_so).
    """
    # Chuẩn bị dữ liệu (copy logic từ _huan_luyen_mot_dataset)
    thu_muc_goc = Path(cfg.thu_muc_goc)
    duong_dataset = thu_muc_goc / "dataset" / cfg.ten_dataset
    thu_muc_trong_so = Path(cfg.thu_muc_trong_so) / cfg.ten_dataset / "_autotune_tmp"
    thu_muc_trong_so.mkdir(parents=True, exist_ok=True)

    canh_duong = doc_lien_ket(duong_dataset / cfg.tep_lien_ket)
    max_thuoc = int(canh_duong[:, 0].max()) + 1
    max_benh = int(canh_duong[:, 1].max()) + 1

    thuoc_raw = doc_ma_tran(duong_dataset / cfg.tep_thuoc)
    benh_raw = doc_ma_tran(duong_dataset / cfg.tep_benh)
    thuoc = can_chinh_hang(thuoc_raw, max_thuoc, "Thuoc")
    benh = can_chinh_hang(benh_raw, max_benh, "Benh")

    if cfg.ghep_nhieu_feature:
        thuoc = ghep_feature_thuoc(thuoc, duong_dataset)
        benh = ghep_feature_benh(benh, duong_dataset)

    so_thuoc = thuoc.shape[0]
    so_benh = benh.shape[0]

    hop_le = (
        (canh_duong[:, 0] >= 0) & (canh_duong[:, 0] < so_thuoc) &
        (canh_duong[:, 1] >= 0) & (canh_duong[:, 1] < so_benh)
    )
    canh_duong = canh_duong[hop_le]
    tap_duong = set(zip(canh_duong[:, 0].tolist(), canh_duong[:, 1].tolist()))
    so_am = max(1, int(len(canh_duong) * cfg.ti_le_am))
    canh_am = tao_canh_am(so_thuoc, so_benh, tap_duong, so_am)

    canh_tat_ca = np.vstack([canh_duong, canh_am])
    nhan_tat_ca = np.hstack([
        np.ones(len(canh_duong), dtype=np.int64),
        np.zeros(len(canh_am), dtype=np.int64),
    ])

    if cfg.bat_chuan_hoa:
        thuoc, benh = chuan_hoa_dac_trung(thuoc, benh)

    # Chỉ chạy so_fold_thu fold đầu để nhanh
    so_fold_thuc = min(so_fold_thu, cfg.so_fold)
    skf = StratifiedKFold(n_splits=cfg.so_fold, shuffle=True, random_state=cfg.seed)
    folds = list(skf.split(canh_tat_ca, nhan_tat_ca))[:so_fold_thuc]

    danh_sach_chi_so: List[Dict[str, float]] = []
    for fold_id, (train_idx, test_idx) in enumerate(folds, start=1):
        canh_train = canh_tat_ca[train_idx]
        nhan_train = nhan_tat_ca[train_idx]
        canh_test  = canh_tat_ca[test_idx]
        nhan_test  = nhan_tat_ca[test_idx]
        data_train = tao_do_thi(thuoc, benh, canh_train[nhan_train == 1])

        chi_so = huan_luyen_1_fold(
            cau_hinh=cfg,
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
        print(f"  Fold {fold_id}/{so_fold_thuc} — AUC={chi_so['AUC']:.4f}  AUPR={chi_so['AUPR']:.4f}")

    auc_list = [cs["AUC"] for cs in danh_sach_chi_so]
    mean_auc = float(np.mean(auc_list))
    std_auc  = float(np.std(auc_list, ddof=1) if len(auc_list) > 1 else 0.0)
    return mean_auc, std_auc, danh_sach_chi_so


def _doc_auc_goc(dataset: str, weights_dir: Path) -> Optional[float]:
    """Đọc AUC gốc từ weights/<dataset>/kfold_metrics.json.

    Returns:
        AUC trung bình K-Fold gốc, hoặc None nếu chưa có file.
    """
    tep = weights_dir / dataset / "kfold_metrics.json"
    if not tep.exists():
        return None
    try:
        data = json.loads(tep.read_text(encoding="utf-8"))
        # Thử các key theo thứ tự ưu tiên
        for path in [
            ["metrics", "AUC", "mean"],
            ["mean", "AUC"],
        ]:
            obj = data
            try:
                for k in path:
                    obj = obj[k]
                return float(obj)
            except (KeyError, TypeError):
                continue
    except Exception as e:
        print(f"  [!] Không đọc được AUC gốc: {e}")
    return None


def _luu_lich_su(
    dataset: str,
    trial_id: int,
    params: Dict[str, Any],
    mean_auc: float,
    std_auc: float,
    chi_so_folds: List[Dict[str, float]],
    la_tot_nhat: bool,
    baseline_auc: Optional[float],
    thoi_gian_s: float,
) -> Path:
    """Lưu thông số và kết quả trial vào file lịch sử.

    Format file: text có thể đọc được bằng mắt, dễ so sánh.
    Trả về đường dẫn file đã lưu.
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    ten_file = f"{dataset}_trial{trial_id:03d}_{timestamp}.txt"
    if la_tot_nhat:
        ten_file = f"{dataset}_BEST_trial{trial_id:03d}_{timestamp}.txt"

    duong_dan = LICH_SU_DIR / ten_file

    # Tính mean các metrics khác
    mean_metrics: Dict[str, float] = {}
    if chi_so_folds:
        for key in chi_so_folds[0]:
            mean_metrics[key] = float(np.mean([cs[key] for cs in chi_so_folds]))

    lines = [
        "=" * 70,
        f"  AUTO-TUNE LỊCH SỬ THÔNG SỐ",
        "=" * 70,
        f"Dataset      : {dataset}",
        f"Trial        : #{trial_id}",
        f"Thời gian    : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"Thời lượng   : {thoi_gian_s:.1f}s",
        f"Tốt nhất?    : {'✅ CÓ' if la_tot_nhat else 'Không'}",
        "",
        "── KẾT QUẢ ─────────────────────────────────────────────────────",
        f"AUC (mean)   : {mean_auc:.6f}",
        f"AUC (std)    : {std_auc:.6f}",
    ]
    if baseline_auc is not None:
        cai_thien = mean_auc - baseline_auc
        ky_hieu = "+" if cai_thien >= 0 else ""
        lines.append(f"AUC gốc      : {baseline_auc:.6f}")
        lines.append(f"Cải thiện    : {ky_hieu}{cai_thien:.6f} ({ky_hieu}{cai_thien/baseline_auc*100:.2f}%)")
    for k, v in mean_metrics.items():
        if k != "AUC":
            lines.append(f"{k:12s}  : {v:.6f}")
    lines += [
        "",
        "── THÔNG SỐ ────────────────────────────────────────────────────",
    ]
    for k, v in params.items():
        if isinstance(v, float):
            lines.append(f"  {k:25s}: {v:.6g}")
        else:
            lines.append(f"  {k:25s}: {v}")
    lines += [
        "",
        "── CHI TIẾT TỪNG FOLD ───────────────────────────────────────────",
    ]
    for i, cs in enumerate(chi_so_folds, 1):
        lines.append(
            f"  Fold {i:2d}: AUC={cs['AUC']:.4f}  AUPR={cs.get('AUPR',0):.4f}"
            f"  F1={cs.get('F1',0):.4f}  MCC={cs.get('MCC',0):.4f}"
        )
    lines.append("=" * 70)

    duong_dan.write_text("\n".join(lines), encoding="utf-8")
    return duong_dan


def _luu_tong_ket(
    dataset: str,
    tat_ca_trials: List[Dict[str, Any]],
    best_trial: Dict[str, Any],
    baseline_auc: Optional[float],
) -> Path:
    """Lưu file tổng kết tất cả trials của 1 dataset."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    duong_dan = LICH_SU_DIR / f"{dataset}_tong_ket_{timestamp}.txt"

    lines = [
        "=" * 70,
        f"  TỔNG KẾT AUTO-TUNE — {dataset}",
        "=" * 70,
        f"Tổng số trial: {len(tat_ca_trials)}",
        f"AUC baseline : {baseline_auc:.6f}" if baseline_auc else "AUC baseline : Chưa có",
        f"AUC tốt nhất : {best_trial['mean_auc']:.6f} (Trial #{best_trial['trial_id']})",
        "",
        "── BẢNG XẾP HẠNG (sắp theo AUC giảm dần) ──────────────────────",
        f"  {'Trial':6s}  {'AUC mean':10s}  {'AUC std':10s}  {'Thời gian':10s}",
        "  " + "-" * 50,
    ]

    for t in sorted(tat_ca_trials, key=lambda x: x["mean_auc"], reverse=True):
        lines.append(
            f"  #{t['trial_id']:4d}    {t['mean_auc']:.6f}    {t['std_auc']:.6f}"
            f"    {t['thoi_gian_s']:.0f}s"
        )

    lines += [
        "",
        "── THÔNG SỐ TỐT NHẤT ───────────────────────────────────────────",
    ]
    for k, v in best_trial["params"].items():
        if isinstance(v, float):
            lines.append(f"  {k:25s}: {v:.6g}")
        else:
            lines.append(f"  {k:25s}: {v}")
    lines.append("=" * 70)

    duong_dan.write_text("\n".join(lines), encoding="utf-8")
    return duong_dan


def tu_dong_chinh_thong_so(
    dataset: str,
    so_trial: int = 20,
    max_epochs: int = 500,
    so_fold_thu: int = 3,
    target_auc: float = 0.99,
    seed: int = 42,
) -> Dict[str, Any]:
    """Tự động tìm kiếm thông số huấn luyện tốt hơn baseline.

    Thuật toán:
    -----------
    - Vòng lặp qua so_trial trial.
    - Trial lẻ (1, 3, 5...): random search toàn cục trong KHONG_GIAN_TIM_KIEM.
    - Trial chẵn (2, 4, 6...): perturbation từ bộ tốt nhất hiện tại.
    - Mỗi trial chạy so_fold_thu fold đầu (nhanh hơn full K-Fold).
    - Lưu lịch sử sau mỗi trial vào lich_su_thong_so_train/.
    - Nếu tìm được bộ tốt hơn baseline → chạy full K-Fold để xác nhận.

    Args:
        dataset    : tên dataset (B-dataset / C-dataset / F-dataset)
        so_trial   : số lần thử tối đa
        max_epochs : số epoch tối đa mỗi trial (để trial chạy nhanh)
        so_fold_thu: số fold mỗi trial (dùng fold đầu để ước lượng nhanh)
        target_auc : AUC mục tiêu — dừng sớm nếu đạt
        seed       : seed ngẫu nhiên

    Returns:
        Dict chứa thông tin trial tốt nhất
    """
    random.seed(seed)
    np.random.seed(seed)
    dat_seed(seed)

    weights_dir = _PROJECT_ROOT / "weights"
    baseline_auc = _doc_auc_goc(dataset, weights_dir)

    print("\n" + "=" * 70)
    print(f"  AUTO-TUNE: {dataset}")
    print("=" * 70)
    if baseline_auc is not None:
        print(f"  AUC baseline: {baseline_auc:.6f}")
    else:
        print("  [!] Chưa có AUC baseline — mọi kết quả đều được lưu")
    print(f"  Số trial   : {so_trial}")
    print(f"  Max epochs : {max_epochs}")
    print(f"  Fold/trial : {so_fold_thu}")
    print(f"  Target AUC : {target_auc}")
    print("=" * 70)

    # Cấu hình gốc dùng làm base
    base_cfg = CauHinh(
        ten_dataset=dataset,
        bat_chuan_hoa=True,
        ghep_nhieu_feature=True,
    )

    best_auc = baseline_auc if baseline_auc is not None else -1.0
    best_params: Optional[Dict[str, Any]] = None
    best_trial_info: Dict[str, Any] = {}
    tat_ca_trials: List[Dict[str, Any]] = []

    for trial_id in range(1, so_trial + 1):
        print(f"\n{'─'*60}")
        print(f"  Trial {trial_id}/{so_trial}")
        print(f"{'─'*60}")

        # Chọn chiến lược: random (trial lẻ) hoặc perturbation (trial chẵn)
        if best_params is None or trial_id % 2 == 1:
            params = _lay_mau_ngau_nhien(KHONG_GIAN_TIM_KIEM)
            chien_luoc = "Random Search"
        else:
            # Perturbation mạnh nếu đang bí (nhiều trial không cải thiện)
            so_trial_khong_cai_thien = trial_id - (best_trial_info.get("trial_id", 0))
            cuong_do = 0.15 + min(0.35, so_trial_khong_cai_thien * 0.05)
            params = _perturbation(best_params, KHONG_GIAN_TIM_KIEM, cuong_do=cuong_do)
            chien_luoc = f"Perturbation (cường độ={cuong_do:.2f})"

        print(f"  Chiến lược : {chien_luoc}")
        print(f"  Thông số   : lr={params.get('toc_do_hoc', '?'):.2e}"
              f"  hidden={params.get('kich_thuoc_an', '?')}"
              f"  gcn_layers={params.get('so_lop_gcn', '?')}")

        # Tạo cấu hình cho trial này
        cfg = _tao_cau_hinh(base_cfg, params, max_epochs)

        # Chạy K-Fold rút gọn
        t_start = time.perf_counter()
        try:
            mean_auc, std_auc, chi_so_folds = _chay_kfold_nhanh(cfg, so_fold_thu)
        except Exception as e:
            print(f"  [!] Trial {trial_id} thất bại: {e}")
            tat_ca_trials.append({
                "trial_id": trial_id,
                "mean_auc": -1.0,
                "std_auc": 0.0,
                "params": params,
                "thoi_gian_s": time.perf_counter() - t_start,
                "loi": str(e),
            })
            continue
        thoi_gian_s = time.perf_counter() - t_start

        la_tot_nhat = mean_auc > best_auc
        print(f"\n  → AUC={mean_auc:.6f} ± {std_auc:.4f}  (baseline={best_auc:.6f})"
              f"  {'✅ TỐT HƠN!' if la_tot_nhat else '— không cải thiện'}")

        # ── Ghi log vào TrainLogger ─────────────────────────────────────────
        if _LOGGER_AVAILABLE and chi_so_folds:
            try:
                _tl = TrainLogger(dataset=dataset, source="auto_tune_trial", trial_id=trial_id)
                _tl.begin_from_params(params)
                _tl.end(chi_so_folds, baseline_auc=baseline_auc)
            except Exception as _le:
                pass  # Không để lỗi logger phá vỡ luồng auto-tune

        # Lưu lịch sử
        tep_lich_su = _luu_lich_su(
            dataset=dataset,
            trial_id=trial_id,
            params=params,
            mean_auc=mean_auc,
            std_auc=std_auc,
            chi_so_folds=chi_so_folds,
            la_tot_nhat=la_tot_nhat,
            baseline_auc=baseline_auc,
            thoi_gian_s=thoi_gian_s,
        )
        print(f"  → Đã lưu: {tep_lich_su.name}")

        trial_info = {
            "trial_id": trial_id,
            "mean_auc": mean_auc,
            "std_auc": std_auc,
            "params": params,
            "thoi_gian_s": thoi_gian_s,
            "chi_so_folds": chi_so_folds,
        }
        tat_ca_trials.append(trial_info)

        if la_tot_nhat:
            best_auc = mean_auc
            best_params = copy.deepcopy(params)
            best_trial_info = copy.deepcopy(trial_info)

        # Dừng sớm nếu đạt target
        if mean_auc >= target_auc:
            print(f"\n  🎯 Đạt mục tiêu AUC={target_auc}! Dừng sớm.")
            break

    # Lưu tổng kết
    if best_trial_info:
        tep_tong_ket = _luu_tong_ket(dataset, tat_ca_trials, best_trial_info, baseline_auc)
        print(f"\n  📋 Tổng kết: {tep_tong_ket}")

        print("\n" + "=" * 70)
        print(f"  KẾT QUẢ CUỐI — {dataset}")
        print("=" * 70)
        print(f"  AUC baseline  : {baseline_auc:.6f}" if baseline_auc else "  AUC baseline  : Chưa có")
        print(f"  AUC tốt nhất : {best_trial_info['mean_auc']:.6f} (Trial #{best_trial_info['trial_id']})")
        print("  Thông số tốt nhất:")
        for k, v in best_trial_info["params"].items():
            if isinstance(v, float):
                print(f"    {k:25s}: {v:.6g}")
            else:
                print(f"    {k:25s}: {v}")
        print("=" * 70)

    return best_trial_info


def _retrain_voi_thong_so_tot_nhat(
    dataset: str,
    best_params: Dict[str, Any],
    full_epochs: int = 2000,
    k_fold: int = 10,
) -> None:
    """Retrain đầy đủ K-Fold với thông số tốt nhất tìm được từ auto-tune.

    Được gọi sau khi auto-tune tìm được bộ thông số vượt baseline AUC.
    Khác với _chay_kfold_nhanh() (chỉ dùng vài fold để đánh giá nhanh),
    hàm này chạy đầy đủ K-Fold và lưu trọng số chính thức vào weights/<dataset>/.

    Quy trình:
    1. Tạo SimpleNamespace giả lập argparse.Namespace từ best_params + CauHinh defaults.
    2. Gọi _huan_luyen_mot_dataset(fake_args, dataset) — chạy K-Fold đầy đủ.
    3. Kết quả mới (kfold_metrics.json) sẽ là baseline mới cho lần auto-tune tiếp.
    4. Lưu thông số retrain vào lich_su_thong_so_train/ với nhãn RETRAIN_CONFIRMED.

    Args:
        dataset    : tên dataset (B-dataset / C-dataset / F-dataset)
        best_params: dict thông số tốt nhất từ tu_dong_chinh_thong_so()
        full_epochs: số epoch đầy đủ cho retrain (thường = CauHinh.so_epoch = 2000)
        k_fold     : số fold cho retrain (thường = CauHinh.so_fold = 10)
    """
    print(f"\n{'='*70}")
    print(f"  RETRAIN ĐẦY ĐỦ — {dataset} với thông số auto-tune tốt nhất")
    print(f"  Epochs: {full_epochs}  K-Fold: {k_fold}")
    print(f"{'='*70}")

    base = CauHinh()

    # Tạo fake args namespace — giả lập argparse.Namespace mà _huan_luyen_mot_dataset cần
    fake_args = SimpleNamespace(
        # Thông số lấy từ best_params (kết quả auto-tune)
        learning_rate=best_params.get("toc_do_hoc", base.toc_do_hoc),
        weight_decay=best_params.get("weight_decay", base.weight_decay),
        gcn_layers=best_params.get("so_lop_gcn", base.so_lop_gcn),
        hidden_size=best_params.get("kich_thuoc_an", base.kich_thuoc_an),
        output_size=best_params.get("kich_thuoc_ra", base.kich_thuoc_ra),
        dropout=best_params.get("dropout_decoder", base.dropout_decoder),
        negative_rate=best_params.get("ti_le_am", base.ti_le_am),
        lr_factor=best_params.get("factor_lr", base.factor_lr),
        lr_patience=best_params.get("patience_lr", base.patience_lr),
        clip_grad=best_params.get("grad_clip", base.grad_clip),
        label_smoothing=best_params.get("label_smoothing", base.label_smoothing),
        lambda_rank=best_params.get("lambda_rank", base.lambda_rank),
        margin_rank=best_params.get("margin_rank", base.margin_rank),
        # Thông số cố định (không tune)
        epochs=full_epochs,
        k_fold=k_fold,
        patience=base.patience,
        min_delta=base.min_delta,
        min_lr=base.min_lr,
        pos_weight=base.pos_weight_duong,
        no_normalize=not base.bat_chuan_hoa,
        no_multi_feature=not base.ghep_nhieu_feature,
        device=base.thiet_bi,
        amp=base.bat_amp,
        # Auto-tune flags (không dùng trong _huan_luyen_mot_dataset nhưng cần tránh AttributeError)
        auto_tune=False,
        auto_tune_trials=0,
        auto_tune_max_epochs=0,
        auto_tune_folds=0,
        auto_tune_target_auc=0.99,
    )

    print("  Thông số retrain:")
    for k, v in best_params.items():
        if isinstance(v, float):
            print(f"    {k:25s}: {v:.6g}")
        else:
            print(f"    {k:25s}: {v}")
    print()

    # Chạy K-Fold đầy đủ
    _huan_luyen_mot_dataset(fake_args, dataset)

    # Lưu bản ghi xác nhận retrain
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    duong_dan = LICH_SU_DIR / f"{dataset}_RETRAIN_CONFIRMED_{timestamp}.txt"
    lines = [
        "=" * 70,
        f"  RETRAIN XÁC NHẬN — {dataset}",
        "=" * 70,
        f"Thời gian    : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"Epochs       : {full_epochs}",
        f"K-Fold       : {k_fold}",
        "",
        "── THÔNG SỐ ĐÃ DÙNG ───────────────────────────────────────────",
    ]
    for k, v in best_params.items():
        lines.append(f"  {k:25s}: {v:.6g}" if isinstance(v, float) else f"  {k:25s}: {v}")
    lines += [
        "",
        "Kết quả đã lưu vào: weights/" + dataset + "/kfold_metrics.json",
        "=" * 70,
    ]
    duong_dan.write_text("\n".join(lines), encoding="utf-8")
    print(f"\n  Đã lưu bản ghi retrain: {duong_dan.name}")


def main() -> None:
    """Điểm vào chính của tool auto-tune.

    Khi chạy trực tiếp:
      python auto_tune.py --dataset C-dataset --trials 20

    Khi được gọi từ huan_luyen.py (--auto-tune):
      python huan_luyen.py --dataset C-dataset --auto-tune --auto-tune-trials 20
      → huan_luyen.py train xong → gọi _chay_auto_tune() → lazy import auto_tune

    Khi muốn tìm thông số VÀ retrain ngay nếu tốt hơn:
      python auto_tune.py --dataset C-dataset --trials 20 --retrain-if-better
    """
    parser = argparse.ArgumentParser(
        description="Auto-tune thông số huấn luyện FuzzyGCN",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ví dụ:
  python auto_tune.py --dataset C-dataset --trials 20 --target-auc 0.95
  python auto_tune.py --dataset B-dataset --trials 30 --max-epochs 300
  python auto_tune.py --all-datasets --trials 10 --folds-per-trial 2
  python auto_tune.py --dataset C-dataset --trials 15 --retrain-if-better
        """,
    )
    parser.add_argument(
        "--dataset", type=str, default="C-dataset",
        choices=["B-dataset", "C-dataset", "F-dataset"],
        help="Tên dataset cần tune (mặc định: C-dataset)",
    )
    parser.add_argument(
        "--all-datasets", action="store_true",
        help="Tune lần lượt tất cả 3 dataset",
    )
    parser.add_argument(
        "--trials", type=int, default=20,
        help="Số trial tối đa (mặc định: 20)",
    )
    parser.add_argument(
        "--max-epochs", type=int, default=500,
        help="Số epoch tối đa mỗi trial (mặc định: 500). "
             "Giảm để trial chạy nhanh hơn, tăng để ước lượng chính xác hơn.",
    )
    parser.add_argument(
        "--folds-per-trial", type=int, default=3,
        help="Số fold chạy mỗi trial (mặc định: 3). "
             "Ít fold → nhanh hơn nhưng ước lượng kém ổn định hơn.",
    )
    parser.add_argument(
        "--target-auc", type=float, default=0.99,
        help="AUC mục tiêu để dừng sớm (mặc định: 0.99)",
    )
    parser.add_argument(
        "--seed", type=int, default=42,
        help="Seed ngẫu nhiên (mặc định: 42)",
    )
    parser.add_argument(
        "--retrain-if-better", action="store_true",
        help="Nếu tìm được thông số tốt hơn baseline → retrain đầy đủ K-Fold ngay",
    )
    parser.add_argument(
        "--full-epochs", type=int, default=CauHinh.so_epoch,
        help=f"Số epoch khi retrain đầy đủ (mặc định: {CauHinh.so_epoch})",
    )
    parser.add_argument(
        "--k-fold", type=int, default=CauHinh.so_fold,
        help=f"Số fold khi retrain đầy đủ (mặc định: {CauHinh.so_fold})",
    )

    args = parser.parse_args()

    datasets = ["B-dataset", "C-dataset", "F-dataset"] if args.all_datasets else [args.dataset]

    for ds in datasets:
        best_trial = tu_dong_chinh_thong_so(
            dataset=ds,
            so_trial=args.trials,
            max_epochs=args.max_epochs,
            so_fold_thu=args.folds_per_trial,
            target_auc=args.target_auc,
            seed=args.seed,
        )

        # Nếu yêu cầu retrain và tìm được thông số tốt hơn baseline
        if args.retrain_if_better and best_trial:
            baseline_auc = _doc_auc_goc(ds, _PROJECT_ROOT / "weights")
            if baseline_auc is None or best_trial["mean_auc"] > baseline_auc:
                print(f"\n[AutoTune] Bat dau retrain day du cho {ds}...")
                _retrain_voi_thong_so_tot_nhat(
                    dataset=ds,
                    best_params=best_trial["params"],
                    full_epochs=args.full_epochs,
                    k_fold=args.k_fold,
                )
            else:
                print(
                    f"\n[AutoTune] Best trial AUC ({best_trial['mean_auc']:.6f}) "
                    f"chua vuot baseline ({baseline_auc:.6f}). Bo qua retrain."
                )


if __name__ == "__main__":
    main()
