"""Shared UI settings for the Smart Fridge Manager app."""

import os

from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
DATABASE_PATH = os.getenv("DB_PATH", "fridge_inventory.db")

CATEGORIES = [
    "蔬菜",
    "肉類",
    "海鮮",
    "水果",
    "乳製品",
    "蛋",
    "冷凍食品/火鍋料",
    "調味料",
    "其他",
]

CATEGORY_ICONS = {
    "蔬菜": "🥬",
    "肉類": "🥩",
    "海鮮": "🦐",
    "水果": "🍎",
    "乳製品": "🥛",
    "蛋": "🥚",
    "冷凍食品/火鍋料": "🧊",
    "調味料": "🧂",
    "其他": "📦",
}

UNITS = [
    "個",
    "顆",
    "把",
    "包",
    "盒",
    "瓶",
    "罐",
    "片",
    "條",
    "塊",
    "串",
    "根",
    "束",
    "份",
    "盤",
    "碗",
    "杯",
    "袋",
    "籃",
    "粒",
    "克",
    "公斤",
    "毫克",
    "毫升",
    "公升",
]

DEFAULT_UNIT = "個"

UNIT_ALIASES = {
    "": DEFAULT_UNIT,
    "只": "個",
    "個兒": "個",
    "棵": "顆",
    "一串": "串",
    "支": "根",
    "公克": "克",
    "g": "克",
    "G": "克",
    "kg": "公斤",
    "KG": "公斤",
    "ml": "毫升",
    "ML": "毫升",
    "l": "公升",
    "L": "公升",
}

STORAGE_METHODS = ["冷藏", "冷凍", "常溫"]
EXPIRY_WARNING_DAYS = 3
