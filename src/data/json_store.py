from __future__ import annotations

import json
import logging
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parent


def _get_data_source():
    try:
        from data.data_source_status import data_source
        return data_source
    except Exception:
        return None


class JsonTable:
    """Thread-safe, in-memory + file-backed JSON table."""

    def __init__(self, name: str, path: Path, owner: JsonStore | None = None) -> None:
        self.name = name
        self._path = path
        self._owner = owner
        self._lock = threading.Lock()
        self._data: list[dict[str, Any]] = []
        self._load()

    def _load(self) -> None:
        try:
            text = self._path.read_text(encoding="utf-8").strip()
            self._data = json.loads(text) if text else []
        except (FileNotFoundError, json.JSONDecodeError) as exc:
            log.warning("[JsonStore] Cannot load %s: %s. Using empty list.", self._path.name, exc)
            self._data = []

    def _save(self) -> None:
        try:
            self._path.write_text(
                json.dumps(self._data, ensure_ascii=False, indent=2, default=str),
                encoding="utf-8",
            )
            if self._owner is not None:
                self._owner.mark_internal_write(self.name)
        except Exception as exc:  # noqa: BLE001
            log.error("[JsonStore] Cannot save %s: %s", self._path.name, exc)

    def all(self) -> list[dict[str, Any]]:
        with self._lock:
            return [dict(row) for row in self._data]

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
        with self._lock:
            result = []
            for row in self._data:
                if all(row.get(key) == value for key, value in kwargs.items()):
                    result.append(dict(row))
            return result

    def find_one(self, **kwargs: Any) -> dict[str, Any] | None:
        rows = self.find(**kwargs)
        return rows[0] if rows else None

    def upsert(self, record: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            rid = record.get("id")
            if rid is not None:
                for index, row in enumerate(self._data):
                    if row.get("id") == rid:
                        self._data[index] = dict(record)
                        self._save()
                        break
                else:
                    self._data.append(dict(record))
                    self._save()
            else:
                max_id = max((row.get("id", 0) for row in self._data), default=0)
                record = dict(record)
                record["id"] = max_id + 1
                self._data.append(record)
                self._save()

        if self._owner is not None:
            self._owner.sync_table_to_db(self.name)
        return dict(record)

    def delete(self, record_id: int) -> bool:
        with self._lock:
            before = len(self._data)
            self._data = [row for row in self._data if row.get("id") != record_id]
            changed = len(self._data) < before
            if changed:
                self._save()

        if changed and self._owner is not None:
            self._owner.sync_table_to_db(self.name)
        return changed

    def replace_all(self, records: list[dict[str, Any]], sync_to_db: bool = True) -> None:
        with self._lock:
            self._data = [dict(row) for row in records]
            self._save()

        if sync_to_db and self._owner is not None:
            self._owner.sync_table_to_db(self.name)

    def reload(self) -> None:
        with self._lock:
            self._load()

    def __repr__(self) -> str:  # noqa: D105
        return f"<JsonTable {self._path.name} ({len(self._data)} rows)>"


class JsonStore:
    """Central registry for all JSON-backed tables."""

    def __init__(self, data_dir: Path = DATA_DIR) -> None:
        self._dir = data_dir
        self._sync_lock = threading.Lock()
        self._watch_thread: threading.Thread | None = None
        self._watch_stop = threading.Event()
        self._watch_started = False
        self._file_tokens: dict[str, tuple[int, int]] = {}
        self._internal_write_until: dict[str, float] = {}
        self._poll_interval = 1.0

        self.users = JsonTable("users", data_dir / "users.json", self)
        self.drugs = JsonTable("drugs", data_dir / "drugs.json", self)
        self.diseases = JsonTable("diseases", data_dir / "diseases.json", self)
        self.proteins = JsonTable("proteins", data_dir / "proteins.json", self)
        self.drug_disease_links = JsonTable("drug_disease_links", data_dir / "drug_disease_links.json", self)
        self.drug_protein_links = JsonTable("drug_protein_links", data_dir / "drug_protein_links.json", self)
        self.protein_disease_links = JsonTable("protein_disease_links", data_dir / "protein_disease_links.json", self)
        self.prediction_history = JsonTable("prediction_history", data_dir / "prediction_history.json", self)

        self.thuoc_b = JsonTable("thuoc_b", data_dir / "thuoc_b.json", self)
        self.thuoc_c = JsonTable("thuoc_c", data_dir / "thuoc_c.json", self)
        self.thuoc_f = JsonTable("thuoc_f", data_dir / "thuoc_f.json", self)
        self.benh_b = JsonTable("benh_b", data_dir / "benh_b.json", self)
        self.benh_c = JsonTable("benh_c", data_dir / "benh_c.json", self)
        self.benh_f = JsonTable("benh_f", data_dir / "benh_f.json", self)
        self.protein_b = JsonTable("protein_b", data_dir / "protein_b.json", self)
        self.protein_c = JsonTable("protein_c", data_dir / "protein_c.json", self)
        self.protein_f = JsonTable("protein_f", data_dir / "protein_f.json", self)
        self.lien_ket_b = JsonTable("lien_ket_b", data_dir / "lien_ket_b.json", self)
        self.lien_ket_c = JsonTable("lien_ket_c", data_dir / "lien_ket_c.json", self)
        self.lien_ket_f = JsonTable("lien_ket_f", data_dir / "lien_ket_f.json", self)

        self._tables: dict[str, JsonTable] = {
            "users": self.users,
            "drugs": self.drugs,
            "diseases": self.diseases,
            "proteins": self.proteins,
            "drug_disease_links": self.drug_disease_links,
            "drug_protein_links": self.drug_protein_links,
            "protein_disease_links": self.protein_disease_links,
            "prediction_history": self.prediction_history,
            "thuoc_b": self.thuoc_b,
            "thuoc_c": self.thuoc_c,
            "thuoc_f": self.thuoc_f,
            "benh_b": self.benh_b,
            "benh_c": self.benh_c,
            "benh_f": self.benh_f,
            "protein_b": self.protein_b,
            "protein_c": self.protein_c,
            "protein_f": self.protein_f,
            "lien_ket_b": self.lien_ket_b,
            "lien_ket_c": self.lien_ket_c,
            "lien_ket_f": self.lien_ket_f,
        }
        self._file_tokens = {
            name: self._file_token(table._path)
            for name, table in self._tables.items()
        }

    def table(self, name: str) -> JsonTable:
        table = self._tables.get(name)
        if table is None:
            raise KeyError(f"Unknown JSON table '{name}'")
        return table

    def reload_all(self) -> None:
        for table in self._tables.values():
            table.reload()
        log.info("[JsonStore] Reloaded %d tables from %s", len(self._tables), self._dir)

    def summary(self) -> dict[str, int]:
        return {name: table.count() for name, table in self._tables.items()}

    def mark_internal_write(self, table_name: str, ttl_seconds: float = 2.0) -> None:
        table = self.table(table_name)
        self._file_tokens[table_name] = self._file_token(table._path)
        self._internal_write_until[table_name] = time.monotonic() + ttl_seconds

    def start_realtime_sync(self, poll_interval: float = 1.0) -> None:
        if self._watch_started:
            return
        self._poll_interval = max(0.5, float(poll_interval))
        self._watch_stop.clear()
        self._watch_thread = threading.Thread(
            target=self._watch_loop,
            daemon=True,
            name="json-realtime-sync",
        )
        self._watch_thread.start()
        self._watch_started = True
        log.info("[JsonStore] Started realtime JSON -> DB sync")

    def sync_all_to_db(self) -> None:
        for name in self._tables:
            self.sync_table_to_db(name)

    def sync_table_to_db(self, table_name: str, reload_from_disk: bool = False) -> bool:
        if not self._db_sync_enabled():
            return False

        table = self.table(table_name)
        if reload_from_disk:
            table.reload()
        records = table.all()

        with self._sync_lock:
            session_factory, model_map = self._db_runtime()
            model_cls = model_map.get(table_name)
            if session_factory is None or model_cls is None:
                return False

            session = session_factory()
            try:
                existing_rows = session.query(model_cls).all()
                existing_by_id = {
                    getattr(row, "id", None): row
                    for row in existing_rows
                    if getattr(row, "id", None) is not None
                }
                seen_ids: set[int] = set()

                for record in records:
                    payload = self._normalize_record(table_name, record, existing_by_id)
                    row_id = payload.get("id")
                    if row_id is not None:
                        seen_ids.add(row_id)

                    current = existing_by_id.get(row_id)
                    if current is None:
                        session.add(model_cls(**payload))
                        continue

                    for key, value in payload.items():
                        setattr(current, key, value)

                for row_id, current in existing_by_id.items():
                    if row_id not in seen_ids:
                        session.delete(current)

                session.commit()
                data_source = _get_data_source()
                if data_source:
                    data_source.update_json_counts(self.summary())
                log.info("[JsonStore] Synced %s (%d rows) from JSON to DB", table_name, len(records))
                return True
            except Exception as exc:  # noqa: BLE001
                session.rollback()
                log.warning("[JsonStore] Failed syncing %s to DB: %s", table_name, exc)
                return False
            finally:
                session.close()

    def _watch_loop(self) -> None:
        while not self._watch_stop.wait(self._poll_interval):
            for table_name, table in self._tables.items():
                token = self._file_token(table._path)
                previous = self._file_tokens.get(table_name)
                if token == previous:
                    continue

                self._file_tokens[table_name] = token
                if self._internal_write_until.get(table_name, 0.0) > time.monotonic():
                    continue

                log.info("[JsonStore] External change detected: %s", table._path.name)
                self.sync_table_to_db(table_name, reload_from_disk=True)

    @staticmethod
    def _file_token(path: Path) -> tuple[int, int]:
        try:
            stat = path.stat()
            return (stat.st_mtime_ns, stat.st_size)
        except FileNotFoundError:
            return (0, 0)

    @staticmethod
    def _normalize_bool(value: Any) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return bool(value)
        return str(value).strip().lower() in {"1", "true", "yes", "y"}

    @staticmethod
    def _normalize_datetime(value: Any) -> datetime:
        if isinstance(value, datetime):
            return value
        if isinstance(value, str) and value.strip():
            try:
                return datetime.fromisoformat(value.replace("Z", "+00:00"))
            except ValueError:
                pass
        return datetime.utcnow()

    def _normalize_record(
        self,
        table_name: str,
        record: dict[str, Any],
        existing_by_id: dict[int, Any],
    ) -> dict[str, Any]:
        payload = dict(record)
        row_id = payload.get("id")
        existing = existing_by_id.get(row_id)

        if table_name == "users":
            payload["username"] = str(payload.get("username") or "").strip()
            payload["email"] = payload.get("email") or None
            payload["role"] = str(payload.get("role") or getattr(existing, "role", "user") or "user")
            password_hash = payload.get("password_hash") or getattr(existing, "password_hash", None)
            if not password_hash:
                try:
                    from backend.app.security import hash_password

                    password_hash = hash_password("change_me")
                except Exception:
                    password_hash = "change_me"
            payload["password_hash"] = str(password_hash)
        elif table_name == "prediction_history":
            payload["score"] = float(payload.get("score") or 0.0)
            payload["known"] = self._normalize_bool(payload.get("known"))
            payload["timestamp"] = self._normalize_datetime(payload.get("timestamp"))

        return payload

    @staticmethod
    def _db_runtime() -> tuple[Any, dict[str, Any]]:
        try:
            from backend.app.database import SessionLocal
            from backend.app.models import (
                BenhB,
                BenhC,
                BenhF,
                Disease,
                Drug,
                DrugDiseaseLink,
                DrugProteinLink,
                LienKetB,
                LienKetC,
                LienKetF,
                PredictionHistory,
                Protein,
                ProteinB,
                ProteinC,
                ProteinDiseaseLink,
                ProteinF,
                ThuocB,
                ThuocC,
                ThuocF,
                User,
            )
        except Exception:
            return None, {}

        model_map = {
            "users": User,
            "drugs": Drug,
            "diseases": Disease,
            "proteins": Protein,
            "drug_disease_links": DrugDiseaseLink,
            "drug_protein_links": DrugProteinLink,
            "protein_disease_links": ProteinDiseaseLink,
            "prediction_history": PredictionHistory,
            "thuoc_b": ThuocB,
            "thuoc_c": ThuocC,
            "thuoc_f": ThuocF,
            "benh_b": BenhB,
            "benh_c": BenhC,
            "benh_f": BenhF,
            "protein_b": ProteinB,
            "protein_c": ProteinC,
            "protein_f": ProteinF,
            "lien_ket_b": LienKetB,
            "lien_ket_c": LienKetC,
            "lien_ket_f": LienKetF,
        }
        return SessionLocal, model_map

    @staticmethod
    def _db_sync_enabled() -> bool:
        session_factory, _ = JsonStore._db_runtime()
        if session_factory is None:
            return False
        data_source = _get_data_source()
        return bool(data_source and data_source.is_db_connected())

    def __repr__(self) -> str:  # noqa: D105
        total = sum(table.count() for table in self._tables.values())
        return f"<JsonStore dir={self._dir} tables={len(self._tables)} total_rows={total}>"


store = JsonStore()
