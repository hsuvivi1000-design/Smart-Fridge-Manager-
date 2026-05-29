"""
應用程式設定與常數定義 — 合併 main + D1257081 設定
"""
import os
from dotenv import load_dotenv

load_dotenv()

# --- Gemini API ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = "gemini-2.5-flash"

# --- Database ---
DATABASE_PATH = os.getenv("DB_PATH", "fridge_inventory.db")

# --- 食材分類（合併 main + D1257081）---
CATEGORIES = ["蔬菜", "肉類", "海鮮", "水果", "乳製品", "蛋", "冷凍食品/火鍋料", "調味料", "其他"]

CATEGORY_ICONS = {
    "蔬菜": "🥬",
    "水果": "🍎",
    "肉類": "🥩",
    "海鮮": "🦐",
    "乳製品": "🥛",
    "蛋": "🥚",
    "冷凍食品/火鍋料": "🧊",
    "調味料": "🧂",
    "其他": "📦",
}

# --- 預設保存天數（依分類）---
SHELF_LIFE_DAYS = {
    "蔬菜": 5,
    "水果": 7,
    "肉類": 3,
    "海鮮": 2,
    "乳製品": 7,
    "蛋": 14,
    "冷凍食品/火鍋料": 30,
    "調味料": 180,
    "其他": 7,
}

# --- 單位（放寬，含日常單位）---
UNITS = ["個", "顆", "把", "包", "盒", "瓶", "罐", "克", "公斤", "毫克", "毫升", "公升", "片", "條", "塊"]

# --- 效期警告門檻 ---
EXPIRY_WARNING_DAYS = 3
