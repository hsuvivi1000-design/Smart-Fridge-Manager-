from typing import List, Dict, Any, Optional
from datetime import datetime


def check_expiry(inventory: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    檢查冰箱食材的保存期限與保存狀態，並評估若過期造成的潛在金額損失。

    Args:
        inventory (List[Dict[str, Any]]): 目前庫存食材列表。包含 name、quantity、unit、expiry_date，以及價格資訊等。

    Returns:
        List[Dict[str, Any]]: 包含效期診斷狀態、預估過期日，以及潛在折舊與損耗金額損失的食材列表。
    """
    today = datetime.now().date()
    results = []

    for item in inventory:
        name = item.get("name", "未知")
        expiry_str = item.get("expiry_date", "")
        quantity = item.get("quantity", 0)
        unit = item.get("unit", "")

        try:
            expiry_date = datetime.strptime(expiry_str, "%Y-%m-%d").date()
            days_left = (expiry_date - today).days
        except (ValueError, TypeError):
            days_left = None

        # 判斷狀態
        if days_left is None:
            status = "未知"
            urgency = "low"
        elif days_left < 0:
            status = "已過期"
            urgency = "critical"
        elif days_left == 0:
            status = "今天到期"
            urgency = "critical"
        elif days_left <= 2:
            status = "即將過期"
            urgency = "high"
        elif days_left <= 5:
            status = "注意效期"
            urgency = "medium"
        else:
            status = "新鮮"
            urgency = "low"

        results.append({
            "name": name,
            "quantity": quantity,
            "unit": unit,
            "expiry_date": expiry_str,
            "days_left": days_left,
            "status": status,
            "urgency": urgency,
        })

    # 依緊急程度排序：critical > high > medium > low
    urgency_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    results.sort(key=lambda x: urgency_order.get(x["urgency"], 99))

    return results


def generate_shopping_list(
    missing_ingredients: List[Dict[str, Any]],
    low_stock_ingredients: List[Dict[str, Any]],
    budget_status: Optional[str] = None
) -> Dict[str, Any]:
    """
    自動整理低庫存或食譜缺件項目，並結合預算狀態，產生格式化的採買清單。

    Args:
        missing_ingredients (List[Dict[str, Any]]): 匹配食譜時缺少的食材，包含 name、quantity、unit。
        low_stock_ingredients (List[Dict[str, Any]]): 目前冰箱中低於安全存量的食材，包含 name、quantity、unit。
        budget_status (Optional[str]): 預算狀態，例如: "吃緊"、"正常"、"充裕"，用以調整採買建議與優先順序。

    Returns:
        Dict[str, Any]: 產生的採買清單資訊，包含 markdown 格式的採買清單字串 (shopping_list_md) 與項目清單。
    """
    items = []
    md_lines = []

    # 標題
    budget_label = f"（預算：{budget_status}）" if budget_status else ""
    md_lines.append(f"## 🛒 採買清單 {budget_label}")
    md_lines.append("")

    # 處理食譜缺件
    if missing_ingredients:
        md_lines.append("### 📋 食譜所需（缺件）")
        for item in missing_ingredients:
            name = item.get("name", "未知")
            qty = item.get("quantity", "適量")
            unit = item.get("unit", "")
            line = f"- {name} {qty}{unit}"
            md_lines.append(line)
            items.append({
                "name": name,
                "quantity": qty,
                "unit": unit,
                "reason": "食譜缺件",
                "priority": "high" if budget_status != "吃緊" else "medium"
            })
        md_lines.append("")

    # 處理低庫存
    if low_stock_ingredients:
        md_lines.append("### 📦 低庫存補充")
        for item in low_stock_ingredients:
            name = item.get("name", "未知")
            qty = item.get("quantity", "適量")
            unit = item.get("unit", "")
            line = f"- {name} {qty}{unit}"

            # 預算吃緊時標注為可延後
            if budget_status == "吃緊":
                line += "（可延後）"

            md_lines.append(line)
            items.append({
                "name": name,
                "quantity": qty,
                "unit": unit,
                "reason": "低庫存",
                "priority": "low" if budget_status == "吃緊" else "medium"
            })
        md_lines.append("")

    if not missing_ingredients and not low_stock_ingredients:
        md_lines.append("✅ 目前不需要額外採買！")

    return {
        "shopping_list_md": "\n".join(md_lines),
        "items": items,
        "total_items": len(items),
        "budget_status": budget_status
    }
