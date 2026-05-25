from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from app.inventory_agent import InventoryAgent
from app.classifier import classify_ingredient

# 共用 InventoryAgent 實例
_agent = None

def _get_agent():
    global _agent
    if _agent is None:
        _agent = InventoryAgent()
    return _agent


def get_inventory() -> List[Dict[str, Any]]:
    """
    取得冰箱現有的所有食材庫存清單。

    Returns:
        List[Dict[str, Any]]: 庫存食材列表。每個食材包含 name、quantity、unit、purchase_date、expiry_date、category。
    """
    agent = _get_agent()
    inventory = agent.get_all_inventory()
    return inventory if inventory else []


def add_ingredient(
    name: str,
    quantity: float,
    unit: str,
    category: Optional[str] = None,
    purchase_date: Optional[str] = None,
    expiry_date: Optional[str] = None
) -> Dict[str, Any]:
    """
    新增食材到冰箱庫存中。

    Args:
        name (str): 食材名稱，例如: "高麗菜"
        quantity (float): 食材數量，例如: 1.0
        unit (str): 單位，例如: "顆"
        category (Optional[str]): 食材類別，例如: "蔬菜類"
        purchase_date (Optional[str]): 購買日期，格式為 YYYY-MM-DD，預設為今天
        expiry_date (Optional[str]): 預計過期日期，格式為 YYYY-MM-DD

    Returns:
        Dict[str, Any]: 新增成功的食材詳細資料。
    """
    agent = _get_agent()

    # 若未指定類別，透過 AI 分類器自動判斷
    if not category:
        category = classify_ingredient(name)

    # 若未指定購買日期，預設為今天
    if not purchase_date:
        purchase_date = datetime.now().strftime("%Y-%m-%d")

    # 若未指定到期日期，根據分類設定預設保存天數
    if not expiry_date:
        from ui.config import SHELF_LIFE_DAYS
        shelf_days = SHELF_LIFE_DAYS.get(category, 7)
        expiry_date = (datetime.now() + timedelta(days=shelf_days)).strftime("%Y-%m-%d")

    item_id = agent.add_ingredient(
        name=name,
        category=category,
        quantity=quantity,
        unit=unit,
        purchase_date=purchase_date,
        expiry_date=expiry_date
    )

    return {
        "status": "success",
        "id": item_id,
        "name": name,
        "quantity": quantity,
        "unit": unit,
        "category": category,
        "purchase_date": purchase_date,
        "expiry_date": expiry_date
    }


def consume_ingredient(name: str, quantity: float, unit: str) -> Dict[str, Any]:
    """
    從冰箱庫存中消耗/扣除指定數量的食材。

    Args:
        name (str): 要消耗的食材名稱，例如: "高麗菜"
        quantity (float): 消耗數量，例如: 0.5
        unit (str): 單位，例如: "顆"

    Returns:
        Dict[str, Any]: 消耗後的食材剩餘狀態，如果完全消耗則 quantity 為 0。
    """
    agent = _get_agent()
    inventory = agent.get_all_inventory()

    # 依名稱找到對應的食材
    target = None
    for item in inventory:
        if item['name'] == name:
            target = item
            break

    if not target:
        return {"error": f"找不到食材「{name}」", "status": "not_found"}

    try:
        agent.consume_ingredient(target['id'], quantity)
        updated = agent.get_ingredient(target['id'])
        return {
            "status": "success",
            "name": name,
            "consumed": quantity,
            "remaining_quantity": updated['quantity'] if updated else 0,
            "unit": unit
        }
    except ValueError as e:
        return {"error": str(e), "status": "insufficient"}
