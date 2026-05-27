import os
import re
import logging
from datetime import datetime, timedelta
from typing import Optional

logger = logging.getLogger(__name__)

# ============================================================
# 保存期限規則表 (SHELF_LIFE_RULES)
# key: (sub_category, storage_method)
# value: 預設保存天數 (int)
# storage_method: '冷藏' | '冷凍' | '常溫'
# ============================================================
SHELF_LIFE_RULES: dict[tuple[str, str], int] = {
    # 蔬菜 — 葉菜類 (高水分、快速失水)
    ("蔬菜-葉菜類", "冷藏"): 4,
    # 蔬菜 — 根莖類/其他 (組織緊密、耐放)
    ("蔬菜-根莖類", "冷藏"): 14,
    # 肉類
    ("肉類", "冷藏"): 3,
    ("肉類", "冷凍"): 90,
    # 海鮮
    ("海鮮", "冷藏"): 2,
    ("海鮮", "冷凍"): 30,
    # 水果
    ("水果", "冷藏"): 7,
    ("水果", "常溫"): 5,
    # 乳製品
    ("乳製品", "冷藏"): 7,
    # 冷凍食品/火鍋料
    ("冷凍食品/火鍋料", "冷凍"): 180,
    # 調味料
    ("調味料", "常溫"): 365,
    ("調味料", "冷藏"): 180,
    # 其他
    ("其他", "冷藏"): 7,
    ("其他", "常溫"): 7,
}

# 葉菜類本地正則關鍵字
LEAFY_KEYWORDS = re.compile(
    r"(菠菜|萵苣|茼蔻|空心菜|莧菜|韭菜|芹菜|高麗菜|大白菜|小白菜|青江菜|油菜|芥菜|生菜|羅蔓|西洋菜|地瓜葉|"
    r"九層塔|香菜|蔥|韭|菜心|芫荽|紫蘇|白菜|包菜|芥藍)"
)
# 根莖類本地正則關鍵字
ROOT_KEYWORDS = re.compile(
    r"(胡蘿蔔|蘿蔔|馬鈴薯|地瓜|芋頭|山藥|淮山|洋蔥|大蒜|蒜頭|薑|蓮藕|牛蒡|竹筍|蘆筍|筍|甜菜根|"
    r"白蘿蔔|紅蘿蔔|番薯|甘薯)"
)


def classify_sub_category(name: str, category: str, api_key: Optional[str] = None) -> str:
    """
    判斷食材的細分類別。

    針對「蔬菜」類別進一步細分為：
      - '蔬菜-葉菜類'
      - '蔬菜-根莖類'
    其餘類別直接回傳原始類別 (例如 '肉類'、'海鮮' 等)。

    優先使用 Gemini API 判定；若無 API Key 或發生錯誤，則降級為本地 Regex。

    Args:
        name (str): 食材名稱，例如 "高麗菜"。
        category (str): 一級分類，例如 "蔬菜"。
        api_key (Optional[str]): Gemini API 金鑰，預設從環境變數讀取。

    Returns:
        str: 細分類別字串，例如 '蔬菜-葉菜類' 或 '肉類'。
    """
    # 非蔬菜類不需要細分
    if category != "蔬菜":
        # 對冷凍食品/火鍋料特別處理，保留斜線
        return category

    # === 本地 Regex 判斷 ===
    def _classify_local(name: str) -> str:
        if ROOT_KEYWORDS.search(name):
            return "蔬菜-根莖類"
        if LEAFY_KEYWORDS.search(name):
            return "蔬菜-葉菜類"
        # 名稱含「菜」字的預設歸葉菜類
        if "菜" in name:
            return "蔬菜-葉菜類"
        return "蔬菜-根莖類"  # 其他蔬菜（菇類、瓜類等）歸根莖類，因為保鮮期較長

    # === Gemini API 判斷 ===
    key = api_key or os.getenv("GEMINI_API_KEY")
    if not key:
        return _classify_local(name)

    try:
        import google.generativeai as genai
        genai.configure(api_key=key)

        prompt = f"""你是廚房食材分類助手。請將以下「蔬菜類」食材進一步細分為「葉菜類」或「根莖類」。
- 葉菜類：以葉片或莖葉為主的蔬菜，例如：高麗菜、菠菜、空心菜、青江菜、萵苣、蔥、韭菜等。
- 根莖類：以根、莖、球莖、菇類、瓜類為主的蔬菜，例如：胡蘿蔔、馬鈴薯、洋蔥、蒜頭、薑、蓮藕、香菇、冬瓜等。

食材名稱：「{name}」
請只回答「葉菜類」或「根莖類」，不要有任何其他文字。"""

        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(prompt)
        result = response.text.strip()

        if "葉菜" in result:
            return "蔬菜-葉菜類"
        elif "根莖" in result:
            return "蔬菜-根莖類"
        else:
            return _classify_local(name)

    except Exception as e:
        logger.warning(f"Gemini 細分類別判定失敗，降級使用本地 Regex: {e}")
        return _classify_local(name)


def get_shelf_life_days(sub_category: str, storage_method: str = "冷藏") -> int:
    """
    根據細分類別與儲存方式查表，回傳預設保存天數。

    Args:
        sub_category (str): 細分類別，例如 '蔬菜-葉菜類'、'肉類'、'海鮮' 等。
        storage_method (str): 儲存方式，'冷藏' | '冷凍' | '常溫'，預設為 '冷藏'。

    Returns:
        int: 預設保存天數。
    """
    # 冷凍食品與調味料儲存方式自動修正
    if sub_category == "冷凍食品/火鍋料":
        storage_method = "冷凍"
    elif sub_category == "調味料" and storage_method == "冷藏":
        storage_method = "常溫"

    # 直接精確查詢
    days = SHELF_LIFE_RULES.get((sub_category, storage_method))
    if days is not None:
        return days

    # 若指定儲存方式查不到，嘗試冷藏
    days = SHELF_LIFE_RULES.get((sub_category, "冷藏"))
    if days is not None:
        return days

    # 最後備援：7 天
    logger.warning(f"未知細分類別 '{sub_category}' 或儲存方式 '{storage_method}'，使用預設 7 天。")
    return 7



def estimate_expiry_date(
    name: str,
    category: str,
    purchase_date: Optional[str] = None,
    storage_method: str = "冷藏",
    api_key: Optional[str] = None,
) -> tuple[str, str, int]:
    """
    根據食材名稱與類別，自動推算預估到期日。

    Args:
        name (str): 食材名稱，例如 "高麗菜"。
        category (str): 一級分類，例如 "蔬菜"。
        purchase_date (Optional[str]): 購買日期 'YYYY-MM-DD'，預設為今天。
        storage_method (str): 儲存方式，預設 '冷藏'。
        api_key (Optional[str]): Gemini API 金鑰（可選）。

    Returns:
        tuple[str, str, int]:
            (expiry_date, sub_category, shelf_days)
            - expiry_date: 推算到期日 'YYYY-MM-DD'
            - sub_category: 細分類別字串
            - shelf_days: 使用的預設保存天數
    """
    # 購買日期預設為今天
    if purchase_date:
        try:
            purchase_dt = datetime.strptime(purchase_date, "%Y-%m-%d")
        except ValueError:
            logger.warning(f"購買日期格式錯誤 '{purchase_date}'，使用今天。")
            purchase_dt = datetime.now()
    else:
        purchase_dt = datetime.now()

    # 細分類別判定
    sub_category = classify_sub_category(name, category, api_key=api_key)

    # 查表取得保存天數
    shelf_days = get_shelf_life_days(sub_category, storage_method)

    # 計算到期日
    expiry_dt = purchase_dt + timedelta(days=shelf_days)
    expiry_date = expiry_dt.strftime("%Y-%m-%d")

    return expiry_date, sub_category, shelf_days
