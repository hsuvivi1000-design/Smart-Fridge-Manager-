from typing import List, Dict, Any, Optional

def check_expiry(inventory: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    檢查冰箱食材的保存期限與保存狀態，並評估若過期造成的潛在金額損失。

    Args:
        inventory (List[Dict[str, Any]]): 目前庫存食材列表。包含 name、quantity、unit、expiry_date，以及價格資訊等。

    Returns:
        List[Dict[str, Any]]: 包含效期診斷狀態、預估過期日，以及潛在折舊與損耗金額損失的食材列表。
    """
    raise NotImplementedError("待角色 E 實作")

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
    raise NotImplementedError("待角色 E 實作")

