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

        # 設計 System Prompt (專業大廚與冰箱管家角色，定義決策優先級)
        system_instruction = (
            "你是一位專業的大廚與冰箱大管家 (AI Kitchen Chef Agent)。\n"
            "你的任務是精準管理冰箱庫存、追蹤食材效期，並推薦合適的食譜與產生採買清單。\n"
            "請嚴格遵守以下決策優先流程與規範：\n"
            "1. 當收到使用者請求時，優先呼叫 `get_inventory` 工具檢查冰箱中的現有庫存與數量。\n"
            "2. 取得庫存後，呼叫 `check_expiry` 工具評估所有食材的保存期限與保存狀態。\n"
            "3. 根據現有的食材與即將過期的食材，以及使用者的健康偏好/忌口設定，呼叫 `search_recipes` 工具推薦合適的食譜。\n"
            "4. 檢查推薦食譜所需食材。如果現有庫存不足或缺少食材，主動呼叫 `generate_shopping_list` 工具整理出缺少的食材採買清單。\n"
            "5. 你的回覆必須包含完整的分析思考過程，並在最終將推薦食譜、採買清單以友善的繁體中文呈現給使用者。"
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
        return {
            "response": final_response,
            "logs": logs
        }
