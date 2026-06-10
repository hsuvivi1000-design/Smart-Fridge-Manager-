# -*- coding: utf-8 -*-
import sys
import os
from dotenv import load_dotenv

# 修正 Windows cmd/PowerShell 的 UTF-8 顯示與輸入
try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stdin.reconfigure(encoding='utf-8')
except AttributeError:
    pass  # 部分舊版 Python 不支援

# 讀取環境變數
load_dotenv()

from agents.chef_planner import ChefAgent

def main():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("❌ 錯誤：未在 .env 檔案中偵測到 GEMINI_API_KEY，請先設定您的 API 金鑰。")
        return

    print("==================================================")
    print("🧊 歡迎進入 AI 冰箱大管家對話測試工具 (CLI 版本) 🧊")
    print("提示：輸入 'exit' 或 'quit' 可以隨時退出對話。")
    print("==================================================")
    
    # 建立大廚規劃者代理
    agent = ChefAgent()
    
    while True:
        try:
            # 讀取使用者輸入
            user_input = input("\n👤 使用者: ").strip()
            if not user_input:
                continue
            if user_input.lower() in ['exit', 'quit']:
                print("👋 感謝使用，掰掰！")
                break
                
            print("🤖 AI 大廚管家正在思考與呼叫工具中...")
            result = agent.run(user_input)
            
            # 列印工具執行軌跡 (Thought & Action)
            logs = result.get("logs", [])
            if logs:
                print("\n🛠️ [大廚規劃軌跡 (Tool Calling Logs)]")
                for i, log in enumerate(logs, 1):
                    tool_name = log.get("action", {}).get("tool", "未知")
                    tool_args = log.get("action", {}).get("args", {})
                    print(f"  第 {i} 步：呼叫 `{tool_name}`，參數：{tool_args}")
                print("--------------------------------------------------")
            
            # 列印 AI 最終回答
            print(f"\n🤖 AI 大廚管家:\n{result['response']}")
            
        except KeyboardInterrupt:
            print("\n👋 對話已中斷退出。")
            break
        except Exception as e:
            print(f"\n❌ 執行時發生錯誤：{e}")

if __name__ == "__main__":
    main()
