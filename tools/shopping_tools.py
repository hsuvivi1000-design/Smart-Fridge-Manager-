from typing import List, Dict, Any

def check_expiry(inventory: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    檢查冰箱食材的保存期限與保存狀態。

    Args:
        inventory (List[Dict[str, Any]]): 目前庫存食材列表。

    Returns:
        List[Dict[str, Any]]: 包含效期診斷狀態與預估過期日的食材列表。
    """
    raise NotImplementedError("待角色 E 實作")

def generate_shopping_list(
    missing_ingredients: List[Dict[str, Any]],
    low_stock_ingredients: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    自動整理低庫存或食譜缺件項目，產生格式化的採買清單。

    Args:
        missing_ingredients (List[Dict[str, Any]]): 匹配食譜時缺少的食材，包含 name、quantity、unit。
        low_stock_ingredients (List[Dict[str, Any]]): 目前冰箱中低於安全存量的食材，包含 name、quantity、unit。

    Returns:
        Dict[str, Any]: 產生的採買清單資訊，包含 markdown 格式的採買清單字串 (shopping_list_md) 與項目清單。
    """
    raise NotImplementedError("待角色 E 實作")
