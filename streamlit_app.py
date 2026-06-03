"""Smart Fridge Manager Streamlit interface."""

from __future__ import annotations

import html
import io
import json
from datetime import date, datetime
from typing import Any

import streamlit as st
from PIL import Image

from app.classifier import classify_ingredient
from app.database import init_db
from app.expiry_agent import estimate_expiry_date
from app.inventory_agent import InventoryAgent
from ui.config import (
    CATEGORIES,
    CATEGORY_ICONS,
    DEFAULT_UNIT,
    GEMINI_API_KEY,
    GEMINI_MODEL,
    STORAGE_METHODS,
    UNIT_ALIASES,
    UNITS,
)
from ui.styles import inject_theme_css


st.set_page_config(
    page_title="AI 冰箱管家",
    page_icon="🧊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

init_db()


@st.cache_resource
def get_inventory_agent() -> InventoryAgent:
    return InventoryAgent()


inventory_agent = get_inventory_agent()


def init_session_state() -> None:
    defaults = {
        "messages": [
            {
                "role": "assistant",
                "content": "冰箱已就緒。你可以告訴我剛買了什麼，或直接問今晚適合煮什麼。",
            }
        ],
        "execution_log": [],
        "dark_mode": False,
        "preferences": "",
        "pending_input": None,
        "pending_image": None,
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


def safe_text(value: Any) -> str:
    return html.escape(str(value if value is not None else ""))


def parse_expiry(expiry_date: str | None) -> int | None:
    if not expiry_date:
        return None
    try:
        expiry = datetime.strptime(expiry_date, "%Y-%m-%d").date()
        return (expiry - date.today()).days
    except (TypeError, ValueError):
        return None


def expiry_tone(days_left: int | None) -> tuple[str, str]:
    if days_left is None:
        return "warning", "日期待確認"
    if days_left < 0:
        return "danger", "已過期"
    if days_left == 0:
        return "danger", "今天到期"
    if days_left <= 2:
        return "danger", f"剩 {days_left} 天"
    if days_left <= 5:
        return "warning", f"剩 {days_left} 天"
    return "fresh", f"剩 {days_left} 天"


def summarize_inventory(items: list[dict[str, Any]]) -> dict[str, int]:
    urgent = 0
    expired = 0
    fresh = 0
    for item in items:
        days_left = parse_expiry(item.get("expiry_date"))
        if days_left is None:
            continue
        if days_left < 0:
            expired += 1
        elif days_left <= 2:
            urgent += 1
        else:
            fresh += 1
    return {
        "total": len(items),
        "urgent": urgent,
        "expired": expired,
        "fresh": fresh,
    }


def render_metrics(summary: dict[str, int]) -> None:
    metrics = [
        ("庫存項目", summary["total"]),
        ("兩天內到期", summary["urgent"]),
        ("已過期", summary["expired"]),
        ("狀態正常", summary["fresh"]),
    ]
    tiles = "".join(
        f"""
        <div class="metric-tile">
            <div class="metric-label">{safe_text(label)}</div>
            <div class="metric-value">{value}</div>
        </div>
        """
        for label, value in metrics
    )
    st.markdown(f'<div class="metric-row">{tiles}</div>', unsafe_allow_html=True)


def render_inventory(items: list[dict[str, Any]]) -> None:
    if not items:
        st.markdown(
            """
            <div class="panel">
                <div class="section-title">庫存狀態 <span class="section-note">0 項</span></div>
                <div class="empty-state">目前沒有食材資料。</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    rows = []
    for item in sorted(items, key=lambda x: parse_expiry(x.get("expiry_date")) or 9999):
        days_left = parse_expiry(item.get("expiry_date"))
        tone, label = expiry_tone(days_left)
        category = item.get("category") or "其他"
        icon = CATEGORY_ICONS.get(category, CATEGORY_ICONS["其他"])
        css_tone = "danger" if tone == "danger" else "warning" if tone == "warning" else ""
        rows.append(
            f"""
            <div class="inventory-item {css_tone}">
                <div class="inventory-main">
                    <div class="inventory-name">{safe_text(icon)} {safe_text(item.get("name", "未命名"))}</div>
                    <div class="inventory-date">{safe_text(label)}</div>
                </div>
                <div class="inventory-meta">
                    {safe_text(category)} · {safe_text(item.get("quantity", 0))} {safe_text(item.get("unit", ""))}
                    · 到期 {safe_text(item.get("expiry_date", "未設定"))}
                </div>
            </div>
            """
        )

    st.markdown(
        f"""
        <div class="panel">
            <div class="section-title">庫存狀態 <span class="section-note">{len(items)} 項</span></div>
            <div class="inventory-list">{''.join(rows)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def process_with_chef_agent(user_message: str) -> dict[str, Any]:
    if not GEMINI_API_KEY:
        return {
            "response": "尚未設定 Gemini API Key。庫存與快速入庫可照常使用；AI 對話需要在 .env 設定 GEMINI_API_KEY。",
            "logs": [
                {
                    "thought": "Gemini API Key is missing.",
                    "action": {"tool": "none", "args": {}},
                    "observation": None,
                }
            ],
        }

    try:
        from agents.chef_planner import ChefAgent

        enhanced_message = user_message
        if st.session_state.preferences:
            enhanced_message += f"\n使用者飲食偏好：{st.session_state.preferences}"

        agent = ChefAgent(api_key=GEMINI_API_KEY, model=GEMINI_MODEL)
        return agent.run(enhanced_message)
    except Exception as exc:
        return {
            "response": f"處理時發生錯誤：{exc}",
            "logs": [
                {
                    "thought": f"Exception: {exc}",
                    "action": {"tool": "error", "args": {}},
                    "observation": None,
                }
            ],
        }


def process_image_with_gemini(image: Image.Image) -> dict[str, Any]:
    if not GEMINI_API_KEY:
        return {
            "response": "尚未設定 Gemini API Key，無法辨識圖片。",
            "ingredients": [],
            "logs": [],
        }

    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=GEMINI_API_KEY)
        categories = "、".join(CATEGORIES)
        allowed_units = "、".join(UNITS)
        prompt = f"""
你是 AI 冰箱管家。請辨識圖片中的食材，只回傳 JSON。
格式：
{{
  "response": "用繁體中文簡短告知辨識結果",
  "ingredients": [{{"name":"食材名稱","quantity":1,"unit":"個","category":"蔬菜"}}]
}}
category 必須是以下之一：{categories}
unit 必須是以下之一：{allowed_units}
quantity 必須是數字。若圖片是水果盤或多種食材，請依食材種類拆成多筆；不確定單位時使用「個」。
"""
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=[image, prompt],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0,
            ),
        )
        result = json.loads(response.text)
        result.setdefault("response", "已辨識食材。")
        result.setdefault("ingredients", [])
        return result
    except Exception as exc:
        return {
            "response": f"圖片辨識失敗：{exc}",
            "ingredients": [],
            "logs": [],
        }


def normalize_unit(unit: Any) -> str:
    cleaned = str(unit or "").strip()
    aliased = UNIT_ALIASES.get(cleaned, cleaned)
    return aliased if aliased in UNITS else DEFAULT_UNIT


def parse_quantity(quantity: Any) -> float:
    try:
        parsed = float(quantity)
    except (TypeError, ValueError):
        return 1.0
    return parsed if parsed > 0 else 1.0


def save_ingredients_to_db(items: list[dict[str, Any]]) -> dict[str, Any]:
    today = date.today().strftime("%Y-%m-%d")
    saved = 0
    skipped = []
    for item in items:
        name = str(item.get("name", "")).strip()
        if not name:
            continue
        category = item.get("category") or classify_ingredient(name)
        if category not in CATEGORIES:
            category = classify_ingredient(name)

        expiry_date, _sub_category, _shelf_days = estimate_expiry_date(
            name=name,
            category=category,
            purchase_date=today,
            storage_method="冷藏",
        )

        try:
            inventory_agent.add_ingredient(
                name=name,
                category=category,
                quantity=parse_quantity(item.get("quantity", 1)),
                unit=normalize_unit(item.get("unit")),
                purchase_date=today,
                expiry_date=expiry_date,
            )
            saved += 1
        except Exception as exc:
            skipped.append({"name": name, "reason": str(exc)})
    return {"saved": saved, "skipped": skipped}


def render_chef_logs(logs: list[dict[str, Any]]) -> str:
    if not logs:
        return '<div class="log-panel"><div class="log-indent">等待下一次任務。</div></div>'

    steps = []
    for entry in logs:
        thought = safe_text(entry.get("thought", ""))
        action = entry.get("action", {}) or {}
        tool_name = safe_text(action.get("tool", ""))
        args = safe_text(action.get("args", {}))
        observation = safe_text(entry.get("observation", ""))
        if len(thought) > 220:
            thought = thought[:220] + "..."
        if len(args) > 180:
            args = args[:180] + "..."
        if len(observation) > 240:
            observation = observation[:240] + "..."

        steps.append(
            f"""
            <div class="log-step">
                <div class="log-thought">thought · {thought or "無"}</div>
                <div class="log-tool">tool · {tool_name or "none"}({args})</div>
                <div class="log-observation">result · {observation or "無"}</div>
            </div>
            """
        )
    return f'<div class="log-panel">{"".join(steps)}</div>'


def handle_pending_events() -> None:
    if st.session_state.pending_input:
        user_msg = st.session_state.pending_input
        st.session_state.pending_input = None
        st.session_state.messages.append({"role": "user", "content": user_msg})

        result = process_with_chef_agent(user_msg)
        st.session_state.messages.append({"role": "assistant", "content": result["response"]})
        st.session_state.execution_log = result.get("logs", [])

    if st.session_state.pending_image is not None:
        image = st.session_state.pending_image
        st.session_state.pending_image = None
        st.session_state.messages.append({"role": "user", "content": "已上傳食材照片"})

        result = process_image_with_gemini(image)
        st.session_state.messages.append({"role": "assistant", "content": result["response"]})
        if result.get("ingredients"):
            save_result = save_ingredients_to_db(result["ingredients"])
            saved = save_result["saved"]
            skipped = save_result["skipped"]
            st.session_state.messages.append(
                {"role": "assistant", "content": f"已將 {saved} 項食材加入庫存。"}
            )
            if skipped:
                skipped_names = "、".join(item["name"] for item in skipped[:3])
                more = f"等 {len(skipped)} 項" if len(skipped) > 3 else ""
                st.session_state.messages.append(
                    {
                        "role": "assistant",
                        "content": f"有 {len(skipped)} 項食材未能入庫：{skipped_names}{more}。",
                    }
                )
        st.session_state.execution_log = [
            {
                "thought": "Analyze uploaded ingredient image.",
                "action": {"tool": "Gemini Vision", "args": {}},
                "observation": result.get("ingredients", []),
            }
        ]


init_session_state()
inject_theme_css(st.session_state.dark_mode)
handle_pending_events()

ingredients = inventory_agent.get_all_inventory()
summary = summarize_inventory(ingredients)

st.markdown(
    """
    <div class="app-shell">
        <div>
            <h1 class="brand-title">AI 冰箱管家</h1>
            <div class="brand-subtitle">庫存、效期、食譜與採買清單集中管理</div>
        </div>
        <div class="top-status"><span class="status-dot"></span> Local workspace · Streamlit</div>
    </div>
    """,
    unsafe_allow_html=True,
)
render_metrics(summary)

left_col, center_col, right_col = st.columns([1.05, 2.15, 1.15], gap="large")

with left_col:
    render_inventory(ingredients)

    st.markdown("")
    with st.expander("快速入庫", expanded=not ingredients):
        with st.form("quick_add_form", clear_on_submit=True):
            name = st.text_input("食材名稱", placeholder="高麗菜")
            c1, c2 = st.columns([1, 1])
            with c1:
                category = st.selectbox("分類", CATEGORIES)
                quantity = st.number_input("數量", min_value=0.0, value=1.0, step=0.5)
            with c2:
                unit = st.selectbox("單位", UNITS)
                storage_method = st.selectbox("保存方式", STORAGE_METHODS)
            submitted = st.form_submit_button("加入庫存", type="primary", use_container_width=True)

        if submitted:
            cleaned_name = name.strip()
            if not cleaned_name:
                st.warning("請輸入食材名稱。")
            else:
                today = date.today().strftime("%Y-%m-%d")
                expiry_date, sub_category, shelf_days = estimate_expiry_date(
                    name=cleaned_name,
                    category=category,
                    purchase_date=today,
                    storage_method=storage_method,
                )
                inventory_agent.add_ingredient(
                    name=cleaned_name,
                    category=category,
                    quantity=quantity,
                    unit=unit,
                    purchase_date=today,
                    expiry_date=expiry_date,
                )
                st.success(f"{cleaned_name} 已入庫，預估保存 {shelf_days} 天。")
                st.session_state.execution_log = [
                    {
                        "thought": "Quick add ingredient from UI.",
                        "action": {
                            "tool": "InventoryAgent.add_ingredient",
                            "args": {
                                "name": cleaned_name,
                                "category": category,
                                "sub_category": sub_category,
                                "storage_method": storage_method,
                            },
                        },
                        "observation": {"expiry_date": expiry_date, "shelf_days": shelf_days},
                    }
                ]
                st.rerun()

    with st.expander("偏好設定"):
        st.session_state.preferences = st.text_area(
            "飲食偏好",
            value=st.session_state.preferences,
            placeholder="不吃辣、低鹽、偏好雞肉",
            height=86,
        )
        theme_label = "切換淺色模式" if st.session_state.dark_mode else "切換深色模式"
        if st.button(theme_label, use_container_width=True):
            st.session_state.dark_mode = not st.session_state.dark_mode
            st.rerun()

with center_col:
    st.markdown(
        '<div class="section-title">對話工作台 <span class="section-note">AI Chef Agent</span></div>',
        unsafe_allow_html=True,
    )
    st.markdown('<div class="chat-frame">', unsafe_allow_html=True)
    chat_container = st.container(height=510, border=False)
    with chat_container:
        for message in st.session_state.messages:
            role_class = "assistant-bubble" if message["role"] == "assistant" else "user-bubble"
            st.markdown(
                f'<div class="chat-bubble {role_class}">{safe_text(message["content"])}</div>',
                unsafe_allow_html=True,
            )
    st.markdown("</div>", unsafe_allow_html=True)

    upload_col, input_col, send_col = st.columns([0.55, 4.8, 0.9])
    with upload_col:
        with st.popover("相機", use_container_width=True):
            uploaded = st.file_uploader("上傳照片", type=["jpg", "jpeg", "png", "webp"])
            captured = st.camera_input("拍照")
            photo = captured or uploaded
            if photo and st.button("辨識食材", type="primary", use_container_width=True):
                st.session_state.pending_image = Image.open(io.BytesIO(photo.getvalue()))
                st.rerun()

    with input_col:
        user_input = st.text_input(
            "輸入訊息",
            placeholder="例如：我有雞胸肉和高麗菜，今晚煮什麼？",
            label_visibility="collapsed",
            key="chat_input",
        )

    with send_col:
        if st.button("發送", type="primary", use_container_width=True):
            if user_input.strip():
                st.session_state.pending_input = user_input.strip()
                st.rerun()

with right_col:
    st.markdown(
        '<div class="section-title">執行紀錄 <span class="section-note">Tool trace</span></div>',
        unsafe_allow_html=True,
    )
    st.markdown(render_chef_logs(st.session_state.execution_log), unsafe_allow_html=True)
