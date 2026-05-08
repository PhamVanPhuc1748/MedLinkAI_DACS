"""
src/data/json_store.py
──────────────────────────────────────────────────────────────────────────────
Module đọc/ghi JSON cho tất cả bảng trong hệ thống.

Mỗi bảng được quản lý bởi một JsonTable instance.
JsonTable hỗ trợ:
  - all()           → list[dict]
  - get(id)         → dict | None
  - find(**kwargs)  → list[dict]  (lọc theo field bất kỳ)
  - upsert(record)  → dict        (thêm hoặc cập nhật theo id)
  - delete(id)      → bool
  - replace_all(records) → None   (thay toàn bộ nội dung)
  - count()         → int

Cách dùng:
  from src.data.json_store import store
  store.drugs.all()
  store.diseases.find(name="Cancer")
  store.prediction_history.upsert({...})
"""
from __future__ import annotations

import json
import logging
import threading
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

# Thư mục chứa các file JSON
DATA_DIR = Path(__file__).resolve().parent


# ── Lớp quản lý từng bảng JSON ────────────────────────────────────────────────
class JsonTable:
    """Thread-safe, in-memory + file-backed JSON table."""

    def __init__(self, path: Path) -> None:
        self._path = path
        self._lock = threading.Lock()
        self._data: list[dict[str, Any]] = []
        self._load()

    # ── Đọc từ file ──────────────────────────────────────────────────────────
    def _load(self) -> None:
        try:
            text = self._path.read_text(encoding="utf-8").strip()
            self._data = json.loads(text) if text else []
        except (FileNotFoundError, json.JSONDecodeError) as exc:
            log.warning("[JsonStore] Không đọc được %s: %s — dùng danh sách rỗng", self._path.name, exc)
            self._data = []

    # ── Ghi xuống file ───────────────────────────────────────────────────────
    def _save(self) -> None:
        try:
            self._path.write_text(
                json.dumps(self._data, ensure_ascii=False, indent=2, default=str),
                encoding="utf-8",
            )
        except Exception as exc:  # noqa: BLE001
            log.error("[JsonStore] Không ghi được %s: %s", self._path.name, exc)

    # ── API công khai ─────────────────────────────────────────────────────────
    def all(self) -> list[dict[str, Any]]:
        with self._lock:
            return list(self._data)

    def count(self) -> int:
        with self._lock:
            return len(self._data)

    def get(self, record_id: int) -> dict[str, Any] | None:
        with self._lock:
            for row in self._data:
                if row.get("id") == record_id:
                    return dict(row)
        return None

    def find(self, **kwargs: Any) -> list[dict[str, Any]]:
        """Lọc các bản ghi khớp với tất cả kwargs được cung cấp."""
        with self._lock:
            result = []
            for row in self._data:
                if all(row.get(k) == v for k, v in kwargs.items()):
                    result.append(dict(row))
            return result

    def find_one(self, **kwargs: Any) -> dict[str, Any] | None:
        rows = self.find(**kwargs)
        return rows[0] if rows else None

    def upsert(self, record: dict[str, Any]) -> dict[str, Any]:
        """Thêm mới hoặc cập nhật bản ghi theo trường `id`."""
        with self._lock:
            rid = record.get("id")
            if rid is not None:
                for i, row in enumerate(self._data):
                    if row.get("id") == rid:
                        self._data[i] = dict(record)
                        self._save()
                        return dict(record)
            # Tự tạo id nếu chưa có
            if rid is None:
                max_id = max((r.get("id", 0) for r in self._data), default=0)
                record = dict(record)
                record["id"] = max_id + 1
            self._data.append(record)
            self._save()
            return dict(record)

    def delete(self, record_id: int) -> bool:
        with self._lock:
            before = len(self._data)
            self._data = [r for r in self._data if r.get("id") != record_id]
            changed = len(self._data) < before
            if changed:
                self._save()
            return changed

    def replace_all(self, records: list[dict[str, Any]]) -> None:
        """Thay toàn bộ nội dung bảng (dùng khi sync từ DB)."""
        with self._lock:
            self._data = [dict(r) for r in records]
            self._save()

    def reload(self) -> None:
        """Đọc lại từ file (hữu ích khi file bị thay đổi bên ngoài)."""
        with self._lock:
            self._load()

    def __repr__(self) -> str:  # noqa: D105
        return f"<JsonTable {self._path.name} ({len(self._data)} rows)>"


# ── Registry tập trung ────────────────────────────────────────────────────────
class JsonStore:
    """
    Điểm truy cập trung tâm cho toàn bộ các bảng JSON.

    Sử dụng:
        from src.data.json_store import store
        store.drugs.all()
    """

    def __init__(self, data_dir: Path = DATA_DIR) -> None:
        self._dir = data_dir

        # ── Bảng chung ────────────────────────────────────────────────
        self.users               = JsonTable(data_dir / "users.json")
        self.drugs               = JsonTable(data_dir / "drugs.json")
        self.diseases            = JsonTable(data_dir / "diseases.json")
        self.proteins            = JsonTable(data_dir / "proteins.json")
        self.drug_disease_links  = JsonTable(data_dir / "drug_disease_links.json")
        self.drug_protein_links  = JsonTable(data_dir / "drug_protein_links.json")
        self.protein_disease_links = JsonTable(data_dir / "protein_disease_links.json")
        self.prediction_history  = JsonTable(data_dir / "prediction_history.json")

        # ── Bảng theo dataset ─────────────────────────────────────────
        self.thuoc_b    = JsonTable(data_dir / "thuoc_b.json")
        self.thuoc_c    = JsonTable(data_dir / "thuoc_c.json")
        self.thuoc_f    = JsonTable(data_dir / "thuoc_f.json")
        self.benh_b     = JsonTable(data_dir / "benh_b.json")
        self.benh_c     = JsonTable(data_dir / "benh_c.json")
        self.benh_f     = JsonTable(data_dir / "benh_f.json")
        self.protein_b  = JsonTable(data_dir / "protein_b.json")
        self.protein_c  = JsonTable(data_dir / "protein_c.json")
        self.protein_f  = JsonTable(data_dir / "protein_f.json")
        self.lien_ket_b = JsonTable(data_dir / "lien_ket_b.json")
        self.lien_ket_c = JsonTable(data_dir / "lien_ket_c.json")
        self.lien_ket_f = JsonTable(data_dir / "lien_ket_f.json")

        # Map tên bảng → JsonTable (dùng khi sync động)
        self._tables: dict[str, JsonTable] = {
            "users":                   self.users,
            "drugs":                   self.drugs,
            "diseases":                self.diseases,
            "proteins":                self.proteins,
            "drug_disease_links":      self.drug_disease_links,
            "drug_protein_links":      self.drug_protein_links,
            "protein_disease_links":   self.protein_disease_links,
            "prediction_history":      self.prediction_history,
            "thuoc_b": self.thuoc_b,   "thuoc_c": self.thuoc_c,   "thuoc_f": self.thuoc_f,
            "benh_b":  self.benh_b,    "benh_c":  self.benh_c,    "benh_f":  self.benh_f,
            "protein_b": self.protein_b, "protein_c": self.protein_c, "protein_f": self.protein_f,
            "lien_ket_b": self.lien_ket_b, "lien_ket_c": self.lien_ket_c, "lien_ket_f": self.lien_ket_f,
        }

    def table(self, name: str) -> JsonTable:
        """Lấy JsonTable theo tên."""
        t = self._tables.get(name)
        if t is None:
            raise KeyError(f"Không có bảng JSON tên '{name}'")
        return t

    def reload_all(self) -> None:
        """Đọc lại tất cả bảng từ file."""
        for t in self._tables.values():
            t.reload()
        log.info("[JsonStore] Đã reload %d bảng từ %s", len(self._tables), self._dir)

    def summary(self) -> dict[str, int]:
        """Trả về dict {tên_bảng: số_bản_ghi}."""
        return {name: t.count() for name, t in self._tables.items()}

    def __repr__(self) -> str:  # noqa: D105
        total = sum(t.count() for t in self._tables.values())
        return f"<JsonStore dir={self._dir} tables={len(self._tables)} total_rows={total}>"


# ── Singleton toàn cục ────────────────────────────────────────────────────────
store = JsonStore()
