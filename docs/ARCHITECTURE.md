# AI 冰箱大管家 (AI Kitchen Chef Agent) - 系統架構說明書

## 1. 系統架構 (System Architecture)

系統採用輕量化模組設計，基於 Python 與 SQLite 建立庫存管理核心，並透過 AI Classifier 分類器模組介接外部大語言模型（LLM）。同時，結合大廚規劃者（Chef Agent）與智慧採買助理（Shopping Agent），以 ChromaDB 向量庫支援食譜 RAG 檢索，並基於庫存臨界值與食譜缺件生成個人化採買清單。

```mermaid
graph TD
    User([👤 使用者]) <--> UI[💻 Streamlit Web UI]

    subgraph Core Agent System [核心代理系統]
        Manager[InventoryAgent 核心]
        Classifier[AI Classifier 分類器]
        DB[Database Helper 資料庫模組]
        Chef[ChefAgent 規劃者]
        Shopping[ShoppingAgent / Tools]
    end

    subgraph External Service [外部服務]
        LLM[🤖 Gemini API / LLM]
    end

    subgraph Database [資料儲存]
        SQLite[(fridge_inventory.db)]
        VectorDB[(ChromaDB 向量庫)]
    end

    UI <--> Chef
    UI <--> Manager
    Chef <--> Manager
    Chef <--> Shopping
    Chef <--> LLM
    Manager <--> Classifier
    Classifier <--> LLM
    Manager <--> DB
    DB <--> SQLite
    Chef <--> VectorDB
```

### 模組說明：
1.  **UI 介面層**：以 Streamlit Web 介面對接使用者，提供庫存監控、快速入庫、偏好設定、以及 AI 對話工作台與執行歷程追蹤 (Tool trace)。
2.  **InventoryAgent 核心**：控制核心業務邏輯，包含防錯單位查驗、安全存量設定、資料操作（新增、讀取、更新、刪除）流程分發。
3.  **AI Classifier 模組**：自動判定輸入食材所屬的分類別。若有設定 `GEMINI_API_KEY`，則調用 Gemini 模型；若無，則採用內建 Regex 語意庫進行本地分類，保障系統不崩潰。
4.  **ChefAgent 規劃者**：作為對話中樞，根據使用者意圖調用庫存查詢、效期診斷、食譜推薦與採買清單生成等工具。
5.  **ShoppingAgent / Tools**：負責比對食譜食材缺件及篩選冰箱中低於安全臨界值 (`min_quantity`) 的食材，結合預算狀態產生個人化採買清單。
6.  **Database 模組**：透過 Context Manager 管理 SQLite 連線，並在資料庫內建立 `inventory`（庫存表，含 `min_quantity` 臨界值欄位）與 `action_history`（歷史異動表）兩張資料表。

---

## 2. 資料流 (Data Flow)

### 2.1 食材入庫與自動分類資料流
```mermaid
sequenceDiagram
    autonumber
    actor User as 👤 使用者
    participant UI as 💻 CLI / Web 介面
    participant Agent as 📦 InventoryAgent
    participant Classify as 🧠 Classifier
    participant LLM as 🤖 Gemini API
    participant DB as 💾 SQLite

    User->>UI: 輸入食材名稱 (如: 高麗菜)
    UI->>Classify: 呼叫 classify_ingredient("高麗菜")
    alt 檢測到 GEMINI_API_KEY
        Classify->>LLM: 傳送 Prompt 進行分類
        LLM-->>Classify: 回傳結果 (如: 蔬菜)
    else 無 API Key (本地降級)
        Classify->>Classify: 執行 Regex 匹配 (包含 "菜" -> 蔬菜)
    end
    Classify-->>UI: 回傳類別「蔬菜」
    UI->>User: 詢問「分類正確嗎？(按 Enter 預設正確)」
    User-->>UI: 按下 Enter 確認
    UI->>UI: 輸入數量、單位 (克/公斤/毫克/公升)、安全存量臨界值、到期日
    UI->>Agent: 呼叫 add_ingredient(...)
    Agent->>DB: 寫入 inventory (食材資料，含 min_quantity)
    Agent->>DB: 寫入 action_history (動作: ADD)
    Agent-->>UI: 回傳成功 ID
    UI->>User: 顯示「高麗菜已成功入庫！」
```

### 2.2 食材消耗與歷史紀錄資料流
```mermaid
sequenceDiagram
    autonumber
    actor User as 👤 使用者
    participant UI as 💻 CLI / Web 介面
    participant Agent as 📦 InventoryAgent
    participant DB as 💾 SQLite

    User->>UI: 選擇消耗食材並輸入編號與數量
    UI->>Agent: 呼叫 consume_ingredient(item_id, amount)
    Agent->>DB: 查詢該食材剩餘庫存
    DB-->>Agent: 回傳目前庫存量
    alt 庫存量不足
        Agent-->>UI: 拋出 ValueError("庫存不足")
        UI-->>User: 顯示錯誤提示，阻斷異動
    else 庫存量充足
        Agent->>DB: 更新庫存數量 (UPDATE inventory)
        Agent->>DB: 寫入 action_history (動作: CONSUME)
        Agent-->>UI: 回傳更新成功
        UI->>User: 顯示消耗成功及剩餘數量
    end
```

### 2.3 採買清單與食譜匹配資料流
```mermaid
sequenceDiagram
    autonumber
    actor User as 👤 使用者
    participant UI as 💻 Web 介面
    participant Chef as 🤖 ChefAgent
    participant Inv as 📦 InventoryAgent
    participant RAG as 📚 RecipeMatcher
    participant Shop as 🛒 ShoppingAgent/Tools
    participant DB as 💾 SQLite

    User->>UI: 詢問「我想煮高麗菜炒豬肉，幫我整理採買清單」或「冰箱有什麼推薦食譜？」
    UI->>Chef: 傳送使用者對話與飲食偏好
    Chef->>Inv: 呼叫 get_inventory() 取得冰箱庫存
    Inv->>DB: 查詢庫存 (SELECT * FROM inventory)
    DB-->>Inv: 回傳現有食材列表 (含 name, quantity, unit, min_quantity)
    Inv-->>Chef: 回傳冰箱所有食材資料
    
    Chef->>Chef: 識別低庫存食材 (當 quantity <= min_quantity 且 min_quantity > 0)
    
    Chef->>RAG: 呼叫 search_recipes(現有食材, 偏好/忌口)
    RAG-->>Chef: 回傳匹配的食譜 (所需食材與數量)
    
    Chef->>Chef: 比對食譜所需食材與現有庫存，計算不足之差額 (Deficit)
    
    Chef->>Shop: 呼叫 generate_shopping_list(缺料食材, 低庫存食材, 預算狀態)
    Shop-->>Chef: 回傳格式化的 Markdown 採買清單及結構化項目
    
    Chef-->>UI: 回傳大廚推薦回覆 (含食譜步驟與 Markdown 採買清單)
    UI->>User: 在對話工作台渲染 AI 回覆，並同步更新「採買清單」看板
```
��/公斤/毫克/公升)、到期日
    UI->>Agent: 呼叫 add_ingredient(...)
    Agent->>DB: 寫入 inventory (食材資料)
    Agent->>DB: 寫入 action_history (動作: ADD)
    Agent-->>UI: 回傳成功 ID
    UI->>User: 顯示「高麗菜已成功入庫！」
```

### 2.2 食材消耗與歷史紀錄資料流
```mermaid
sequenceDiagram
    autonumber
    actor User as 👤 使用者
    participant UI as 💻 CLI 介面
    participant Agent as 📦 InventoryAgent
    participant DB as 💾 SQLite

    User->>UI: 選擇消耗食材並輸入編號與數量
    UI->>Agent: 呼叫 consume_ingredient(item_id, amount)
    Agent->>DB: 查詢該食材剩餘庫存
    DB-->>Agent: 回傳目前庫存量
    alt 庫存量不足
        Agent-->>UI: 拋出 ValueError("庫存不足")
        UI-->>User: 顯示錯誤提示，阻斷異動
    else 庫存量充足
        Agent->>DB: 更新庫存數量 (UPDATE inventory)
        Agent->>DB: 寫入 action_history (動作: CONSUME)
        Agent-->>UI: 回傳更新成功
        UI->>User: 顯示消耗成功及剩餘數量
    end
```

---

## 3. Agent 流程 (Agent Flow)
整個「冰箱大管家」系統規劃由多個協作的子 Agent 組成，分工如下：
1.  **Inventory Agent (本次實作)**：專注在庫存的 CRUD、單位控制、與寫入 SQLite 資料庫持久化紀錄。
2.  **Expiry Agent (預估保存期限)**：根據食材分類（例如葉菜類 vs 根莖類）動態計算不同的預設保存期限，並診斷出高價位快過期的食材，主動警示使用者。
3.  **Chef Agent (食譜推薦與過濾)**：使用 RAG 結合向量資料庫，以現有庫存食材為基礎，在 Prompt 中載入使用者健康喜好、忌口設定（Memory Agent）來自動產生食譜。
4.  **Shopping Agent (智慧採買)**：分析冰箱內即將用完的佐料、食材，或者針對欲烹飪食譜中所缺少的材料，自動整理出可導出的分組採買清單。

---

## 4. 工具清單 (Tool List)

| 工具函數 / 方法名稱 | 所屬模組 | 參數定義 | 描述說明 |
| :--- | :--- | :--- | :--- |
| `init_db()` | `database.py` | 無 | 初始化 SQLite 資料庫，建立 `inventory` 與 `action_history` 資料表。 |
| `execute_query(query, params, fetch)` | `database.py` | `query` (str), `params` (tuple), `fetch` (bool) | 通用 SQL 執行輔助函數，具備 Context 關閉管理與 Row 映射字典。 |
| `classify_ingredient(name)` | `classifier.py` | `name` (str) | 自動分類核心：混合式檢索，支援 Gemini 模型呼叫與 Regex 本地降級庫。 |
| `add_ingredient(name, category, ...)` | `inventory_agent.py` | `name`, `category`, `quantity`, `unit`, `purchase_date`, `expiry_date`, `min_quantity` | **C**reate 食材入庫，含單位防錯與自訂或智慧安全水位警示設定。 |
| `update_min_quantity(item_id, min_qty)` | `inventory_agent.py` | `item_id` (int), `min_qty` (float) | **U**pdate 更新食材的安全存量臨界值。 |
| `get_all_inventory()` | `inventory_agent.py` | 無 | **R**ead 取得冰箱現有庫存所有品項（含 safety threshold 水位資訊）。 |
| `get_ingredient(item_id)` | `inventory_agent.py` | `item_id` (int) | **R**ead 查詢單一食材詳細屬性。 |
| `update_quantity(item_id, qty)` | `inventory_agent.py` | `item_id` (int), `qty` (float) | **U**pdate 手動調整庫存數量。 |
| `consume_ingredient(item_id, amount)` | `inventory_agent.py` | `item_id` (int), `amount` (float) | **U**pdate 扣減食材消耗，含餘額不足防護機制。 |
| `delete_ingredient(item_id)` | `inventory_agent.py` | `item_id` (int) | **D**elete 丟棄/移除食材。 |
| `get_expiring_ingredients(date)` | `inventory_agent.py` | `date` (str) | 篩選出到期日小於或等於指定日期的快過期食材。 |
| `get_action_history()` | `inventory_agent.py` | 無 | 讀取所有異動紀錄（依據主鍵 `id DESC` 確保精準排序）。 |
| `log_action(type, name, qty, ...)` | `inventory_agent.py` | `type`, `name`, `qty`, `unit`, `details` | 將任何食材的異動日誌存入資料庫以供備查。 |

