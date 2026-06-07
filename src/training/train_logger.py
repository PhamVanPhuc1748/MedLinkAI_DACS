"""
train_logger.py — Module tự động lưu thông số và kết quả huấn luyện FuzzyGCN.
===============================================================================

Mỗi lần train (kể cả auto-tune trial), module này ghi lại:
  - Thời điểm bắt đầu / kết thúc
  - Toàn bộ siêu tham số (CauHinh / params dict)
  - Kết quả từng fold: AUC, AUPR, Accuracy, Precision, Recall, F1, MCC
  - Trung bình ± std toàn bộ folds
  - Nguồn gọi: manual / auto_tune_trial / auto_tune_retrain

File lưu theo 3 định dạng song song:
  1. train_logs/<dataset>/runs.jsonl       — mỗi dòng là 1 JSON record (dễ parse)
  2. train_logs/<dataset>/runs_table.csv  — bảng CSV (mở Excel được)
  3. train_logs/summary.json             — tổng hợp best run mỗi dataset
"""
from __future__ import annotations

import csv
import json
import os
import platform
import socket
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# ── Đường dẫn gốc: src/training/ → project root là 2 cấp trên ───────────────
_THIS_DIR    = Path(__file__).resolve().parent          # src/training/
_PROJECT_ROOT = _THIS_DIR.parent.parent                  # model_GNN_new/
LOGS_DIR = _PROJECT_ROOT / "src" / "training" / "train_logs"


# ── Cấu trúc 1 bản ghi huấn luyện ───────────────────────────────────────────
@dataclass
class TrainRecord:
    # Định danh
    run_id: str = ""
    dataset: str = ""
    source: str = "manual"          # manual | auto_tune_trial | auto_tune_retrain
    trial_id: Optional[int] = None  # Chỉ điền khi source = auto_tune_*

    # Thời gian
    started_at: str = ""
    finished_at: str = ""
    duration_s: float = 0.0

    # Môi trường
    hostname: str = ""
    python: str = ""
    device: str = ""
    cuda_available: bool = False
    cuda_name: str = ""

    # Siêu tham số kiến trúc
    so_lop_gcn: int = 0
    kich_thuoc_an: int = 0
    kich_thuoc_ra: int = 0
    dropout_decoder: float = 0.0

    # Siêu tham số tối ưu
    toc_do_hoc: float = 0.0
    weight_decay: float = 0.0
    grad_clip: float = 0.0
    label_smoothing: float = 0.0
    lambda_rank: float = 0.0
    margin_rank: float = 0.0
    pos_weight: float = 0.0
    factor_lr: float = 0.0
    patience_lr: int = 0
    min_lr: float = 0.0

    # Tham số huấn luyện
    so_epoch: int = 0
    so_fold: int = 0
    ti_le_am: float = 0.0
    patience: int = 0
    bat_chuan_hoa: bool = True
    ghep_nhieu_feature: bool = True
    seed: int = 42

    # Kết quả tổng hợp (mean ± std)
    auc_mean: float = 0.0
    auc_std: float = 0.0
    aupr_mean: float = 0.0
    aupr_std: float = 0.0
    accuracy_mean: float = 0.0
    accuracy_std: float = 0.0
    precision_mean: float = 0.0
    precision_std: float = 0.0
    recall_mean: float = 0.0
    recall_std: float = 0.0
    f1_mean: float = 0.0
    f1_std: float = 0.0
    mcc_mean: float = 0.0
    mcc_std: float = 0.0

    # Kết quả chi tiết từng fold
    folds: List[Dict[str, float]] = field(default_factory=list)

    # Cờ
    is_best_ever: bool = False       # True nếu đây là AUC cao nhất từ trước đến nay
    improved_from: float = 0.0      # AUC baseline trước khi run này


# ── Hàm tiện ích nội bộ ──────────────────────────────────────────────────────
def _now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _run_id(dataset: str, source: str) -> str:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:20]
    return f"{dataset}_{source}_{ts}"


def _env_info() -> Dict[str, Any]:
    try:
        import torch
        cuda_avail = torch.cuda.is_available()
        cuda_name = torch.cuda.get_device_name(0) if cuda_avail else ""
    except Exception:
        cuda_avail, cuda_name = False, ""
    return {
        "hostname": socket.gethostname(),
        "python": platform.python_version(),
        "cuda_available": cuda_avail,
        "cuda_name": cuda_name,
    }


def _calc_stats(folds: List[Dict[str, float]]) -> Dict[str, float]:
    """Tính mean và std cho từng metric qua tất cả fold."""
    import statistics
    keys = ["AUC", "AUPR", "Accuracy", "Precision", "Recall", "F1", "MCC"]
    out: Dict[str, float] = {}
    for k in keys:
        vals = [f.get(k, 0.0) for f in folds]
        out[f"{k.lower()}_mean"] = float(sum(vals) / len(vals)) if vals else 0.0
        out[f"{k.lower()}_std"] = float(statistics.stdev(vals)) if len(vals) > 1 else 0.0
    return out


def _csv_header() -> List[str]:
    return [
        "run_id", "dataset", "source", "trial_id",
        "started_at", "finished_at", "duration_s",
        "hostname", "device", "cuda_name",
        "so_lop_gcn", "kich_thuoc_an", "kich_thuoc_ra", "dropout_decoder",
        "toc_do_hoc", "weight_decay", "grad_clip",
        "label_smoothing", "lambda_rank", "margin_rank", "pos_weight",
        "factor_lr", "patience_lr", "min_lr",
        "so_epoch", "so_fold", "ti_le_am", "patience",
        "bat_chuan_hoa", "ghep_nhieu_feature", "seed",
        "auc_mean", "auc_std", "aupr_mean", "aupr_std",
        "accuracy_mean", "accuracy_std", "precision_mean", "precision_std",
        "recall_mean", "recall_std", "f1_mean", "f1_std",
        "mcc_mean", "mcc_std",
        "is_best_ever", "improved_from",
    ]


# ── Lớp Logger chính ─────────────────────────────────────────────────────────
class TrainLogger:
    """Logger tự động ghi lại mọi lần chạy huấn luyện.

    Cách dùng trong huan_luyen.py:
        logger = TrainLogger(dataset)
        logger.begin(cau_hinh)
        # ... train ...
        logger.end(danh_sach_chi_so)

    Cách dùng trong auto_tune.py (từng trial):
        logger = TrainLogger(dataset, source="auto_tune_trial", trial_id=trial_id)
        logger.begin_from_params(params)
        logger.end(chi_so_folds)
    """

    def __init__(
        self,
        dataset: str,
        source: str = "manual",
        trial_id: Optional[int] = None,
    ):
        self.dataset = dataset
        self.source = source
        self.trial_id = trial_id
        self._record = TrainRecord(
            run_id=_run_id(dataset, source),
            dataset=dataset,
            source=source,
            trial_id=trial_id,
            started_at=_now_str(),
        )
        self._t0 = time.perf_counter()

        # Chuẩn bị thư mục
        self._log_dir = LOGS_DIR / dataset
        self._log_dir.mkdir(parents=True, exist_ok=True)

        # Điền thông tin môi trường
        env = _env_info()
        self._record.hostname = env["hostname"]
        self._record.python = env["python"]
        self._record.cuda_available = env["cuda_available"]
        self._record.cuda_name = env["cuda_name"]

    def begin(self, cau_hinh: Any) -> "TrainLogger":
        """Điền thông tin từ CauHinh dataclass."""
        r = self._record
        r.device = getattr(cau_hinh, "thiet_bi", "auto")
        r.so_lop_gcn = getattr(cau_hinh, "so_lop_gcn", 0)
        r.kich_thuoc_an = getattr(cau_hinh, "kich_thuoc_an", 0)
        r.kich_thuoc_ra = getattr(cau_hinh, "kich_thuoc_ra", 0)
        r.dropout_decoder = getattr(cau_hinh, "dropout_decoder", 0.0)
        r.toc_do_hoc = getattr(cau_hinh, "toc_do_hoc", 0.0)
        r.weight_decay = getattr(cau_hinh, "weight_decay", 0.0)
        r.grad_clip = getattr(cau_hinh, "grad_clip", 0.0)
        r.label_smoothing = getattr(cau_hinh, "label_smoothing", 0.0)
        r.lambda_rank = getattr(cau_hinh, "lambda_rank", 0.0)
        r.margin_rank = getattr(cau_hinh, "margin_rank", 0.0)
        r.pos_weight = getattr(cau_hinh, "pos_weight_duong", 1.0)
        r.factor_lr = getattr(cau_hinh, "factor_lr", 0.0)
        r.patience_lr = getattr(cau_hinh, "patience_lr", 0)
        r.min_lr = getattr(cau_hinh, "min_lr", 0.0)
        r.so_epoch = getattr(cau_hinh, "so_epoch", 0)
        r.so_fold = getattr(cau_hinh, "so_fold", 0)
        r.ti_le_am = getattr(cau_hinh, "ti_le_am", 1.0)
        r.patience = getattr(cau_hinh, "patience", 0)
        r.bat_chuan_hoa = getattr(cau_hinh, "bat_chuan_hoa", True)
        r.ghep_nhieu_feature = getattr(cau_hinh, "ghep_nhieu_feature", True)
        r.seed = getattr(cau_hinh, "seed", 42)
        return self

    def begin_from_params(self, params: Dict[str, Any]) -> "TrainLogger":
        """Điền thông tin từ params dict (dùng trong auto_tune)."""
        r = self._record
        r.so_lop_gcn = params.get("so_lop_gcn", 0)
        r.kich_thuoc_an = params.get("kich_thuoc_an", 0)
        r.kich_thuoc_ra = params.get("kich_thuoc_ra", 0)
        r.dropout_decoder = params.get("dropout_decoder", 0.0)
        r.toc_do_hoc = params.get("toc_do_hoc", 0.0)
        r.weight_decay = params.get("weight_decay", 0.0)
        r.grad_clip = params.get("grad_clip", 0.0)
        r.label_smoothing = params.get("label_smoothing", 0.0)
        r.lambda_rank = params.get("lambda_rank", 0.0)
        r.margin_rank = params.get("margin_rank", 0.0)
        r.factor_lr = params.get("factor_lr", 0.0)
        r.patience_lr = params.get("patience_lr", 0)
        r.ti_le_am = params.get("ti_le_am", 1.0)
        return self

    def end(
        self,
        folds: List[Dict[str, float]],
        baseline_auc: Optional[float] = None,
    ) -> TrainRecord:
        """Ghi kết quả sau khi train xong, lưu file."""
        r = self._record
        r.finished_at = _now_str()
        r.duration_s = round(time.perf_counter() - self._t0, 2)
        r.folds = folds

        # Tính stats
        stats = _calc_stats(folds)
        for k, v in stats.items():
            setattr(r, k, v)

        # Cờ is_best_ever
        if baseline_auc is not None:
            r.improved_from = baseline_auc
            r.is_best_ever = r.auc_mean > baseline_auc
        else:
            r.is_best_ever = True  # Lần đầu tiên

        # Ghi file
        self._write_jsonl(r)
        self._write_csv(r)
        self._update_summary(r)

        self._print_summary(r)
        return r

    # ── Ghi JSONL ────────────────────────────────────────────────────────────
    def _write_jsonl(self, r: TrainRecord) -> None:
        path = self._log_dir / "runs.jsonl"
        record_dict = asdict(r)
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record_dict, ensure_ascii=False) + "\n")

    # ── Ghi CSV ──────────────────────────────────────────────────────────────
    def _write_csv(self, r: TrainRecord) -> None:
        path = self._log_dir / "runs_table.csv"
        header = _csv_header()
        file_exists = path.exists()
        with open(path, "a", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=header, extrasaction="ignore")
            if not file_exists:
                writer.writeheader()
            row = asdict(r)
            row.pop("folds", None)  # Bỏ cột folds (quá dài)
            writer.writerow(row)

    # ── Cập nhật summary.json ─────────────────────────────────────────────────
    def _update_summary(self, r: TrainRecord) -> None:
        path = LOGS_DIR / "summary.json"
        summary: Dict[str, Any] = {}
        if path.exists():
            try:
                summary = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                pass

        ds = r.dataset
        if ds not in summary or r.auc_mean > summary[ds].get("auc_mean", 0.0):
            summary[ds] = {
                "run_id": r.run_id,
                "auc_mean": round(r.auc_mean, 6),
                "auc_std": round(r.auc_std, 6),
                "aupr_mean": round(r.aupr_mean, 6),
                "f1_mean": round(r.f1_mean, 6),
                "mcc_mean": round(r.mcc_mean, 6),
                "so_lop_gcn": r.so_lop_gcn,
                "kich_thuoc_an": r.kich_thuoc_an,
                "kich_thuoc_ra": r.kich_thuoc_ra,
                "toc_do_hoc": r.toc_do_hoc,
                "weight_decay": r.weight_decay,
                "ti_le_am": r.ti_le_am,
                "dropout_decoder": r.dropout_decoder,
                "label_smoothing": r.label_smoothing,
                "lambda_rank": r.lambda_rank,
                "updated_at": r.finished_at,
                "source": r.source,
            }
            path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    # ── In tóm tắt ───────────────────────────────────────────────────────────
    def _print_summary(self, r: TrainRecord) -> None:
        star = " ** NEW BEST!" if r.is_best_ever else ""
        lines = [
            f"\n{'='*65}",
            f"  [TrainLogger] {r.dataset} | {r.source}{star}",
            f"  Run ID    : {r.run_id}",
            f"  Time      : {r.duration_s:.0f}s ({r.started_at} -> {r.finished_at})",
            f"{'─'*65}",
            f"  {'Metric':<14} {'Mean':>10}  {'Std':>10}",
            f"  {'─'*40}",
        ]
        for m in ["auc", "aupr", "accuracy", "precision", "recall", "f1", "mcc"]:
            mean = getattr(r, f"{m}_mean", 0.0)
            std  = getattr(r, f"{m}_std", 0.0)
            label = m.upper() if m in ("auc", "aupr", "mcc") else m.capitalize()
            flag = " <-- BEST" if m == "auc" and r.is_best_ever else ""
            lines.append(f"  {label:<14} {mean:>10.4f}  {std:>10.4f}{flag}")
        lines += [
            f"{'─'*65}",
            f"  Saved to : src/training/train_logs/{r.dataset}/runs.jsonl",
            f"             src/training/train_logs/{r.dataset}/runs_table.csv",
            f"{'='*65}\n",
        ]
        for line in lines:
            _safe_print(line)



# ── Hàm tiện ích đọc lại logs ────────────────────────────────────────────────
def load_runs(dataset: str) -> List[Dict[str, Any]]:
    """Đọc toàn bộ lịch sử huấn luyện của 1 dataset từ runs.jsonl."""
    path = LOGS_DIR / dataset / "runs.jsonl"
    if not path.exists():
        return []
    runs = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            try:
                runs.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return runs


def load_summary() -> Dict[str, Any]:
    """Đọc bảng tổng hợp best run của mỗi dataset."""
    path = LOGS_DIR / "summary.json"
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _safe_print(text: str) -> None:
    """In văn bản ra console, bỏ qua lỗi encoding trên Windows."""
    try:
        print(text)
    except UnicodeEncodeError:
        print(text.encode("ascii", "replace").decode())


def print_leaderboard() -> None:
    """In bảng xếp hạng AUC tốt nhất của từng dataset."""
    summary = load_summary()
    if not summary:
        _safe_print("[TrainLogger] Chua co du lieu. Hay train it nhat 1 lan.")
        return
    _safe_print("\n" + "=" * 70)
    _safe_print("  BANG XEP HANG — AUC TOT NHAT TUNG DATASET")
    _safe_print("=" * 70)
    _safe_print(f"  {'Dataset':<16} {'AUC':>8}  {'AUPR':>8}  {'F1':>8}  {'MCC':>8}  {'Source':<20}")
    _safe_print("  " + "─" * 62)
    for ds, info in sorted(summary.items(), key=lambda x: -x[1].get("auc_mean", 0)):
        _safe_print(
            f"  {ds:<16} {info['auc_mean']:>8.4f}  {info['aupr_mean']:>8.4f}"
            f"  {info['f1_mean']:>8.4f}  {info['mcc_mean']:>8.4f}  {info['source']:<20}"
        )
    _safe_print("=" * 70 + "\n")



# ── Điểm vào CLI ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "leaderboard":
        print_leaderboard()
    elif len(sys.argv) > 1 and sys.argv[1] == "show":
        ds = sys.argv[2] if len(sys.argv) > 2 else "B-dataset"
        runs = load_runs(ds)
        print(f"\n[{ds}] {len(runs)} runs:")
        for r in runs[-10:]:  # Hiện 10 runs gần nhất
            print(
                f"  {r['run_id']}  AUC={r['auc_mean']:.4f}±{r['auc_std']:.4f}"
                f"  src={r['source']}"
            )
    else:
        print("Cách dùng:")
        print("  python -m src.training.train_logger leaderboard")
        print("  python -m src.training.train_logger show B-dataset")
