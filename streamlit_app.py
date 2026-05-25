"""
AI 冰箱大管家 — 三欄式聊天介面
整合 main 分支的 ChefAgent 框架 + D1257081 分支的 Streamlit UI
"""
import streamlit as st
from datetime import datetime, date, timedelta
from PIL import Image
import io
import json
import os

from app.database import init_db
from app.inventory_agent import InventoryAgent
from app.classifier import classify_ingredient
from ui.config import CATEGORY_ICONS, SHELF_LIFE_DAYS, GEMINI_API_KEY, GEMINI_MODEL, CATEGORIES
from ui.styles import inject_theme_css

# --- Page config ---
st.set_page_config(
    page_title="AI 冰箱大管家",
    page_icon="🧊",
    layout="wide",
    initial_sidebar_state="collapsed",
)
init_db()

# --- 初始化 InventoryAgent ---
@st.cache_resource
def get_inventory_agent():
    return InventoryAgent()

inventory_agent = get_inventory_agent()

# --- Session state ---
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "你好！我是你的 AI 冰箱管家 🧊 今天採買了什麼嗎？"}
    ]
if "execution_log" not in st.session_state:
    st.session_state.execution_log = []
if "dark_mode" not in st.session_state:
    st.session_state.dark_mode = False
if "preferences" not in st.session_state:
    st.session_state.preferences = ""
if "pending_input" not in st.session_state:
    st.session_state.pending_input = None
if "pending_image" not in st.session_state:
    st.session_state.pending_image = None

# --- Inject CSS ---
inject_theme_css(st.session_state.dark_mode)


# --- Helper: 透過 ChefAgent 處理使用者輸入 ---
def process_with_chef_agent(user_message: str):
    """使用 ChefAgent Function Calling 框架處理使用者訊息"""
    if not GEMINI_API_KEY or GEMINI_API_KEY == "your_gemini_api_key_here":
        return {
            "response": "⚠️ 尚未設定 Gemini API Key，請在 .env 中填入 GEMINI_API_KEY。",
            "logs": [{"thought": "偵測到 API Key 尚未設定。", "action": {"tool": "none", "args": {}}, "observation": None}]
        }

    try:
        from agents.chef_planner import ChefAgent

        # 在 user_message 中附加偏好資訊
        enhanced_message = user_message
        if st.session_state.preferences:
            enhanced_message += f"\n（使用者飲食偏好：{st.session_state.preferences}）"

        agent = ChefAgent(api_key=GEMINI_API_KEY, model=GEMINI_MODEL)
        result = agent.run(enhanced_message)
        return result
    except Exception as e:
        return {
            "response": f"處理時發生錯誤：{e}",
            "logs": [{"thought": f"錯誤：{e}", "action": {"tool": "error", "args": {}}, "observation": None}]
        }


# --- Helper: 透過 Gemini Vision 辨識圖片食材 ---
def process_image_with_gemini(image):
    """使用 Gemini Vision 辨識圖片中的食材"""
    if not GEMINI_API_KEY or GEMINI_API_KEY == "your_gemini_api_key_here":
        return {
            "response": "⚠️ 尚未設定 Gemini API Key。",
            "ingredients": [],
            "logs": []
        }

    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=GEMINI_API_KEY)
        categories_str = "、".join(CATEGORIES)

        prompt = f"""你是 AI 冰箱管家。請辨識圖片中的食材並回應。
以 JSON 回傳：
{{
  "response": "告訴使用者你辨識到了什麼食材（繁體中文、友善）",
  "ingredients": [{{"name":"xx","quantity":1,"unit":"個","category":"蔬菜"}}]，category 必須是 {categories_str} 之一
}}
只回傳 JSON。"""

        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=[image, prompt],
            config=types.GenerateContentConfig(response_mime_type="application/json"),
        )
        result = json.loads(response.text)
        result.setdefault("response", "已辨識食材。")
        result.setdefault("ingredients", [])
        return result
    except Exception as e:
        return {
            "response": f"圖片辨識失敗：{e}",
            "ingredients": [],
        }


# --- Helper: 將辨識到的食材入庫 ---
def save_ingredients_to_db(items):
    """將辨識到的食材存入資料庫"""
    today_str = date.today().strftime("%Y-%m-%d")
    count = 0
    for item in items:
        name = item.get("name", "").strip()
        if not name:
            continue
        category = item.get("category", "其他")
        if category not in CATEGORIES:
            category = classify_ingredient(name)
        shelf = SHELF_LIFE_DAYS.get(category, 7)
        expiry = (date.today() + timedelta(days=shelf)).strftime("%Y-%m-%d")
        try:
            inventory_agent.add_ingredient(
                name=name,
                category=category,
                quantity=float(item.get("quantity", 1)),
                unit=item.get("unit", "個"),
                purchase_date=today_str,
                expiry_date=expiry,
            )
            count += 1
        except Exception as e:
            st.warning(f"食材「{name}」入庫失敗：{e}")
    return count


# --- Helper: 渲染 ChefAgent 執行日誌 ---
def render_chef_logs(logs):
    """將 ChefAgent 的 Thought/Action/Observation logs 渲染為 HTML"""
    html = '<div class="log-panel">'

    if not logs:
        html += '<div class="log-indent">等待使用者輸入...</div>'
        html += '</div>'
        return html

    for i, entry in enumerate(logs, 1):
        html += f'<div class="log-step">'

        # Thought
        thought = entry.get("thought", "")
        if thought:
            # 截斷過長的思考內容
            display_thought = thought[:200] + "..." if len(thought) > 200 else thought
            html += f'<div class="log-thought">[Thought] {display_thought}</div>'

        # Action
        action = entry.get("action", {})
        tool_name = action.get("tool", "")
        tool_args = action.get("args", {})
        if tool_name:
            args_str = ", ".join(f"{k}={v}" for k, v in tool_args.items()) if tool_args else ""
            # 截斷過長的參數
            if len(args_str) > 150:
                args_str = args_str[:150] + "..."
            html += f'<div class="log-tool">[Call Tool] {tool_name}({args_str})</div>'

        # Observation
        observation = entry.get("observation")
        if observation is not None:
            obs_str = str(observation)
            if len(obs_str) > 200:
                obs_str = obs_str[:200] + "..."
            html += f'<div class="log-observation">> {obs_str}</div>'

        html += '</div>'

    html += '</div>'
    return html


# --- Process pending input ---
if st.session_state.pending_input:
    user_msg = st.session_state.pending_input
    st.session_state.pending_input = None
    st.session_state.messages.append({"role": "user", "content": user_msg})

    # 使用 ChefAgent 處理
    result = process_with_chef_agent(user_msg)

    st.session_state.messages.append({"role": "assistant", "content": result["response"]})
    st.session_state.execution_log = result.get("logs", [])

if st.session_state.pending_image is not None:
    image = st.session_state.pending_image
    st.session_state.pending_image = None
    st.session_state.messages.append({"role": "user", "content": "📷 [已上傳食材照片]"})

    # 使用 Gemini Vision 辨識
    result = process_image_with_gemini(image)

    st.session_state.messages.append({"role": "assistant", "content": result["response"]})

    # 辨識到的食材自動入庫
    if result.get("ingredients"):
        count = save_ingredients_to_db(result["ingredients"])
        if count > 0:
            st.session_state.messages.append(
                {"role": "assistant", "content": f"✅ 已成功將 {count} 項食材入庫！"}
            )

    st.session_state.execution_log = [
        {"thought": "分析使用者上傳的食材圖片", "action": {"tool": "Gemini Vision", "args": {}}, "observation": result.get("ingredients", [])}
    ]


# ============================================================
# LAYOUT: Three columns
# ============================================================
left_col, center_col, right_col = st.columns([1, 2.5, 1.5])

# ======================== LEFT: 庫存管理 ========================
with left_col:
    st.markdown(
        '<div class="panel-header">庫存管理 <span style="float:right;">Agent 狀態 🟢</span></div>',
        unsafe_allow_html=True,
    )

    ingredients = inventory_agent.get_all_inventory()
    today = datetime.now().date()

    if ingredients:
        for item in ingredients:
            try:
                expiry = datetime.strptime(item["expiry_date"], "%Y-%m-%d").date()
                days_left = (expiry - today).days
            except (ValueError, TypeError):
                days_left = 999

            if days_left <= 2:
                border_color = "#E74C3C"
            elif days_left <= 5:
                border_color = "#F39C12"
            else:
                border_color = "#27AE60"

            cat_icon = CATEGORY_ICONS.get(item.get("category", ""), "📦")

            st.markdown(
                f"""<div class="inventory-item" style="border-left: 4px solid {border_color};">
                    <strong>{cat_icon} {item['name']}</strong> (剩餘 {max(days_left, 0)} 天)<br>
                    <span class="item-category">分類: {item.get('category', '其他')} ｜ {item['quantity']} {item['unit']}</span>
                </div>""",
                unsafe_allow_html=True,
            )
    else:
        st.caption("目前冰箱沒有食材 🫙")

    # Preferences
    st.markdown('<hr class="divider">', unsafe_allow_html=True)
    with st.expander("⚙️ 飲食偏好"):
        pref = st.text_area(
            "偏好", value=st.session_state.preferences,
            placeholder="不吃辣、素食、低鹽...",
            label_visibility="collapsed", height=70,
        )
        if pref != st.session_state.preferences:
            st.session_state.preferences = pref

    # Theme toggle
    st.markdown('<hr class="divider">', unsafe_allow_html=True)
    toggle_label = "☀️ 切換淺色模式" if st.session_state.dark_mode else "🌙 切換深色模式"
    if st.button(toggle_label, use_container_width=True, key="theme_toggle"):
        st.session_state.dark_mode = not st.session_state.dark_mode
        st.rerun()

# ======================== CENTER: 聊天介面 ========================
with center_col:
    # Chat messages in scrollable container
    chat_container = st.container(height=480)
    with chat_container:
        for msg in st.session_state.messages:
            if msg["role"] == "assistant":
                st.markdown(
                    f'<div class="chat-bubble assistant-bubble">{msg["content"]}</div>',
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    f'<div class="chat-bubble user-bubble">{msg["content"]}</div>',
                    unsafe_allow_html=True,
                )

    # Input area
    in1, in2, in3 = st.columns([0.6, 5, 0.8])
    with in1:
        with st.popover("📷", use_container_width=True):
            st.markdown("##### 上傳食材照片")
            uploaded = st.file_uploader("選擇圖片", type=["jpg", "jpeg", "png", "webp"], label_visibility="collapsed")
            cam = st.camera_input("或拍照", label_visibility="collapsed")
            photo = cam if cam else uploaded
            if photo and st.button("🔍 辨識食材", type="primary", use_container_width=True):
                img = Image.open(io.BytesIO(photo.getvalue()))
                st.session_state.pending_image = img
                st.rerun()
    with in2:
        user_input = st.text_input(
            "msg", placeholder="請輸入指令或食材... (例如：我買了高麗菜和豬肉 / 今晚吃什麼？)",
            label_visibility="collapsed", key="chat_input",
        )
    with in3:
        if st.button("發送", use_container_width=True, type="primary", key="send_btn"):
            if user_input.strip():
                st.session_state.pending_input = user_input.strip()
                st.rerun()

# ======================== RIGHT: 執行日誌 ========================
with right_col:
    st.markdown(
        '<div class="panel-header" style="color: #C9D1D9;">System Execution Log</div>',
        unsafe_allow_html=True,
    )

    # 渲染 ChefAgent 決策歷程
    log_html = render_chef_logs(st.session_state.execution_log)
    st.markdown(log_html, unsafe_allow_html=True)
