import os
import unittest
from datetime import datetime, timedelta

# 在匯入任何 app 模組前，先設定測試資料庫的路徑，避免影響正式資料
os.environ["DB_PATH"] = "test_fridge_inventory.db"

from app.database import DB_PATH, get_db_connection
from app.inventory_agent import InventoryAgent

class TestInventoryAgent(unittest.TestCase):
    def setUp(self):
        """每個測試執行前執行，確保測試資料庫是乾淨的"""
        self.agent = InventoryAgent()
        # 清空資料表，確保測試環境獨立
        with get_db_connection() as conn:
            conn.execute("DELETE FROM inventory")
            conn.execute("DELETE FROM action_history")
            conn.commit()

    def tearDown(self):
        """每個測試完成後清理測試資料庫檔案"""
        if os.path.exists(DB_PATH):
            try:
                os.remove(DB_PATH)
            except PermissionError:
                pass  # 有時連線尚未釋放，可忽略

    def test_add_and_get_ingredient(self):
        """測試新增與查詢食材"""
        # 新增食材
        item_id = self.agent.add_ingredient(
            name="高麗菜",
            category="蔬菜",
            quantity=1.0,
            unit="公斤",
            purchase_date="2026-05-20",
            expiry_date="2026-05-27"
        )
        self.assertIsNotNone(item_id)
        
        # 查詢單一食材
        item = self.agent.get_ingredient(item_id)
        self.assertIsNotNone(item)
        self.assertEqual(item["name"], "高麗菜")
        self.assertEqual(item["category"], "蔬菜")
        self.assertEqual(item["quantity"], 1.0)
        self.assertEqual(item["unit"], "公斤")

    def test_get_all_inventory(self):
        """測試取得所有庫存"""
        self.agent.add_ingredient("蘋果", "水果", 5.0, "公斤", "2026-05-20", "2026-06-03")
        self.agent.add_ingredient("牛奶", "乳製品", 1.0, "公升", "2026-05-20", "2026-05-25")
        
        inventory = self.agent.get_all_inventory()
        self.assertEqual(len(inventory), 2)
        names = [item["name"] for item in inventory]
        self.assertIn("蘋果", names)
        self.assertIn("牛奶", names)

    def test_update_quantity(self):
        """測試更新數量"""
        item_id = self.agent.add_ingredient("豬肉片", "肉類", 500.0, "克", "2026-05-20", "2026-05-23")
        
        # 更新數量
        self.agent.update_quantity(item_id, 300.0)
        item = self.agent.get_ingredient(item_id)
        self.assertEqual(item["quantity"], 300.0)

    def test_consume_ingredient_success(self):
        """測試消耗食材成功"""
        item_id = self.agent.add_ingredient("蛋", "其他", 10.0, "克", "2026-05-20", "2026-06-10")
        
        # 消耗部分
        self.agent.consume_ingredient(item_id, 4.0)
        item = self.agent.get_ingredient(item_id)
        self.assertEqual(item["quantity"], 6.0)

    def test_consume_ingredient_insufficient(self):
        """測試消耗食材不足時應拋出例外"""
        item_id = self.agent.add_ingredient("起司", "乳製品", 2.0, "克", "2026-05-20", "2026-06-10")
        
        # 消耗超過庫存量，應拋出 ValueError
        with self.assertRaises(ValueError):
            self.agent.consume_ingredient(item_id, 3.0)

    def test_delete_ingredient(self):
        """測試刪除食材"""
        item_id = self.agent.add_ingredient("壞掉的番茄", "水果", 1.0, "公斤", "2026-05-10", "2026-05-15")
        
        # 刪除
        self.agent.delete_ingredient(item_id)
        item = self.agent.get_ingredient(item_id)
        self.assertIsNone(item)

    def test_get_expiring_ingredients(self):
        """測試過期食材篩選"""
        today = datetime.now()
        yesterday_str = (today - timedelta(days=1)).strftime("%Y-%m-%d")
        tomorrow_str = (today + timedelta(days=1)).strftime("%Y-%m-%d")
        next_week_str = (today + timedelta(days=7)).strftime("%Y-%m-%d")

        # 新增三種不同過期日的食材
        self.agent.add_ingredient("已過期吐司", "其他", 1.0, "公斤", "2026-05-10", yesterday_str)
        self.agent.add_ingredient("明天過期沙拉", "蔬菜", 1.0, "公斤", "2026-05-19", tomorrow_str)
        self.agent.add_ingredient("下週過期罐頭", "其他", 1.0, "公升", "2026-05-20", next_week_str)

        # 查詢今天到明天的過期清單 (以明天為基準日)
        expiring = self.agent.get_expiring_ingredients(tomorrow_str)
        self.assertEqual(len(expiring), 2)
        names = [item["name"] for item in expiring]
        self.assertIn("已過期吐司", names)
        self.assertIn("明天過期沙拉", names)
        self.assertNotIn("下週過期罐頭", names)

    def test_invalid_unit_validation(self):
        """測試新增不支援單位時應拋出例外"""
        with self.assertRaises(ValueError):
            self.agent.add_ingredient("不支援單位的食材", "其他", 1.0, "顆", "2026-05-20", "2026-05-27")

    def test_action_history_logging(self):
        """測試各項 CRUD 操作是否確實寫入歷史紀錄 (action_history)"""
        # 1. 測試入庫寫入歷史 (ADD)
        item_id = self.agent.add_ingredient("青江菜", "蔬菜", 200.0, "克", "2026-05-20", "2026-05-25")
        history = self.agent.get_action_history()
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["action_type"], "ADD")
        self.assertEqual(history[0]["ingredient_name"], "青江菜")
        self.assertEqual(history[0]["quantity"], 200.0)
        self.assertEqual(history[0]["unit"], "克")

        # 2. 測試手動調整數量寫入歷史 (UPDATE_QTY)
        self.agent.update_quantity(item_id, 150.0)
        history = self.agent.get_action_history()
        self.assertEqual(len(history), 2)
        self.assertEqual(history[0]["action_type"], "UPDATE_QTY")
        self.assertEqual(history[0]["ingredient_name"], "青江菜")
        self.assertEqual(history[0]["quantity"], 150.0)

        # 3. 測試消耗食材寫入歷史 (CONSUME)
        self.agent.consume_ingredient(item_id, 50.0)
        history = self.agent.get_action_history()
        self.assertEqual(len(history), 3)
        self.assertEqual(history[0]["action_type"], "CONSUME")
        self.assertEqual(history[0]["ingredient_name"], "青江菜")
        self.assertEqual(history[0]["quantity"], 50.0)

        # 4. 測試刪除食材寫入歷史 (DELETE)
        self.agent.delete_ingredient(item_id)
        history = self.agent.get_action_history()
        self.assertEqual(len(history), 4)
        self.assertEqual(history[0]["action_type"], "DELETE")
        self.assertEqual(history[0]["ingredient_name"], "青江菜")

if __name__ == "__main__":
    unittest.main()
