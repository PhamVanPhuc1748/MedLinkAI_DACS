"""Xóa toàn bộ dữ liệu trong các bảng (giữ schema) để seed lại."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src" / "backend"))

from sqlalchemy import text
from app.database import engine

with engine.begin() as conn:
    print("Tắt FK constraints...")
    conn.execute(text("EXEC sp_msforeachtable 'ALTER TABLE ? NOCHECK CONSTRAINT ALL'"))
    print("Xóa drug_disease_links...")
    conn.execute(text("DELETE FROM drug_disease_links"))
    print("Xóa predictions_history...")
    conn.execute(text("DELETE FROM predictions_history"))
    print("Xóa diseases...")
    conn.execute(text("DELETE FROM diseases"))
    print("Xóa drugs...")
    conn.execute(text("DELETE FROM drugs"))
    print("Bật lại FK constraints...")
    conn.execute(text("EXEC sp_msforeachtable 'ALTER TABLE ? CHECK CONSTRAINT ALL'"))
    print("DONE - tất cả bảng đã được xóa (giữ users).")
