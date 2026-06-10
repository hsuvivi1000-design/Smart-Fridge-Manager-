import sys
import os
sys.path.insert(0, '.')
sys.stdout.reconfigure(encoding='utf-8')
sys.stdin.reconfigure(encoding='utf-8')

from app.database import init_db, execute_query
from app.inventory_agent import InventoryAgent
from tools.shopping_tools import generate_shopping_list

def run_tests():
    print("Initializing Database...")
    init_db()
    
    agent = InventoryAgent()
    
    # 1. 測試食材入庫是否支援 min_quantity 參數，且是否支援智慧預設值
    print("\n--- 測試 1: 食材入庫與智慧預設安全臨界值 ---")
    
    # 使用預設 (克 -> 100.0)
    id1 = agent.add_ingredient("大白菜", "蔬菜", 150.0, "克", "2026-06-07", "2026-06-12", min_quantity=None)
    item1 = agent.get_ingredient(id1)
    print(f"大白菜入庫成功，單位：克，數量：{item1['quantity']}，智慧預設安全存量為：{item1['min_quantity']}")
    assert item1['min_quantity'] == 100.0, "智慧預設安全水位（克）應該是 100.0"
    
    # 使用預設 (個 -> 1.0)
    id2 = agent.add_ingredient("雞蛋", "蛋", 6.0, "個", "2026-06-07", "2026-06-15", min_quantity=None)
    item2 = agent.get_ingredient(id2)
    print(f"雞蛋入庫成功，單位：個，數量：{item2['quantity']}，智慧預設安全存量為：{item2['min_quantity']}")
    assert item2['min_quantity'] == 1.0, "智慧預設安全水位（個）應該是 1.0"
    
    # 自訂安全水位
    id3 = agent.add_ingredient("豬肉片", "肉類", 300.0, "克", "2026-06-07", "2026-06-10", min_quantity=50.0)
    item3 = agent.get_ingredient(id3)
    print(f"豬肉片入庫成功，自訂安全存量為：{item3['min_quantity']}")
    assert item3['min_quantity'] == 50.0, "自訂安全水位應該是 50.0"
    
    # 2. 測試更新 min_quantity 欄位
    print("\n--- 測試 2: 更新安全存量臨界值 ---")
    agent.update_min_quantity(id2, 3.0)
    item2_updated = agent.get_ingredient(id2)
    print(f"雞蛋安全水位更新後為：{item2_updated['min_quantity']}")
    assert item2_updated['min_quantity'] == 3.0, "安全水位更新失敗"
    
    # 3. 測試偵測低庫存與預算感知優先級
    print("\n--- 測試 3: 偵測低庫存與預算感知採買清單生成 ---")
    
    # 模擬庫存狀況
    # 大白菜: 150g > 100g (不屬於低庫存)
    # 雞蛋: 6個 > 3個 (不屬於低庫存)
    # 豬肉片: 300g > 50g (不屬於低庫存)
    
    # 消耗大白菜到低水位
    agent.consume_ingredient(id1, 100.0) # 剩下 50.0 克
    item1_low = agent.get_ingredient(id1)
    print(f"大白菜消耗 100克，剩下 {item1_low['quantity']} 克，安全存量 {item1_low['min_quantity']}")
    
    # 消耗雞蛋到低水位
    agent.consume_ingredient(id2, 4.0) # 剩下 2.0 個
    item2_low = agent.get_ingredient(id2)
    print(f"雞蛋消耗 4個，剩下 {item2_low['quantity']} 個，安全存量 {item2_low['min_quantity']}")
    
    # 找出所有低庫存食材
    all_items = agent.get_all_inventory()
    low_stock = []
    for item in all_items:
        mq = item.get("min_quantity", 0.0)
        q = item.get("quantity", 0.0)
        if mq > 0.0 and q <= mq:
            low_stock.append({
                "name": item["name"],
                "quantity": mq - q,
                "unit": item["unit"]
            })
            
    print("低庫存食材:", low_stock)
    assert len(low_stock) >= 2, "應該至少有大白菜與雞蛋為低庫存"
    
    # 測試預算正常時的採買清單
    shopping_normal = generate_shopping_list(
        missing_ingredients=[{"name": "豆腐", "quantity": 1.0, "unit": "盒"}],
        low_stock_ingredients=low_stock,
        budget_status="正常"
    )
    print("\n[預算：正常] 產生的採買清單:")
    print(shopping_normal["shopping_list_md"])
    
    # 驗證優先級
    normal_items = shopping_normal["items"]
    tofu_item = next(x for x in normal_items if x["name"] == "豆腐")
    egg_item = next(x for x in normal_items if x["name"] == "雞蛋")
    assert tofu_item["priority"] == "high", "正常預算下，食譜缺件應為 high 優先級"
    assert egg_item["priority"] == "medium", "正常預算下，低庫存補充應為 medium 優先級"
    
    # 測試預算吃緊時的採買清單
    shopping_tight = generate_shopping_list(
        missing_ingredients=[{"name": "豆腐", "quantity": 1.0, "unit": "盒"}],
        low_stock_ingredients=low_stock,
        budget_status="吃緊"
    )
    print("\n[預算：吃緊] 產生的採買清單:")
    print(shopping_tight["shopping_list_md"])
    
    tight_items = shopping_tight["items"]
    tofu_tight = next(x for x in tight_items if x["name"] == "豆腐")
    egg_tight = next(x for x in tight_items if x["name"] == "雞蛋")
    assert tofu_tight["priority"] == "medium", "預算吃緊下，食譜缺件降為 medium"
    assert egg_tight["priority"] == "low", "預算吃緊下，低庫存補充降為 low 且備註可延後"
    assert "可延後" in shopping_tight["shopping_list_md"], "預算吃緊時，低庫存應有「可延後」標注"
    
    # 清理測試資料
    agent.delete_ingredient(id1)
    agent.delete_ingredient(id2)
    agent.delete_ingredient(id3)
    print("\n=== 所有測試皆順利通過！ ===")

if __name__ == "__main__":
    run_tests()
