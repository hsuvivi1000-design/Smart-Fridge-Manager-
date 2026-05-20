from typing import Optional, List, Dict, Any

def get_inventory() -> List[Dict[str, Any]]:
    """
    取得冰箱現有的所有食材庫存清單。

    Returns:
        List[Dict[str, Any]]: 庫存食材列表。每個食材包含 name、quantity、unit、purchase_date、expiry_date、category。
    """
    raise NotImplementedError("待角色 B 實作")

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
    raise NotImplementedError("待角色 B 實作")

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
    raise NotImplementedError("待角色 B 實作")
