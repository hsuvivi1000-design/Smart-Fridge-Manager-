import sqlite3
import os
from contextlib import contextmanager
from datetime import datetime

DB_PATH = os.getenv("DB_PATH", "fridge_inventory.db")

def init_db():
    """初始化資料庫與資料表"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # 1. 建立食材庫存表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS inventory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                category TEXT,
                quantity REAL NOT NULL,
                unit TEXT NOT NULL,
                purchase_date DATE,
                expiry_date DATE,
                status TEXT DEFAULT 'fresh',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 2. 建立歷史異動紀錄表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS action_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                action_type TEXT NOT NULL,          -- 'ADD', 'CONSUME', 'UPDATE_QTY', 'DELETE'
                ingredient_name TEXT NOT NULL,
                quantity REAL,
                unit TEXT,
                details TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()

@contextmanager
def get_db_connection():
    """提供資料庫連線的 Context Manager"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # 讓結果可以像 dict 一樣存取
    try:
        yield conn
    finally:
        conn.close()

def execute_query(query, params=(), fetch=False):
    """執行 SQL 查詢"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        if fetch:
            result = cursor.fetchall()
            return [dict(row) for row in result]
        conn.commit()
        return cursor.lastrowid
