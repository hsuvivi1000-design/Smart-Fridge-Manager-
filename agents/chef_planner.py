import os
from typing import Optional, List, Dict, Any
from dotenv import load_dotenv
from google import genai
from google.genai import types

# 載入環境變數 (例如 GEMINI_API_KEY)
load_dotenv()

class ChefAgent:
    """
    核心 Chef Agent (角色 C) 規劃類別。
    串接 LLM 決策邏輯並實作手動攔截 Function Calling 流程，
    記錄每一輪的 Thought (思考)、Action (行動與參數) 以及 Observation (觀察結果)。
    """
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gemini-2.5-flash",
        tool_implementations: Optional[Dict[str, Any]] = None
    ):
        """
        初始化 ChefAgent。

        Args:
            api_key (Optional[str]): Gemini API 金鑰。若無，將自環境變數 GEMINI_API_KEY 讀取。
            model (str): 使用的 Gemini 模型名稱，預設為 gemini-2.5-flash。
            tool_implementations (Optional[Dict[str, Any]]): 用於注入的 Mock/實作工具字典，
                                                             鍵為工具名稱，值為 Callable 函式。
        """
        self.model = model
        
        # 取得金鑰並初始化 Client
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        if self.api_key:
            self.client = genai.Client(api_key=self.api_key)
        else:
            # 若無金鑰，將由 SDK 嘗試預設載入流程 (可能引發 ValueError)
            self.client = genai.Client()

        # 導入預設介面 stubs
        from tools.inventory_tools import get_inventory, add_ingredient, consume_ingredient
        from tools.recipe_tools import search_recipes
        from tools.shopping_tools import check_expiry, generate_shopping_list

        # 初始化工具對照表
        self.tools_map = {
            "get_inventory": get_inventory,
            "add_ingredient": add_ingredient,
            "consume_ingredient": consume_ingredient,
            "search_recipes": search_recipes,
            "check_expiry": check_expiry,
            "generate_shopping_list": generate_shopping_list,
        }

        # 支援注入實作或 Mock 方法 (便於測試與後續串接)
        if tool_implementations:
            self.tools_map.update(tool_implementations)

    def run(self, user_message: str) -> Dict[str, Any]:
        """
        執行 Agent 決策流程，處理使用者訊息並觸發工具調用。

        Args:
            user_message (str): 使用者輸入的請求訊息。

        Returns:
            Dict[str, Any]: 包含最終回覆 'response' 與決策歷程 'logs'。
        """
        # 初始化對話歷程
        history = [
            types.Content(role="user", parts=[types.Part.from_text(text=user_message)])
        ]
        logs = []
        expired_names_set: set = set()  # 跨工具累積過期食材名稱

        # 設計 System Prompt (專業大廚與冰箱管家角色，定義決策優先級)
        from datetime import datetime
        today_str = datetime.now().strftime("%Y-%m-%d")
        system_instruction = (
            "你是一位專業的大廚與冰箱大管家 (AI Kitchen Chef Agent)。\n"
            f"今天的日期是：{today_str}。\n"
            "你的任務是根據冰箱現有食材，為使用者推薦今日可以烹飪的料理。\n"
            "請嚴格遵守以下決策流程，不可跳過任何步驟：\n\n"
            "【步驟一：取得庫存】\n"
            "呼叫 `get_inventory` 取得所有食材的清單（含名稱、數量、到期日）。\n\n"
            "【步驟二：過濾過期食材】\n"
            "呼叫 `check_expiry` 判斷每項食材的保存狀態。\n"
            "- 狀態為「已過期」的食材，絕對不可用於任何食譜推薦，請在心中記下它們的名稱，留待最後告知使用者。\n"
            "- 僅使用狀態為「正常」、「即將到期」或「剩餘天數 ≤ 3 天」的食材來規劃菜色。\n\n"
            "【步驟三：推薦食譜（2–3 道）】\n"
            "呼叫 `search_recipes`，根據以下原則選出 2 到 3 道菜：\n"
            "- 優先選用即將到期（剩餘天數最少）的食材，避免浪費。\n"
            "- 所有推薦食譜的主要食材必須是冰箱中「未過期」的庫存。\n"
            "- 每道菜請說明：菜名、使用到哪些冰箱食材、簡短烹調方式（1–2 句）。\n\n"
            "【步驟四：採買清單（視需要）】\n"
            "僅在推薦食譜缺少部分食材時，才呼叫 `generate_shopping_list` 列出需採購的項目。\n"
            "若冰箱食材已足夠完成所有推薦菜色，則跳過此步驟，不需產生採買清單。\n\n"
            "【步驟五：最終回覆格式】\n"
            "請以繁體中文，按照以下順序回覆使用者：\n"
            "1. 🍽️ 今日推薦菜色（2–3 道），說明每道菜使用的食材與作法。\n"
            "2. 🛒 採買清單（若有缺料才顯示）。\n"
            "3. ⚠️ 已過期食材提醒：列出所有過期食材名稱，提醒使用者已無法使用。\n"
            "   若無過期食材，此區塊可省略。\n"
        )

        # 設定 GenerateContentConfig
        # 將 tools_map 中註冊的 callable 函式傳入作為 available tools
        config = types.GenerateContentConfig(
            system_instruction=system_instruction,
            tools=list(self.tools_map.values()),
        )

        max_iterations = 10
        iteration = 0

        while iteration < max_iterations:
            iteration += 1
            
            # 呼叫 Gemini 模型
            response = self.client.models.generate_content(
                model=self.model,
                contents=history,
                config=config
            )

            # 將 LLM 生成內容存入對話歷史 (設定 role 為 model)
            if response.candidates and response.candidates[0].content:
                model_content = response.candidates[0].content
                model_content.role = "model"
                history.append(model_content)
            else:
                break

            # 提取 LLM 在這一輪的 Thought (思考)
            thought = response.text or ""

            # 若此輪沒有產生 function_calls，代表決策樹結束
            if not response.function_calls:
                break

            tool_responses = []

            # 遍歷此輪所有工具呼叫請求 (Gemini 2.5 支援平行工具呼叫)
            for function_call in response.function_calls:
                tool_name = function_call.name
                tool_args = function_call.args
                args_dict = dict(tool_args) if tool_args else {}

                # 建立本輪 Log 模板
                action_log = {
                    "thought": thought,
                    "action": {
                        "tool": tool_name,
                        "args": args_dict
                    },
                    "observation": None
                }

                # 執行對應工具
                if tool_name in self.tools_map:
                    try:
                        func = self.tools_map[tool_name]
                        observation = func(**args_dict)
                    except NotImplementedError as e:
                        # 處理 stubs 尚未實作的預設行為
                        observation = {
                            "error": f"Tool '{tool_name}' is not implemented yet",
                            "detail": str(e)
                        }
                    except Exception as e:
                        observation = {
                            "error": f"Exception occurred in tool '{tool_name}'",
                            "detail": str(e)
                        }
                    # ── 攔截工具回傳，確保 LLM 永遠看不到過期食材 ──
                    if tool_name == "get_inventory" and isinstance(observation, list):
                        from datetime import datetime
                        today = datetime.now().date()
                        fresh_items = []
                        for item in observation:
                            expiry_str = item.get("expiry_date", "")
                            try:
                                expiry_date = datetime.strptime(expiry_str, "%Y-%m-%d").date()
                                days_left = (expiry_date - today).days
                            except (ValueError, TypeError):
                                days_left = None

                            if days_left is not None and days_left < 0:
                                # 已過期 → 記錄名稱，不傳給 LLM
                                expired_names_set.add(item.get("name", "未知"))
                            else:
                                # 未過期 → 附上剩餘天數方便 LLM 排序緊迫程度
                                item_copy = dict(item)
                                if days_left is not None:
                                    item_copy["days_left"] = days_left
                                fresh_items.append(item_copy)

                        # 覆寫 observation，LLM 只拿到未過期食材
                        observation = fresh_items

                    elif tool_name == "check_expiry" and isinstance(observation, list):
                        # check_expiry 結果中「已過期」的名稱也累積到集合
                        for item in observation:
                            if item.get("status") == "已過期":
                                expired_names_set.add(item.get("name", "未知"))
                        # 過濾觀測結果，只保留非過期項目給 LLM
                        observation = [item for item in observation if item.get("status") != "已過期"]
                else:
                    observation = {
                        "error": f"Tool '{tool_name}' not registered in ChefAgent"
                    }

                # 更新 Log
                action_log["observation"] = observation
                logs.append(action_log)

                # 封裝 Tool Response Part (Gemini 要求回傳型態為 Dict)
                resp_dict = observation if isinstance(observation, dict) else {"result": observation}
                tool_responses.append(
                    types.Part.from_function_response(
                        name=tool_name,
                        response=resp_dict
                    )
                )

            # 將工具回傳之 Observation 包裝為 Content 存回 history (角色為 user)
            if tool_responses:
                history.append(
                    types.Content(
                        role="user",
                        parts=tool_responses
                    )
                )

        final_response = response.text if response.text else "決策流程執行完畢。"
        # 過期食材警告：統一放在回覆最末，且使用從兩個工具累積的去重名稱集合
        if expired_names_set:
            sorted_names = sorted(expired_names_set)  # 排序讓輸出穩定
            expired_footer = (
                "\n---\n"
                "⚠️ **已過期食材提醒**\n"
                f"以下食材已過期，**請勿食用且不能用於料理**：{', '.join(sorted_names)}。\n"
                "建議儘速清理冰箱並補充新鮮食材。"
            )
            final_response = final_response + expired_footer
        return {
            "response": final_response,
            "logs": logs
        }
