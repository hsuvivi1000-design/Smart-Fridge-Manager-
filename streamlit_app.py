"""Smart Fridge Manager Streamlit interface."""

from __future__ import annotations

import html
import io
import json
from datetime import date, datetime, timedelta
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
        "budget_status": "正常",
        "chat_input": "",
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


def queue_chat_input() -> None:
    message = st.session_state.get("chat_input", "").strip()
    if not message:
        return
    st.session_state.pending_input = message
    st.session_state.chat_input = ""


def render_shopping_list(items: list[dict[str, Any]]) -> None:
    st.markdown('<div class="section-title">採買清單 <span class="section-note">Shopping Agent</span></div>', unsafe_allow_html=True)
    
    # 預算狀態選擇
    budget = st.selectbox(
        "預算狀態",
        options=["吃緊", "正常", "充裕"],
        index=["吃緊", "正常", "充裕"].index(st.session_state.get("budget_status", "正常")),
        key="budget_selectbox"
    )
    if budget != st.session_state.get("budget_status"):
        st.session_state.budget_status = budget
        st.rerun()

    # 1. 偵測最近一次 AI generate_shopping_list 的結果
    latest_shopping = None
    for log in reversed(st.session_state.execution_log):
        action = log.get("action", {})
        if action.get("tool") == "generate_shopping_list" and log.get("observation"):
            latest_shopping = log["observation"]
            break

    # 如果有 AI 產生的採買清單，我們直接顯示它
    if latest_shopping and isinstance(latest_shopping, dict):
        md_content = latest_shopping.get("shopping_list_md", "")
        st.markdown(md_content)
        st.text_area("複製採買清單 (Markdown)", value=md_content, height=150, key="copy_latest_shopping_list")
    else:
        # 沒有最近的 AI 食譜採買清單，我們動態基於低庫存生成
        low_stock = []
        for item in items:
            mq = item.get("min_quantity", 0.0)
            try:
                mq_val = float(mq)
            except (TypeError, ValueError):
                mq_val = 0.0
            q_val = float(item.get("quantity", 0.0))
            if mq_val > 0.0 and q_val <= mq_val:
                diff_qty = max(0.0, mq_val - q_val)
                suggested_qty = diff_qty if diff_qty > 0 else mq_val
                low_stock.append({
                    "name": item["name"],
                    "quantity": suggested_qty,
                    "unit": item["unit"]
                })

        from tools.shopping_tools import generate_shopping_list
        res = generate_shopping_list(
            missing_ingredients=[],
            low_stock_ingredients=low_stock,
            budget_status=st.session_state.budget_status
        )
        md_content = res.get("shopping_list_md", "")
        st.markdown(md_content)
        if low_stock:
            st.text_area("複製採買清單 (Markdown)", value=md_content, height=150, key="copy_realtime_shopping_list")



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
        '<div class="metric-tile">'
        f'<div class="metric-label">{safe_text(label)}</div>'
        f'<div class="metric-value">{value}</div>'
        "</div>"
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
            '<div class="inventory-item {tone}">'
            '<div class="inventory-main">'
            '<div class="inventory-name">{icon} {name}</div>'
            '<div class="inventory-date">{label}</div>'
            "</div>"
            '<div class="inventory-meta">{category} · {quantity} {unit} · 到期 {expiry}</div>'
            "</div>".format(
                tone=css_tone,
                icon=safe_text(icon),
                name=safe_text(item.get("name", "未命名")),
                label=safe_text(label),
                category=safe_text(category),
                quantity=safe_text(item.get("quantity", 0)),
                unit=safe_text(item.get("unit", "")),
                expiry=safe_text(item.get("expiry_date", "未設定")),
            )
        )

    st.markdown(
        (
            '<div class="panel">'
            f'<div class="section-title">庫存狀態 <span class="section-note">{len(items)} 項</span></div>'
            f'<div class="inventory-list">{"".join(rows)}</div>'
            "</div>"
        ),
        unsafe_allow_html=True,
    )


def process_with_chef_agent(user_message: str, past_messages: list[dict[str, str]] | None = None) -> dict[str, Any]:
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
        chat_history = st.session_state.messages[:-1] if len(st.session_state.messages) > 0 else []
        return agent.run(enhanced_message, chat_history=chat_history)
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
你是 AI 冰箱管家。請辨識圖片中出現的食材或食品本身，並只回傳 JSON。
【重要注意事項】：
1. 僅辨識包裝或食品本身的「主要品名/食材名稱」（例如：鮮奶、牛肉、水餃、泡麵），**絕對禁止**去讀取或拆解外包裝背面或側邊的「成分表/配料表/營養標示細項」（例如：水、食鹽、棕櫚油、食品添加物、大豆沙拉油等）。
2. 如果看到的是包裝好的食品，食材名稱應為該食品的名稱（如「水餃」），而非包裝上的成分原料。
3. **有效期限提取**：請仔細尋找包裝上是否有印製「有效日期」、「到期日」、「有效期限」、「EXP」或「Use By」等日期。如果有，請將該日期提取並寫在 json 的 `expiry_date` 欄位（格式必須是 yyyy-mm-dd，如 2026-06-25）；如果在圖片中找不到任何有效期限，請將其設為 null，不要亂編。

格式：
{{
  "response": "用繁體中文簡短告知辨識結果",
  "ingredients": [{{"name":"食材名稱","quantity":1,"unit":"個","category":"蔬菜","expiry_date":"2026-06-25"}}]
}}
category 必須是以下之一：{categories}
unit 必須是以下之一：{allowed_units}
quantity 必須是數字。若圖片是水果盤或多種食材，請依食材種類拆成多筆；不確定單位時使用「個」。
"""
        fallback_models = [
            "gemini-2.5-flash",
            "gemini-2.5-flash-lite",
            "gemini-3.5-flash",
            "gemini-flash-latest",
            "gemini-1.5-flash",
            "gemini-2.0-flash",
            "gemini-2.0-flash-lite",
            "gemini-2.5-pro"
        ]
        models_to_try = [GEMINI_MODEL] + [m for m in fallback_models if m != GEMINI_MODEL]
        
        response = None
        last_exception = None
        
        for try_model in models_to_try:
            try:
                response = client.models.generate_content(
                    model=try_model,
                    contents=[image, prompt],
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        temperature=0,
                    ),
                )
                break
            except Exception as e:
                last_exception = e
                import sys
                print(f"⚠️ 圖片辨識模型 {try_model} 呼叫失敗。錯誤訊息: {e}。嘗試下一個備援模型...", file=sys.stderr)
        
        if response is None:
            raise last_exception
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

        # 如果 Vision 模型有成功識別出包裝上的有效日期，且格式正確，我們直接採用它
        expiry_date = item.get("expiry_date")
        is_valid_date = False
        if expiry_date:
            try:
                # 驗證日期格式是否為 yyyy-mm-dd
                datetime.strptime(expiry_date, "%Y-%m-%d")
                is_valid_date = True
            except (ValueError, TypeError):
                is_valid_date = False

        if not is_valid_date:
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
            '<div class="log-step">'
            f'<div class="log-thought">thought · {thought or "無"}</div>'
            f'<div class="log-tool">tool · {tool_name or "none"}({args})</div>'
            f'<div class="log-observation">result · {observation or "無"}</div>'
            "</div>"
        )
    return f'<div class="log-panel">{"".join(steps)}</div>'


def handle_pending_events() -> None:
    if st.session_state.pending_input:
        user_msg = st.session_state.pending_input
        st.session_state.pending_input = None
        st.session_state.messages.append({"role": "user", "content": user_msg})

        # 傳遞扣除目前剛加入的 user_msg 之前的歷史紀錄給 ChefAgent
        past = st.session_state.messages[:-1]
        result = process_with_chef_agent(user_msg, past_messages=past)
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

def render_expiry_panel(items: list[dict[str, Any]]) -> None:
    """Render a panel showing items sorted by urgency of expiry.
    Uses check_expiry from tools.shopping_tools.
    """
    from tools.shopping_tools import check_expiry
    st.markdown('<div class="section-title">效期檢查 <span class="section-note">Expiry Agent</span></div>', unsafe_allow_html=True)
    expired_items = [
        item
        for item in items
        if (parse_expiry(item.get("expiry_date")) is not None and parse_expiry(item.get("expiry_date")) < 0)
    ]
    if expired_items:
        expired_names = "、".join(safe_text(item.get("name", "未命名")) for item in expired_items[:3])
        more = f"等 {len(expired_items)} 項" if len(expired_items) > 3 else ""
        st.warning(f"偵測到過期食材：{expired_names}{more}")
        if st.button(
            f"刪除 {len(expired_items)} 項過期食材",
            use_container_width=True,
            key="delete_expired_items",
        ):
            deleted_names = []
            for item in expired_items:
                inventory_agent.delete_ingredient(item["id"])
                deleted_names.append(item.get("name", "未命名"))
            st.session_state.execution_log = [
                {
                    "thought": "Remove expired ingredients from inventory.",
                    "action": {
                        "tool": "InventoryAgent.delete_ingredient",
                        "args": {"expired_item_ids": [item["id"] for item in expired_items]},
                    },
                    "observation": {"deleted": deleted_names},
                }
            ]
            st.success(f"已刪除 {len(deleted_names)} 項過期食材。")
            st.rerun()

    # Run expiry check
    expiry_results = check_expiry(items)
    # Build markdown list
    md_lines = []
    for r in expiry_results:
        name = r.get("name", "未知")
        qty = r.get("quantity", 0)
        unit = r.get("unit", "")
        days = r.get("days_left")
        status = r.get("status", "未知")
        # Show days left if available
        if days is None:
            day_info = ""
        elif days < 0:
            day_info = f"（過期 {abs(days)} 天）"
        else:
            day_info = f"（剩 {days} 天）"
        md_lines.append(f"- {name} {qty}{unit} {status}{day_info}")
    if md_lines:
        st.markdown("\n".join(md_lines))
    else:
        st.markdown("✅ 沒有食材需要注意效期。")

left_col, center_col, right_col = st.columns([1.05, 2.15, 1.15], gap="large")

with left_col:
    render_inventory(ingredients)


    with st.expander("快速入庫", expanded=not ingredients):
        with st.form("quick_add_form", clear_on_submit=True):
            name = st.text_input("食材名稱", placeholder="高麗菜")
            c1, c2 = st.columns([1, 1])
            with c1:
                cat_options = ["🤖 自動判斷"] + CATEGORIES
                selected_category = st.selectbox("分類", cat_options)
                quantity = st.number_input("數量", min_value=0.0, value=1.0, step=0.5)
            with c2:
                unit = st.selectbox("單位", UNITS)
                storage_method = st.selectbox("保存方式", STORAGE_METHODS)
            
            c3, c4 = st.columns([1, 1])
            with c3:
                use_custom_min = st.checkbox("自訂安全水位", value=False, help="未勾選時，將自動依據單位套用智慧安全存量（如：克為 100g，個為 1個）")
            with c4:
                min_quantity_val = st.number_input("安全存量臨界值", min_value=0.0, value=0.0, step=0.5)
                
            c_date1, c_date2 = st.columns([1, 1])
            with c_date1:
                expiry_mode = st.radio(
                    "效期設定方式",
                    options=["AI 自動估算", "手動指定日期"],
                    horizontal=True,
                    help="AI 自動估算將依據食材名稱與保存方式自動估計保存期限；手動指定則可自訂到期日。"
                )
            with c_date2:
                custom_expiry_date = st.date_input(
                    "手動到期日",
                    value=date.today() + timedelta(days=7),
                    min_value=date.today(),
                    help="僅在選擇「手動指定日期」時有效。"
                )

            submitted = st.form_submit_button("加入庫存", type="primary", use_container_width=True)

        if submitted:
            cleaned_name = name.strip()
            if not cleaned_name:
                st.warning("請輸入食材名稱。")
            else:
                today = date.today().strftime("%Y-%m-%d")
                if expiry_mode == "手動指定日期":
                    expiry_date = custom_expiry_date.strftime("%Y-%m-%d")
                    shelf_days = (custom_expiry_date - date.today()).days
                    sub_category = "手動指定"
                else:
                    expiry_date, sub_category, shelf_days = estimate_expiry_date(
                        name=cleaned_name,
                        category=category,
                        purchase_date=today,
                        storage_method=storage_method,
                    )
                min_qty = min_quantity_val if use_custom_min else None
                inventory_agent.add_ingredient(
                    name=cleaned_name,
                    category=final_category,
                    quantity=quantity,
                    unit=unit,
                    purchase_date=today,
                    expiry_date=expiry_date,
                    min_quantity=min_qty
                )
                st.success(f"{cleaned_name} 已入庫，預估保存 {shelf_days} 天。")
                st.session_state.execution_log = [
                    {
                        "thought": "Quick add ingredient from UI.",
                        "action": {
                            "tool": "InventoryAgent.add_ingredient",
                            "args": {
                                "name": cleaned_name,
                                "category": final_category,
                                "sub_category": sub_category,
                                "storage_method": storage_method,
                                "min_quantity": min_qty,
                            },
                        },
                        "observation": {"expiry_date": expiry_date, "shelf_days": shelf_days},
                    }
                ]
                st.rerun()

    with st.expander("管理與編輯庫存"):
        if not ingredients:
            st.markdown('<div class="empty-state">目前冰箱無食材。</div>', unsafe_allow_html=True)
        else:
            item_options = {
                item["id"]: f"{item['name']} (目前: {item['quantity']}{item['unit']}, 安全值: {item.get('min_quantity', 0.0)})"
                for item in ingredients
            }
            selected_id = st.selectbox(
                "選擇要編輯的食材",
                options=list(item_options.keys()),
                format_func=lambda x: item_options[x],
                key="edit_select_box"
            )
            
            selected_item = next(item for item in ingredients if item["id"] == selected_id)
            
            edit_qty = st.number_input(
                f"調整數量 ({selected_item['unit']})",
                min_value=0.0,
                value=float(selected_item["quantity"]),
                step=0.1 if selected_item['unit'] in ["克", "毫克", "毫升", "公斤", "公升"] else 1.0,
                key=f"qty_input_{selected_id}"
            )
            
            edit_min_qty = st.number_input(
                f"安全存量臨界值 ({selected_item['unit']})",
                min_value=0.0,
                value=float(selected_item.get("min_quantity", 0.0)),
                step=1.0,
                key=f"min_input_{selected_id}",
                help="設定為 0.0 可停用此食材的安全水位警示。"
            )

            # 讀取當前有效日期作為預設值
            curr_expiry_str = selected_item.get("expiry_date", "")
            try:
                curr_expiry_val = datetime.strptime(curr_expiry_str, "%Y-%m-%d").date()
            except (ValueError, TypeError):
                curr_expiry_val = date.today()

            edit_expiry = st.date_input(
                "調整有效日期",
                value=curr_expiry_val,
                min_value=date.today() - timedelta(days=365),  # 允許輸入過期日期以編輯已過期食材
                key=f"expiry_input_{selected_id}"
            )
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("更新設定", type="primary", use_container_width=True, key=f"btn_up_{selected_id}"):
                    inventory_agent.update_quantity(selected_id, edit_qty)
                    inventory_agent.update_min_quantity(selected_id, edit_min_qty)
                    inventory_agent.update_expiry_date(selected_id, edit_expiry.strftime("%Y-%m-%d"))
                    st.success(f"已更新 {selected_item['name']} 設定！")
                    st.rerun()
            with col2:
                if st.button("刪除食材", type="secondary", use_container_width=True, key=f"btn_del_{selected_id}"):
                    inventory_agent.delete_ingredient(selected_id)
                    st.success(f"已將 {selected_item['name']} 移出庫存！")
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
        st.text_input(
            "輸入訊息",
            placeholder="例如：我有雞胸肉和高麗菜，今晚煮什麼？",
            label_visibility="collapsed",
            key="chat_input",
            on_change=queue_chat_input,
        )

    with send_col:
        if st.button("發送", type="primary", use_container_width=True):
            queue_chat_input()
            st.rerun()

with right_col:
    render_expiry_panel(ingredients)
    st.markdown("")
    st.markdown(
        '<div class="section-title">執行紀錄 <span class="section-note">Tool trace</span></div>',
        unsafe_allow_html=True,
    )
    st.markdown(render_chef_logs(st.session_state.execution_log), unsafe_allow_html=True)
