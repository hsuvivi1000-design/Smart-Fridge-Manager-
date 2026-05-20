from typing import Optional, List, Dict, Any

def search_recipes(
    available_ingredients: List[str],
    preferences: Optional[List[str]] = None,
    expiring_ingredients: Optional[List[str]] = None
) -> List[Dict[str, Any]]:
    """
    根據現有可用食材、使用者忌口/偏好、以及即將過期的食材，從食譜知識庫檢索匹配最適合的食譜。

    Args:
        available_ingredients (List[str]): 現有可用的食材名稱列表，例如: ["高麗菜", "豬肉"]
        preferences (Optional[List[str]]): 使用者偏好或忌口設定，例如: ["不吃辣", "低鹽"]
        expiring_ingredients (Optional[List[str]]): 即將過期的食材名稱列表，用於優先考慮匹配食譜

    Returns:
        List[Dict[str, Any]]: 推薦的食譜列表，包含食譜名稱(name)、所需食材(ingredients)、步驟(instructions)、烹飪時間等。
    """
    raise NotImplementedError("待角色 D 實作")
