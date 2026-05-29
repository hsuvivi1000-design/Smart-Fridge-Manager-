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
    "克",
    "公斤",
    "毫升",
    "公升",
]

STORAGE_METHODS = ["冷藏", "冷凍", "常溫"]
EXPIRY_WARNING_DAYS = 3
