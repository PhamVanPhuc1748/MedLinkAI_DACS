import json
import sqlite3
import os
from pathlib import Path

# Đường dẫn tới file JSON và Database
BASE_DIR = Path(__file__).parent
JSON_FILE = BASE_DIR / "prediction_history.json"
DB_FILE = BASE_DIR / "prediction_history.db"

def init_db(conn):
    cursor = conn.cursor()
    # Tạo bảng lưu lịch sử chung
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT,
        username TEXT,
        query TEXT,
        query_type TEXT,
        dataset TEXT,
        timestamp TEXT,
        top_score REAL
    )
    """)
    
    # Tạo bảng lưu chi tiết kết quả (Top N)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS history_results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        history_id INTEGER,
        name TEXT,
        score REAL,
        is_known BOOLEAN,
        FOREIGN KEY(history_id) REFERENCES history(id)
    )
    """)
    conn.commit()

def load_json_to_sql():
    if not JSON_FILE.exists():
        print(f"Không tìm thấy file {JSON_FILE}")
        return

    with open(JSON_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    conn = sqlite3.connect(DB_FILE)
    init_db(conn)
    cursor = conn.cursor()

    for record in data:
        # Chèn vào bảng history
        cursor.execute("""
            INSERT INTO history (user_id, username, query, query_type, dataset, timestamp, top_score)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            record.get("user_id"),
            record.get("username"),
            record.get("query"),
            record.get("query_type"),
            record.get("dataset"),
            record.get("timestamp"),
            record.get("top_score")
        ))
        
        history_id = cursor.lastrowid
        
        # Chèn vào bảng history_results
        results = record.get("results", [])
        for res in results:
            cursor.execute("""
                INSERT INTO history_results (history_id, name, score, is_known)
                VALUES (?, ?, ?, ?)
            """, (
                history_id,
                res.get("name"),
                res.get("score"),
                res.get("known")
            ))
            
    conn.commit()
    conn.close()
    print(f"Da do du lieu tu JSON vao {DB_FILE} thanh cong!")

if __name__ == "__main__":
    load_json_to_sql()
