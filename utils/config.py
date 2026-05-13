"""
應用程式設定與常數定義
"""
import os
from dotenv import load_dotenv

load_dotenv()

# --- Gemini API ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = "gemini-3.1-flash-lite"

# --- Database ---
DATABASE_PATH = "fridge.db"

# --- 食材分類 ---
CATEGORIES = ["蔬菜", "水果", "肉類", "海鮮", "乳製品", "蛋", "調味料", "其他"]

CATEGORY_ICONS = {
    "蔬菜": "🥬",
    "水果": "🍎",
    "肉類": "🥩",
    "海鮮": "🦐",
    "乳製品": "🥛",
    "蛋": "🥚",
    "調味料": "🧂",
    "其他": "📦",
}

# --- 預設保存天數 ---
SHELF_LIFE_DAYS = {
    "蔬菜": 5,
    "水果": 7,
    "肉類": 3,
    "海鮮": 2,
    "乳製品": 7,
    "蛋": 14,
    "調味料": 180,
    "其他": 7,
}

# --- 單位 ---
UNITS = ["個", "顆", "把", "包", "盒", "瓶", "罐", "克", "公斤", "毫升", "公升", "片", "條", "塊"]

# --- 效期警告門檻 ---
EXPIRY_WARNING_DAYS = 3
