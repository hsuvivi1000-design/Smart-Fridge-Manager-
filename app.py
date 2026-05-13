"""
AI 冰箱大管家 — 三欄式聊天介面
"""
import streamlit as st
from datetime import datetime, date, timedelta
from PIL import Image
import io

from utils.database import init_db, get_all_ingredients, add_ingredient
from utils.gemini_client import get_client, process_chat_input, process_image_input
from utils.config import CATEGORY_ICONS, SHELF_LIFE_DAYS
from utils.styles import inject_theme_css

# --- Page config ---
st.set_page_config(
    page_title="AI 冰箱大管家",
    page_icon="🧊",
    layout="wide",
    initial_sidebar_state="collapsed",
)
init_db()

# --- Session state ---
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "你好！我是你的 AI 冰箱管家。今天採買了什麼嗎？"}
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

# --- Helper: add identified ingredients to DB ---
def save_ingredients(items):
    today_str = date.today().strftime("%Y-%m-%d")
    count = 0
    for item in items:
        name = item.get("name", "").strip()
        if not name:
            continue
        category = item.get("category", "其他")
        shelf = SHELF_LIFE_DAYS.get(category, 7)
        expiry = (date.today() + timedelta(days=shelf)).strftime("%Y-%m-%d")
        add_ingredient(
            name=name,
            quantity=float(item.get("quantity", 1)),
            unit=item.get("unit", "個"),
            category=category,
            purchase_date=today_str,
            expiry_date=expiry,
        )
        count += 1
    return count

# --- Helper: render execution log ---
def render_log_entry(entry):
    t = entry.get("type", "thought")
    c = entry.get("content", "")
    css_map = {
        "thought": "log-thought",
        "tool": "log-tool",
        "tool_result": "log-indent",
        "memory": "log-memory",
        "rag": "log-rag",
    }
    label_map = {
        "thought": "[Thought]",
        "tool": "[Call Tool]",
        "tool_result": ">",
        "memory": "[Memory]",
        "rag": "[RAG]",
    }
    css = css_map.get(t, "log-indent")
    label = label_map.get(t, "")
    return f'<div class="{css}">{label} {c}</div>'

# --- Process pending input ---
if st.session_state.pending_input:
    user_msg = st.session_state.pending_input
    st.session_state.pending_input = None
    st.session_state.messages.append({"role": "user", "content": user_msg})

    ingredients = get_all_ingredients()
    result = process_chat_input(user_msg, ingredients, st.session_state.preferences)

    st.session_state.messages.append({"role": "assistant", "content": result["response"]})
    st.session_state.execution_log = result.get("execution_log", [])

    if result.get("action") == "add_ingredient" and result.get("ingredients"):
        save_ingredients(result["ingredients"])

if st.session_state.pending_image is not None:
    image = st.session_state.pending_image
    st.session_state.pending_image = None
    st.session_state.messages.append({"role": "user", "content": "📷 [已上傳食材照片]"})

    result = process_image_input(image, st.session_state.preferences)

    st.session_state.messages.append({"role": "assistant", "content": result["response"]})
    st.session_state.execution_log = result.get("execution_log", [])

    if result.get("action") == "add_ingredient" and result.get("ingredients"):
        save_ingredients(result["ingredients"])

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

    ingredients = get_all_ingredients()
    today = datetime.now().date()

    if ingredients:
        for item in ingredients:
            expiry = datetime.strptime(item["expiry_date"], "%Y-%m-%d").date()
            days_left = (expiry - today).days
            if days_left <= 2:
                border_color = "#E74C3C"
            elif days_left <= 5:
                border_color = "#F39C12"
            else:
                border_color = "#27AE60"

            st.markdown(
                f"""<div class="inventory-item" style="border-left: 4px solid {border_color};">
                    <strong>{item['name']}</strong> (剩餘 {max(days_left, 0)} 天)<br>
                    <span class="item-category">分類: {item['category']}</span>
                </div>""",
                unsafe_allow_html=True,
            )
    else:
        st.caption("目前冰箱沒有食材")

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
            "msg", placeholder="請輸入指令或食材...",
            label_visibility="collapsed", key="chat_input",
        )
    with in3:
        if st.button("發送", use_container_width=True, type="primary", key="send_btn"):
            if user_input.strip():
                st.session_state.pending_input = user_input.strip()
                st.rerun()

    # Also allow Enter key submission
    if user_input and user_input.strip():
        # Check if this is a new submission (not already processed)
        last_user_msgs = [m for m in st.session_state.messages if m["role"] == "user"]
        if not last_user_msgs or last_user_msgs[-1]["content"] != user_input.strip():
            pass  # Will be sent via button click

# ======================== RIGHT: 執行日誌 ========================
with right_col:
    st.markdown(
        '<div class="panel-header" style="color: #C9D1D9;">System Execution Log</div>',
        unsafe_allow_html=True,
    )

    log_html = '<div class="log-panel">'
    if st.session_state.execution_log:
        for entry in st.session_state.execution_log:
            log_html += render_log_entry(entry)
    else:
        log_html += '<div class="log-indent">等待使用者輸入...</div>'
    log_html += "</div>"
    st.markdown(log_html, unsafe_allow_html=True)
