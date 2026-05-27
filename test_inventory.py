import os
import sys
import re
from datetime import datetime, timedelta
from app.inventory_agent import InventoryAgent
from app.database import DB_PATH
from app.classifier import classify_ingredient
from app.expiry_agent import estimate_expiry_date

# 修正 Windows 終端機編碼問題 (cp950 不支援 Emoji)
sys.stdout.reconfigure(encoding='utf-8')
sys.stdin.reconfigure(encoding='utf-8')

# ============================
# AI 冰箱管家 - 互動式測試腳本
# ============================
# 模擬使用者與 Inventory Agent 的對話流程
# 確保 AI 能以清楚的指示引導使用者完成食材管理

CATEGORIES = {
    "1": "蔬菜",
    "2": "肉類",
    "3": "海鮮",
    "4": "水果",
    "5": "乳製品",
    "6": "冷凍食品/火鍋料",
    "7": "調味料",
    "8": "其他",
}

UNITS = {
    "1": "克",
    "2": "公斤",
    "3": "毫克",
    "4": "公升",
}


def print_divider():
    print("─" * 50)


def ai_say(message: str):
    """模擬 AI Agent 的回覆格式"""
    print(f"\n🤖 AI 管家: {message}")


def show_menu():
    """顯示主選單"""
    print_divider()
    ai_say("你好！我是你的 AI 冰箱管家 🧊")
    print("   請問你想做什麼呢？\n")
    print("   ❶ 食材入庫 (把新買的食材放進冰箱)")
    print("   ❷ 查看庫存 (看看冰箱裡有什麼)")
    print("   ❸ 消耗食材 (煮飯用掉了一些食材)")
    print("   ❹ 刪除食材 (丟掉過期或壞掉的食材)")
    print("   ❺ 查看快過期食材 (哪些東西快要過期了)")
    print("   ❻ 查看歷史紀錄 (查看食材所有異動日誌)")
    print("   ⓿ 離開系統")
    print_divider()


def choose_from_options(prompt: str, options: dict) -> str:
    """讓使用者從選項中選擇，支援輸入數字序號或直接輸入數值名稱"""
    ai_say(prompt)
    for key, value in options.items():
        print(f"   {key}. {value}")
    while True:
        choice = input("\n👤 你的選擇: ").strip()
        # 1. 檢查是否符合選項的 key (例如 "1")
        if choice in options:
            return options[choice]
        # 2. 檢查是否直接輸入了選項的 value (例如 "克" 或 "蔬菜")
        for key, value in options.items():
            if choice.lower() == value.lower():
                return value
        print("   ⚠️ 輸入無效，請輸入數字序號或直接輸入文字名稱。")


def ask_input(prompt: str) -> str:
    """向使用者詢問輸入"""
    ai_say(prompt)
    return input("👤 你的回答: ").strip()


def handle_add_ingredient(agent: InventoryAgent):
    """處理食材入庫流程"""
    ai_say("好的！讓我幫你把新食材登記入庫 📝")
    ai_say("請準備輸入以下內容：\n   [食材: 類別: 數量: 購買日: 到期日:]\n")

    # Step 1: 食材名稱
    name = ask_input("請問食材名稱是什麼？(例如：高麗菜、豬肉片)")
    if not name:
        ai_say("食材名稱不能為空，已取消操作。")
        return

    # Step 2: 類別 (由 AI 自動辨識)
    ai_say(f"正在分析「{name}」的食材分類...")
    predicted_category = classify_ingredient(name)
    ai_say(f"自動辨識分類為：【{predicted_category}】")
    
    confirm_cat = ask_input("分類正確嗎？(按 Enter 預設正確)")
    confirm_cat_clean = confirm_cat.lower().strip()
    
    # 預設按 Enter 為正確
    if not confirm_cat_clean:
        is_positive_cat = True
        is_negative_cat = False
    else:
        is_positive_cat = any(word in confirm_cat_clean for word in ["y", "yes", "是", "確定", "確認", "要", "對", "好", "ok", "同意", "正確"])
        is_negative_cat = any(word in confirm_cat_clean for word in ["n", "no", "否", "不", "取消", "拒絕", "不對", "錯誤"])

    if is_positive_cat and not is_negative_cat:
        category = predicted_category
        ai_say(f"📝 已設定類別為：「{category}」")
    else:
        category = choose_from_options("請選擇這個食材屬於哪一類：", CATEGORIES)

    # Step 3: 數量與單位
    quantity_str = ask_input("數量是多少？(可直接輸入數字加單位，例如：500克 或 10公升)")
    
    match = re.match(r"([\d\.]+)\s*(.*)", quantity_str)
    if not match:
        ai_say("⚠️ 數量格式不正確，已取消操作。")
        return
        
    try:
        quantity = float(match.group(1))
    except ValueError:
        ai_say("⚠️ 數量格式不正確，已取消操作。")
        return
        
    extracted_unit = match.group(2).strip()

    # Step 4: 單位 (若剛才已經輸入，則跳過選項)
    if extracted_unit:
        if extracted_unit in UNITS.values():
            unit = extracted_unit
            ai_say(f"📝 自動辨識單位為：「{unit}」")
        else:
            ai_say(f"⚠️ 錯誤：不支援的單位「{extracted_unit}」。僅支援：克、公斤、毫克、公升。")
            return
    else:
        unit = choose_from_options("單位是什麼？", UNITS)

    # Step 5: 購買日期
    purchase_date = ask_input("購買日期？(格式: YYYY-MM-DD，按 Enter 預設今天)")
    if not purchase_date:
        purchase_date = datetime.now().strftime("%Y-%m-%d")
        print(f"   ℹ️ 已設定為今天: {purchase_date}")

    # Step 6: 到期日期 — 優先使用 ExpiryAgent 智慧推算
    ai_say(f"正在根據「{name}」的類別推算預估保存期限...")
    estimated_expiry, sub_cat, shelf_days = estimate_expiry_date(
        name=name,
        category=category,
        purchase_date=purchase_date,
        storage_method="冷藏",  # 預設冷藏；未來可讓使用者選擇
    )

    # 顯示細分類別與預估天數給使用者
    sub_cat_display = sub_cat if sub_cat != category else ""
    if sub_cat_display:
        ai_say(f"🧠 智慧判斷：「{name}」屬於【{sub_cat}】，預設保存 {shelf_days} 天。")
    else:
        ai_say(f"🧠 智慧判斷：「{name}」屬於【{category}】，預設保存 {shelf_days} 天。")

    expiry_date = ask_input(
        f"預計到期日？(格式: YYYY-MM-DD，按 Enter 使用推算日期: {estimated_expiry})"
    )
    if not expiry_date:
        expiry_date = estimated_expiry
        print(f"   ℹ️ 已設定為推算到期日: {expiry_date} (購買後第 {shelf_days} 天)")

    # 確認
    print_divider()
    ai_say("請確認以下資訊：")
    print(f"   📦 食材: {name}")
    print(f"   📂 類別: {category}")
    print(f"   🔢 數量: {quantity} {unit}")
    print(f"   📅 購買日: {purchase_date}")
    print(f"   ⏰ 到期日: {expiry_date}")

    confirm = ask_input("確定要入庫嗎？(按 Enter 預設確認)")
    confirm_clean = confirm.lower().strip()
    
    # 預設按 Enter 為確認
    if not confirm_clean:
        is_positive = True
        is_negative = False
    else:
        is_positive = any(word in confirm_clean for word in ["y", "yes", "是", "確定", "確認", "要", "對", "好", "ok", "同意"])
        is_negative = any(word in confirm_clean for word in ["n", "no", "否", "不", "取消", "拒絕"])

    if is_positive and not is_negative:
        item_id = agent.add_ingredient(name, category, quantity, unit, purchase_date, expiry_date)
        ai_say(f"✅ 太好了！「{name}」已成功入庫！(編號: {item_id})")
    else:
        ai_say("已取消入庫操作。")


def handle_view_inventory(agent: InventoryAgent):
    """處理查看庫存流程"""
    inventory = agent.get_all_inventory()
    if not inventory:
        ai_say("冰箱裡目前是空的喔！要不要先去買些食材？🛒")
        return

    ai_say(f"目前冰箱裡有 {len(inventory)} 項食材：\n")
    print(f"   {'編號':<6} {'名稱':<10} {'類別':<8} {'數量':<12} {'購買日':<14} {'到期日':<14}")
    print("   " + "─" * 64)
    for item in inventory:
        qty_display = f"{item['quantity']} {item['unit']}"
        print(f"   {item['id']:<6} {item['name']:<10} {item['category']:<8} {qty_display:<12} {item['purchase_date']:<14} {item['expiry_date']:<14}")


def handle_consume_ingredient(agent: InventoryAgent):
    """處理消耗食材流程"""
    # 先顯示庫存
    inventory = agent.get_all_inventory()
    if not inventory:
        ai_say("冰箱裡沒有任何食材可以消耗喔！")
        return

    ai_say("好的，讓我看看冰箱裡有什麼可以用...\n")
    for item in inventory:
        print(f"   編號 {item['id']}: {item['name']} — 剩餘 {item['quantity']} {item['unit']}")

    # 選擇食材
    item_id_str = ask_input("請輸入要消耗的食材編號：")
    try:
        item_id = int(item_id_str)
    except ValueError:
        ai_say("⚠️ 編號格式不正確，已取消操作。")
        return

    item = agent.get_ingredient(item_id)
    if not item:
        ai_say(f"⚠️ 找不到編號 {item_id} 的食材。")
        return

    ai_say(f"你選擇了「{item['name']}」，目前剩餘 {item['quantity']} {item['unit']}。")
    amount_str = ask_input(f"要消耗多少 {item['unit']}？(可直接輸入數字)")
    match = re.match(r"([\d\.]+)", amount_str)
    if not match:
        ai_say("⚠️ 數量格式不正確，已取消操作。")
        return
        
    try:
        amount = float(match.group(1))
    except ValueError:
        ai_say("⚠️ 數量格式不正確，已取消操作。")
        return

    try:
        agent.consume_ingredient(item_id, amount)
        updated = agent.get_ingredient(item_id)
        ai_say(f"🍽️ 已消耗「{item['name']}」{amount} {item['unit']}！剩餘: {updated['quantity']} {updated['unit']}")
    except ValueError as e:
        ai_say(f"❌ 操作失敗: {e}")


def handle_delete_ingredient(agent: InventoryAgent):
    """處理刪除食材流程"""
    inventory = agent.get_all_inventory()
    if not inventory:
        ai_say("冰箱裡沒有任何食材可以刪除喔！")
        return

    ai_say("以下是目前的庫存：\n")
    for item in inventory:
        print(f"   編號 {item['id']}: {item['name']} — {item['quantity']} {item['unit']} (到期: {item['expiry_date']})")

    item_id_str = ask_input("請輸入要刪除的食材編號：")
    try:
        item_id = int(item_id_str)
    except ValueError:
        ai_say("⚠️ 編號格式不正確，已取消操作。")
        return

    item = agent.get_ingredient(item_id)
    if not item:
        ai_say(f"⚠️ 找不到編號 {item_id} 的食材。")
        return

    confirm = ask_input(f"確定要刪除「{item['name']}」嗎？這個動作無法復原。(按 Enter 預設確認)")
    confirm_clean = confirm.lower().strip()
    
    # 預設按 Enter 為確認
    if not confirm_clean:
        is_positive = True
        is_negative = False
    else:
        is_positive = any(word in confirm_clean for word in ["y", "yes", "是", "確定", "確認", "要", "對", "好", "ok", "同意"])
        is_negative = any(word in confirm_clean for word in ["n", "no", "否", "不", "取消", "拒絕"])

    if is_positive and not is_negative:
        agent.delete_ingredient(item_id)
        ai_say(f"🗑️ 已成功刪除「{item['name']}」！")
    else:
        ai_say("已取消刪除操作。")


def handle_expiring_check(agent: InventoryAgent):
    """處理查看快過期食材流程"""
    days_str = ask_input("要查看幾天內即將過期的食材？(預設 3 天，按 Enter 使用預設)")
    if not days_str:
        days = 3
    else:
        try:
            days = int(days_str)
        except ValueError:
            ai_say("⚠️ 天數格式不正確，使用預設 3 天。")
            days = 3

    target_date = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d")
    expiring = agent.get_expiring_ingredients(target_date)

    if not expiring:
        ai_say(f"太好了！未來 {days} 天內沒有食材會過期 🎉")
    else:
        ai_say(f"⚠️ 注意！以下 {len(expiring)} 項食材將在 {days} 天內過期：\n")
        for item in expiring:
            remaining_days = (datetime.strptime(item['expiry_date'], "%Y-%m-%d") - datetime.now()).days
            if remaining_days < 0:
                status = "🔴 已過期！"
            elif remaining_days == 0:
                status = "🟠 今天到期！"
            else:
                status = f"🟡 還剩 {remaining_days} 天"
            print(f"   {item['name']} ({item['quantity']} {item['unit']}) — 到期: {item['expiry_date']} {status}")
        ai_say("建議優先使用這些食材，避免浪費！🌱")


def handle_view_history(agent: InventoryAgent):
    """處理查看歷史異動紀錄流程"""
    history = agent.get_action_history()
    if not history:
        ai_say("目前還沒有任何食材異動紀錄喔！")
        return

    ai_say(f"目前共有 {len(history)} 筆食材異動紀錄：\n")
    print(f"   {'時間':<20} {'動作':<10} {'食材名稱':<12} {'數量/單位':<12} {'說明'}")
    print("   " + "─" * 72)
    
    # 對應動作的中文顯示
    action_map = {
        "ADD": "📥 入庫",
        "CONSUME": "🍽️ 消耗",
        "UPDATE_QTY": "🔄 調整",
        "DELETE": "🗑️ 刪除"
    }
    
    for log in history:
        action_display = action_map.get(log['action_type'], log['action_type'])
        qty_display = f"{log['quantity']} {log['unit']}" if log['quantity'] is not None else "-"
        print(f"   {log['created_at']:<20} {action_display:<10} {log['ingredient_name']:<12} {qty_display:<12} {log['details']}")


def main():
    """主程式 — 互動式對話迴圈"""
    agent = InventoryAgent()

    show_menu()

    while True:
        choice = input("\n👤 請輸入選項 (0-6): ").strip()

        if choice == "1":
            handle_add_ingredient(agent)
        elif choice == "2":
            handle_view_inventory(agent)
        elif choice == "3":
            handle_consume_ingredient(agent)
        elif choice == "4":
            handle_delete_ingredient(agent)
        elif choice == "5":
            handle_expiring_check(agent)
        elif choice == "6":
            handle_view_history(agent)
        elif choice == "0":
            ai_say("掰掰！記得常常檢查冰箱喔 👋🧊")
            break
        else:
            ai_say("⚠️ 無效的選項，請輸入 0~6 的數字。")

        print_divider()
        ai_say("還需要做什麼嗎？")
        print("   ❶ 入庫  ❷ 查庫存  ❸ 消耗  ❹ 刪除  ❺ 快過期  ❻ 歷史  ⓿ 離開")


if __name__ == "__main__":
    # 保留資料：已移除 startup 重置 DB 邏輯，以便保存歷史紀錄與食材資料
    main()
