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
    try:
        from tools.recipe_matcher import RecipeMatcher
        matcher = RecipeMatcher()

        # 將偏好轉換為忌口清單
        dislikes = preferences if preferences else []
        expiring = expiring_ingredients if expiring_ingredients else []

        results = matcher.match_recipes(
            current_ingredients=available_ingredients,
            dislikes=dislikes,
            expiring_ingredients=expiring,
            top_k=5
        )

        if isinstance(results, dict) and "error" in results:
            # ChromaDB 未初始化，改用 Gemini 直接生成食譜
            return _fallback_recipe_search(available_ingredients, preferences, expiring_ingredients)

        if not results:
            return _fallback_recipe_search(available_ingredients, preferences, expiring_ingredients)

        # 轉換為統一格式
        formatted = []
        for r in results:
            formatted.append({
                "name": r.get("title", ""),
                "ingredients": r.get("ingredients", []),
                "instructions": r.get("steps", []),
                "url": r.get("url", ""),
                "nutrition": r.get("nutrition", {}),
                "score": r.get("score", 0)
            })
        return formatted

    except Exception as e:
        # RAG 不可用時，降級為直接推薦
        return _fallback_recipe_search(available_ingredients, preferences, expiring_ingredients)


def _fallback_recipe_search(
    available_ingredients: List[str],
    preferences: Optional[List[str]] = None,
    expiring_ingredients: Optional[List[str]] = None
) -> List[Dict[str, Any]]:
    """當 ChromaDB 不可用時，使用內建的基本食譜庫作為降級方案"""
    mock_recipes = [
        {
            "name": "高麗菜炒肉片",
            "ingredients": ["高麗菜", "豬肉", "蒜頭", "鹽", "醬油"],
            "instructions": ["1. 高麗菜切塊，豬肉切片。", "2. 熱鍋下油，爆香蒜頭。", "3. 放入豬肉炒至變色。", "4. 加入高麗菜翻炒。", "5. 加入鹽和醬油調味，炒熟即可。"],
            "nutrition": {"calories": 350, "protein": 20, "fat": 25, "carbs": 10}
        },
        {
            "name": "番茄炒蛋",
            "ingredients": ["番茄", "雞蛋", "蔥", "鹽", "糖"],
            "instructions": ["1. 番茄切塊，雞蛋打散。", "2. 炒熟雞蛋，盛出備用。", "3. 炒番茄至軟爛出汁。", "4. 加入雞蛋混合，加鹽糖調味。", "5. 撒上蔥花即可。"],
            "nutrition": {"calories": 250, "protein": 15, "fat": 15, "carbs": 12}
        },
        {
            "name": "清炒高麗菜",
            "ingredients": ["高麗菜", "蒜頭", "鹽"],
            "instructions": ["1. 高麗菜切塊。", "2. 爆香蒜頭。", "3. 加入高麗菜大火快炒。", "4. 加鹽調味即可。"],
            "nutrition": {"calories": 100, "protein": 2, "fat": 5, "carbs": 8}
        },
        {
            "name": "麻婆豆腐",
            "ingredients": ["豆腐", "豬絞肉", "豆瓣醬", "花椒", "辣椒", "蒜末", "蔥"],
            "instructions": ["1. 豆腐切塊。", "2. 炒熟豬絞肉。", "3. 加入豆瓣醬、花椒、辣椒、蒜末爆香。", "4. 加水煮滾，放入豆腐。", "5. 勾芡後撒上蔥花。"],
            "nutrition": {"calories": 450, "protein": 22, "fat": 35, "carbs": 15}
        },
        {
            "name": "生酮蒜香鮭魚",
            "ingredients": ["鮭魚", "蒜末", "橄欖油", "鹽", "黑胡椒"],
            "instructions": ["1. 鮭魚兩面撒上鹽與黑胡椒。", "2. 熱鍋下橄欖油，煎熟鮭魚。", "3. 最後加入蒜末爆香即可。"],
            "nutrition": {"calories": 380, "protein": 30, "fat": 28, "carbs": 1}
        },
    ]

    # 簡單的關鍵字匹配過濾
    if available_ingredients:
        scored = []
        for recipe in mock_recipes:
            match_count = sum(1 for ing in available_ingredients if any(ing in r_ing for r_ing in recipe["ingredients"]))
            if match_count > 0:
                scored.append((match_count, recipe))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [r for _, r in scored[:3]] if scored else mock_recipes[:3]

    return mock_recipes[:3]
