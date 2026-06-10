import os
from datetime import date
from app.inventory_agent import InventoryAgent
from app.classifier import classify_ingredient
from agents.chef_planner import ChefAgent
from app.database import get_db_connection

def run_test():
    print("=== 測試 1: 自動分類 ===")
    ingredient_name = "雞胸肉"
    category = classify_ingredient(ingredient_name)
    print(f"輸入: {ingredient_name} -> AI 自動分類為: {category}")
    
    ingredient2 = "高麗菜"
    cat2 = classify_ingredient(ingredient2)
    print(f"輸入: {ingredient2} -> AI 自動分類為: {cat2}")

    print("\n=== 測試 2: 庫存建立 ===")
    # Clear DB for clean test
    with get_db_connection() as conn:
        conn.execute("DELETE FROM inventory")
        conn.execute("DELETE FROM action_history")
        conn.commit()

    inventory_agent = InventoryAgent()
    today = date.today().strftime("%Y-%m-%d")
    inventory_agent.add_ingredient(name="雞胸肉", category="肉類", quantity=500.0, unit="克", purchase_date=today, expiry_date="2026-12-31")
    inventory_agent.add_ingredient(name="高麗菜", category="蔬菜", quantity=1.0, unit="顆", purchase_date=today, expiry_date="2026-12-31")
    
    current_inv = inventory_agent.get_all_inventory()
    print("當前庫存:")
    for item in current_inv:
        print(f"- {item['name']} {item['quantity']} {item['unit']}")

    print("\n=== 測試 3: AI 大廚三階段互動 ===")
    agent = ChefAgent()
    
    print("\n【階段一】詢問晚餐推薦")
    msg1 = "晚餐吃什麼好？我只有雞胸肉跟高麗菜。"
    print(f"User: {msg1}")
    res1 = agent.run(msg1)
    print(f"AI: {res1['response']}")

    print("\n【階段二】確認料理與採買清單")
    msg2 = "聽起來不錯，我要煮第一道！"
    print(f"User: {msg2}")
    res2 = agent.run(msg2)
    print(f"AI: {res2['response']}")

    print("\n【階段三】回報使用並扣除庫存")
    msg3 = "我煮完了，用了 200 克 雞胸肉"
    print(f"User: {msg3}")
    res3 = agent.run(msg3)
    print(f"AI: {res3['response']}")

    print("\n=== 驗證庫存是否扣除 ===")
    updated_inv = inventory_agent.get_all_inventory()
    for item in updated_inv:
        print(f"- {item['name']} {item['quantity']} {item['unit']}")

if __name__ == "__main__":
    run_test()
