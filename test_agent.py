import os
import unittest
from unittest.mock import MagicMock, patch
from dotenv import load_dotenv

# 載入環境變數
load_dotenv()

# 匯入待測試模組
from models.schemas import Ingredient, Recipe, ShoppingItem
from tools.inventory_tools import get_inventory, add_ingredient, consume_ingredient
from tools.recipe_tools import search_recipes
from tools.shopping_tools import check_expiry, generate_shopping_list
from agents.chef_planner import ChefAgent


class TestChefAgentFramework(unittest.TestCase):
    """
    驗證角色 C 核心 Chef Agent 決策框架、工具介面與手動 Function Calling 流程。
    """

    def test_tool_signatures_and_stubs(self):
        """
        1. 驗證 6 個 Tool 簽名，並確保預設 raise NotImplementedError。
        """
        print("\n--- 測試 1: 驗證工具介面簽名與 Stub 拋出異常 ---")
        
        # 驗證呼叫 stub 拋出 NotImplementedError
        with self.assertRaises(NotImplementedError) as ctx:
            get_inventory()
        self.assertIn("待角色 B 實作", str(ctx.exception))

        with self.assertRaises(NotImplementedError) as ctx:
            add_ingredient(name="高麗菜", quantity=1.0, unit="顆")
        self.assertIn("待角色 B 實作", str(ctx.exception))

        with self.assertRaises(NotImplementedError) as ctx:
            consume_ingredient(name="高麗菜", quantity=0.5, unit="顆")
        self.assertIn("待角色 B 實作", str(ctx.exception))

        with self.assertRaises(NotImplementedError) as ctx:
            search_recipes(available_ingredients=["高麗菜"])
        self.assertIn("待角色 D 實作", str(ctx.exception))

        with self.assertRaises(NotImplementedError) as ctx:
            check_expiry(inventory=[])
        self.assertIn("待角色 E 實作", str(ctx.exception))

        with self.assertRaises(NotImplementedError) as ctx:
            generate_shopping_list(missing_ingredients=[], low_stock_ingredients=[])
        self.assertIn("待角色 E 實作", str(ctx.exception))
        
        print("✓ 工具 Stub 驗證通過")

    def test_agent_initialization_and_system_prompt(self):
        """
        2. 初始化 Agent 並檢查 System Prompt 關鍵字與工具對照表。
        """
        print("\n--- 測試 2: 驗證 Agent 初始化與 System Prompt ---")
        
        # 使用 dummy key 初始化 Agent，避免無 API key 時初始化失敗
        agent = ChefAgent(api_key="mock_key_12345")
        
        # 檢查 6 個 Tool 鍵是否存在於 tools_map
        required_tools = {
            "get_inventory",
            "add_ingredient",
            "consume_ingredient",
            "search_recipes",
            "check_expiry",
            "generate_shopping_list"
        }
        self.assertTrue(required_tools.issubset(agent.tools_map.keys()), "工具對照表缺少必要的 Tool")
        
        # 藉由 Mock run 方法來檢視 system_instruction，或者在此處測試關鍵字。
        # 我們直接宣告一個內含 system_instruction 的測試 (我們在 ChefAgent.run 中定義了 system_instruction)
        # 為了能在不執行 LLM 下檢查 system_instruction，我們可以直接檢查 run 內部產生的 config 設定
        with patch('google.genai.Client') as mock_client:
            agent = ChefAgent(api_key="mock_key_12345")
            # 使用 mock client 呼叫 run，確認其 system_instruction 是否包含關鍵字
            mock_generate = mock_client.return_value.models.generate_content
            
            # 設定 mock 回傳值，讓 run 可以結束
            mock_resp = MagicMock()
            mock_resp.candidates = []
            mock_resp.function_calls = []
            mock_resp.text = "結束"
            mock_generate.return_value = mock_resp
            
            agent.run("測試指令")
            
            # 取得 generate_content 被呼叫時傳入的 config
            call_args = mock_generate.call_args
            config = call_args[1].get('config')
            self.assertIsNotNone(config)
            system_instruction = config.system_instruction
            
            # 檢查 System Prompt 的核心關鍵字
            keywords = ["大廚", "冰箱大管家", "get_inventory", "check_expiry", "search_recipes", "generate_shopping_list"]
            for kw in keywords:
                self.assertIn(kw, system_instruction, f"System Prompt 遺漏關鍵字: {kw}")
                
        print("✓ System Prompt 關鍵字檢查與初始化驗證通過")

    @patch('google.genai.Client')
    def test_manual_function_calling_loop(self, mock_genai_client):
        """
        3. 使用 Mock LLM 驗證手動攔截 Function Calling 的 Thought、Action 與 Observation 記錄流程。
        """
        print("\n--- 測試 3: 驗證手動 Function Calling 攔截與 Log 流程 ---")
        
        # 模擬 Mock 工具實作
        mock_inventory_data = [{"name": "豬肉", "quantity": 1, "unit": "包"}]
        mock_expiry_data = [{"name": "豬肉", "status": "即將過期"}]
        mock_recipes = [{"name": "高麗菜炒肉片", "ingredients": [{"name": "豬肉", "quantity": 1, "unit": "包"}, {"name": "高麗菜", "quantity": 0.5, "unit": "顆"}]}]
        mock_shopping_list = {"shopping_list_md": "- 高麗菜 0.5 顆 (食譜缺件)"}

        # 注入 Mock 工具
        injected_tools = {
            "get_inventory": MagicMock(return_value=mock_inventory_data),
            "check_expiry": MagicMock(return_value=mock_expiry_data),
            "search_recipes": MagicMock(return_value=mock_recipes),
            "generate_shopping_list": MagicMock(return_value=mock_shopping_list)
        }

        # 初始化 ChefAgent 注入 mock tools
        agent = ChefAgent(api_key="mock_key_12345", tool_implementations=injected_tools)

        # 模擬 LLM 的多輪輸出
        # 第一輪：LLM 思考並呼叫 get_inventory 庫存
        mock_call_1 = MagicMock()
        mock_call_1.name = "get_inventory"
        mock_call_1.args = {}
        
        mock_content_1 = MagicMock()
        mock_content_1.parts = [MagicMock(text="我需要先檢查庫存"), mock_call_1]
        
        mock_resp_1 = MagicMock()
        mock_resp_1.text = "我需要先檢查庫存"
        mock_resp_1.function_calls = [mock_call_1]
        mock_resp_1.candidates = [MagicMock(content=mock_content_1)]

        # 第二輪：LLM 思考並呼叫 check_expiry 檢查效期
        mock_call_2 = MagicMock()
        mock_call_2.name = "check_expiry"
        mock_call_2.args = {"inventory": mock_inventory_data}
        
        mock_content_2 = MagicMock()
        mock_content_2.parts = [MagicMock(text="檢查效期以確定食材狀態"), mock_call_2]
        
        mock_resp_2 = MagicMock()
        mock_resp_2.text = "檢查效期以確定食材狀態"
        mock_resp_2.function_calls = [mock_call_2]
        mock_resp_2.candidates = [MagicMock(content=mock_content_2)]

        # 第三輪：LLM 思考並呼叫 search_recipes 尋找食譜
        mock_call_3 = MagicMock()
        mock_call_3.name = "search_recipes"
        mock_call_3.args = {"available_ingredients": ["豬肉"]}
        
        mock_content_3 = MagicMock()
        mock_content_3.parts = [MagicMock(text="現在來推薦適合的食譜"), mock_call_3]
        
        mock_resp_3 = MagicMock()
        mock_resp_3.text = "現在來推薦適合的食譜"
        mock_resp_3.function_calls = [mock_call_3]
        mock_resp_3.candidates = [MagicMock(content=mock_content_3)]

        # 第四輪：LLM 思考並呼叫 generate_shopping_list 缺料採買
        mock_call_4 = MagicMock()
        mock_call_4.name = "generate_shopping_list"
        mock_call_4.args = {
            "missing_ingredients": [{"name": "高麗菜", "quantity": 0.5, "unit": "顆"}],
            "low_stock_ingredients": []
        }
        
        mock_content_4 = MagicMock()
        mock_content_4.parts = [MagicMock(text="发现缺少高麗菜，生成採買清單"), mock_call_4]
        
        mock_resp_4 = MagicMock()
        mock_resp_4.text = "发现缺少高麗菜，生成採買清單"
        mock_resp_4.function_calls = [mock_call_4]
        mock_resp_4.candidates = [MagicMock(content=mock_content_4)]

        # 第五輪：最終結果回覆
        mock_resp_5 = MagicMock()
        mock_resp_5.text = "建議烹煮高麗菜炒肉片。採買清單已生成：高麗菜 0.5 顆。"
        mock_resp_5.function_calls = []
        mock_resp_5.candidates = [MagicMock(content=MagicMock(parts=[MagicMock(text="建議烹煮...")]))]

        # 設定 mock_client generate_content 的連續回傳序列
        mock_genai_client.return_value.models.generate_content.side_effect = [
            mock_resp_1,
            mock_resp_2,
            mock_resp_3,
            mock_resp_4,
            mock_resp_5
        ]

        # 執行 Agent
        result = agent.run("今晚吃什麼？")
        logs = result["logs"]

        # 驗證最終輸出
        self.assertIn("建議烹煮", result["response"])

        # 驗證決策日誌 Logs 長度與內容 (應有 4 次 Tool 調用)
        self.assertEqual(len(logs), 4)

        # 驗證 log 1 (get_inventory)
        self.assertEqual(logs[0]["action"]["tool"], "get_inventory")
        self.assertEqual(logs[0]["thought"], "我需要先檢查庫存")
        self.assertEqual(logs[0]["observation"], mock_inventory_data)
        injected_tools["get_inventory"].assert_called_once()

        # 驗證 log 2 (check_expiry)
        self.assertEqual(logs[1]["action"]["tool"], "check_expiry")
        self.assertEqual(logs[1]["action"]["args"]["inventory"], mock_inventory_data)
        self.assertEqual(logs[1]["observation"], mock_expiry_data)
        injected_tools["check_expiry"].assert_called_once()

        # 驗證 log 3 (search_recipes)
        self.assertEqual(logs[2]["action"]["tool"], "search_recipes")
        self.assertEqual(logs[2]["observation"], mock_recipes)
        injected_tools["search_recipes"].assert_called_once()

        # 驗證 log 4 (generate_shopping_list)
        self.assertEqual(logs[3]["action"]["tool"], "generate_shopping_list")
        self.assertEqual(logs[3]["observation"], mock_shopping_list)
        injected_tools["generate_shopping_list"].assert_called_once()

        # 列印 log 內容供驗證
        print("\n--- 模擬運作之 Thought / Action / Observation 歷程 ---")
        for i, log in enumerate(logs, 1):
            print(f"Step {i}:")
            print(f"  [Thought]     : {log['thought']}")
            print(f"  [Action]      : {log['action']['tool']}({log['action']['args']})")
            print(f"  [Observation] : {log['observation']}")
        print("✓ 手動 Function Calling 攔截與 Log 測試通過")

    def test_live_connection_and_execution(self):
        """
        4. 連線測試：若有提供 GEMINI_API_KEY，進行真實 Gemini API 串接與 mock 執行測試。
        """
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            print("\n--- 測試 4: 連線測試 (跳過) ---")
            print("跳過連線測試：環境變數中未設定 GEMINI_API_KEY")
            return

        print("\n--- 測試 4: 連線測試 (真實 API 呼叫) ---")
        # 真實 API 測試中，我們同樣使用 mock 實作工具注入，但 LLM 決策為真實 API
        mock_inventory_data = [
            {"name": "高麗菜", "quantity": 0.5, "unit": "顆", "expiry_date": "2026-05-22"},
            {"name": "豬肉", "quantity": 200, "unit": "g", "expiry_date": "2026-05-21"}
        ]
        
        # 真實 API 測試中，我們使用真實 Python 函數作為注入工具，確保 SDK 能正常解析簽名與 docstrings
        def mock_get_inventory() -> list[dict]:
            """取得冰箱現有的所有食材庫存清單。"""
            return mock_inventory_data

        def mock_check_expiry(inventory: list[dict]) -> list[dict]:
            """檢查冰箱食材的保存期限與保存狀態。"""
            return [{"name": item["name"], "status": "即將過期" if item["name"] == "豬肉" else "正常"} for item in inventory]

        def mock_search_recipes(available_ingredients: list[str], preferences: list[str] = None, expiring_ingredients: list[str] = None) -> list[dict]:
            """根據現有可用食材與忌口偏好，從食譜知識庫檢索匹配最適合的食譜。"""
            return [{
                "name": "高麗菜炒肉片",
                "ingredients": [{"name": "豬肉", "quantity": 100, "unit": "g"}, {"name": "高麗菜", "quantity": 0.25, "unit": "顆"}],
                "instructions": ["1. 切食材", "2. 熱油下鍋炒熟"]
            }]

        def mock_generate_shopping_list(missing_ingredients: list[dict], low_stock_ingredients: list[dict], budget_status: str = None) -> dict:
            """自動整理低庫存或食譜缺件項目，並結合預算狀態，產生格式化的採買清單。"""
            return {"shopping_list_md": "無缺件"}

        injected_tools = {
            "get_inventory": mock_get_inventory,
            "check_expiry": mock_check_expiry,
            "search_recipes": mock_search_recipes,
            "generate_shopping_list": mock_generate_shopping_list
        }

        agent = ChefAgent(api_key=api_key, tool_implementations=injected_tools)
        result = agent.run("我今晚想做飯，看看冰箱有什麼可以推薦的？")
        
        self.assertIsNotNone(result)
        self.assertIn("response", result)
        self.assertIn("logs", result)
        
        print("\n--- 真實 API 決策歷程 ---")
        for i, log in enumerate(result["logs"], 1):
            print(f"Step {i}:")
            print(f"  [Thought]     : {log['thought']}")
            print(f"  [Action]      : {log['action']['tool']}({log['action']['args']})")
            print(f"  [Observation] : {log['observation']}")
            
        print("\n--- 真實 API 最終回覆 ---")
        print(result["response"])
        print("✓ 連線測試與決策邏輯通過")

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
