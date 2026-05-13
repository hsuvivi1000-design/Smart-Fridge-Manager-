"""
Gemini API 封裝模組
"""
import json
from utils.config import GEMINI_API_KEY, GEMINI_MODEL, CATEGORIES


def get_client():
    """取得 Gemini API 客戶端，若未設定 API Key 則回傳 None"""
    if not GEMINI_API_KEY or GEMINI_API_KEY == "your_gemini_api_key_here":
        return None
    from google import genai
    return genai.Client(api_key=GEMINI_API_KEY)


def identify_ingredients(image):
    """透過 Gemini Vision 辨識圖片中的食材，回傳食材列表"""
    client = get_client()
    if client is None:
        return None

    categories_str = "、".join(CATEGORIES)
    prompt = f"""請仔細辨識這張圖片中的所有食材。
以 JSON 陣列格式回傳，每個食材包含：
- name: 食材名稱（繁體中文）
- quantity: 預估數量（數字）
- unit: 單位（如：個、顆、瓶、克等）
- category: 分類（必須是：{categories_str} 之一）
只回傳 JSON 陣列。"""

    try:
        from google.genai import types
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=[image, prompt],
            config=types.GenerateContentConfig(response_mime_type="application/json"),
        )
        result = json.loads(response.text)
        return result if isinstance(result, list) else []
    except Exception as e:
        raise RuntimeError(f"Gemini 辨識失敗：{e}")


def suggest_recipes(ingredients_list, preferences=""):
    """根據食材清單與偏好，請 Gemini 生成食譜建議"""
    client = get_client()
    if client is None:
        return None

    ingredients_str = "\n".join(f"- {item}" for item in ingredients_list)
    pref_str = f"\n使用者飲食偏好：{preferences}" if preferences else ""

    prompt = f"""你是專業家庭料理廚師。根據以下食材推薦 3 道家常料理。
現有食材：
{ingredients_str}{pref_str}

以 JSON 陣列回傳，每道含：name, description, ingredients(列表), steps(列表), cooking_time, difficulty
只回傳 JSON。"""

    try:
        from google.genai import types
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(response_mime_type="application/json"),
        )
        result = json.loads(response.text)
        return result if isinstance(result, list) else []
    except Exception as e:
        raise RuntimeError(f"Gemini 食譜推薦失敗：{e}")


def process_chat_input(user_message, ingredients_list, preferences=""):
    """
    處理使用者聊天輸入，回傳結構化回應與執行日誌。
    回傳 dict: {response, action, ingredients[], execution_log[]}
    """
    client = get_client()
    if client is None:
        return {
            "response": "⚠️ 尚未設定 Gemini API Key，請在 .env 中填入 GEMINI_API_KEY。",
            "action": "none",
            "ingredients": [],
            "execution_log": [
                {"type": "thought", "content": "偵測到 API Key 尚未設定。"}
            ],
        }

    inv_str = "\n".join(
        [f"- {i['name']} ({i['quantity']}{i['unit']}, 到期: {i['expiry_date']})" for i in ingredients_list]
    ) if ingredients_list else "（冰箱目前沒有食材）"

    categories_str = "、".join(CATEGORIES)

    prompt = f"""你是 AI 冰箱管家。請根據使用者訊息回應。

使用者訊息：{user_message}
目前庫存：
{inv_str}
使用者偏好：{preferences if preferences else "無"}

請以 JSON 回傳：
{{
  "response": "回覆文字（繁體中文、友善自然）",
  "action": "none" 或 "add_ingredient" 或 "suggest_recipe",
  "ingredients": [若 action 為 add_ingredient，列出食材 {{"name":"xx","quantity":1,"unit":"個","category":"蔬菜"}}，category 必須是 {categories_str} 之一],
  "execution_log": [
    {{"type": "thought", "content": "你的思考過程"}},
    {{"type": "tool", "content": "工具呼叫描述與參數"}},
    {{"type": "tool_result", "content": "工具回傳結果"}},
    {{"type": "memory", "content": "讀取的使用者記憶/偏好"}},
    {{"type": "rag", "content": "檢索食譜庫的結果"}}
  ]
}}
只回傳 JSON。"""

    try:
        from google.genai import types
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(response_mime_type="application/json"),
        )
        result = json.loads(response.text)
        # Ensure required keys exist
        result.setdefault("response", "已收到您的訊息。")
        result.setdefault("action", "none")
        result.setdefault("ingredients", [])
        result.setdefault("execution_log", [])
        return result
    except Exception as e:
        return {
            "response": f"處理時發生錯誤：{e}",
            "action": "none",
            "ingredients": [],
            "execution_log": [{"type": "thought", "content": f"錯誤：{e}"}],
        }


def process_image_input(image, preferences=""):
    """處理使用者上傳的圖片，辨識食材並回傳結構化結果"""
    client = get_client()
    if client is None:
        return {
            "response": "⚠️ 尚未設定 Gemini API Key。",
            "action": "none",
            "ingredients": [],
            "execution_log": [],
        }

    categories_str = "、".join(CATEGORIES)
    prompt = f"""你是 AI 冰箱管家。請辨識圖片中的食材並回應。
使用者偏好：{preferences if preferences else "無"}

以 JSON 回傳：
{{
  "response": "告訴使用者你辨識到了什麼食材（繁體中文、友善）",
  "action": "add_ingredient",
  "ingredients": [{{"name":"xx","quantity":1,"unit":"個","category":"蔬菜"}}]，category 必須是 {categories_str} 之一,
  "execution_log": [
    {{"type": "thought", "content": "分析圖片中的食材"}},
    {{"type": "tool", "content": "呼叫食材辨識工具"}},
    {{"type": "tool_result", "content": "辨識結果"}}
  ]
}}
只回傳 JSON。"""

    try:
        from google.genai import types
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=[image, prompt],
            config=types.GenerateContentConfig(response_mime_type="application/json"),
        )
        result = json.loads(response.text)
        result.setdefault("response", "已辨識食材。")
        result.setdefault("action", "add_ingredient")
        result.setdefault("ingredients", [])
        result.setdefault("execution_log", [])
        return result
    except Exception as e:
        return {
            "response": f"圖片辨識失敗：{e}",
            "action": "none",
            "ingredients": [],
            "execution_log": [{"type": "thought", "content": f"錯誤：{e}"}],
        }
