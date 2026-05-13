"""
SQLite 資料庫操作模組
"""
import sqlite3
from datetime import datetime, timedelta
from utils.config import DATABASE_PATH, SHELF_LIFE_DAYS


def get_connection():
    """取得資料庫連線"""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """初始化資料庫表"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ingredients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            quantity REAL NOT NULL DEFAULT 1,
            unit TEXT NOT NULL DEFAULT '個',
            category TEXT NOT NULL DEFAULT '其他',
            purchase_date TEXT NOT NULL,
            expiry_date TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now', 'localtime'))
        )
    """)
    conn.commit()
    conn.close()


def add_ingredient(name, quantity, unit, category, purchase_date, expiry_date=None):
    """新增食材到資料庫"""
    if expiry_date is None:
        shelf_days = SHELF_LIFE_DAYS.get(category, 7)
        purchase_dt = datetime.strptime(purchase_date, "%Y-%m-%d")
        expiry_date = (purchase_dt + timedelta(days=shelf_days)).strftime("%Y-%m-%d")

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO ingredients (name, quantity, unit, category, purchase_date, expiry_date) VALUES (?, ?, ?, ?, ?, ?)",
        (name, quantity, unit, category, purchase_date, expiry_date),
    )
    conn.commit()
    conn.close()


def get_all_ingredients():
    """取得所有食材，按效期排序"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM ingredients ORDER BY expiry_date ASC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def delete_ingredient(ingredient_id):
    """刪除食材"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM ingredients WHERE id = ?", (ingredient_id,))
    conn.commit()
    conn.close()


def update_ingredient_quantity(ingredient_id, new_quantity):
    """更新食材數量，若數量 ≤ 0 則刪除"""
    conn = get_connection()
    cursor = conn.cursor()
    if new_quantity <= 0:
        cursor.execute("DELETE FROM ingredients WHERE id = ?", (ingredient_id,))
    else:
        cursor.execute(
            "UPDATE ingredients SET quantity = ? WHERE id = ?",
            (new_quantity, ingredient_id),
        )
    conn.commit()
    conn.close()


def get_ingredient_stats():
    """取得庫存統計數據"""
    conn = get_connection()
    cursor = conn.cursor()

    today = datetime.now().strftime("%Y-%m-%d")
    warning_date = (datetime.now() + timedelta(days=3)).strftime("%Y-%m-%d")

    cursor.execute("SELECT COUNT(*) FROM ingredients")
    total = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM ingredients WHERE expiry_date <= ?", (today,))
    expired = cursor.fetchone()[0]

    cursor.execute(
        "SELECT COUNT(*) FROM ingredients WHERE expiry_date > ? AND expiry_date <= ?",
        (today, warning_date),
    )
    expiring = cursor.fetchone()[0]

    fresh = total - expired - expiring

    conn.close()
    return {"total": total, "fresh": fresh, "expiring": expiring, "expired": expired}


def get_category_counts():
    """取得各分類食材數量"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT category, COUNT(*) as count FROM ingredients GROUP BY category"
    )
    rows = cursor.fetchall()
    conn.close()
    return {row["category"]: row["count"] for row in rows}
