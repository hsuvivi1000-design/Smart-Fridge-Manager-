import chromadb
import json
import os
from chromadb.utils import embedding_functions

# 計算當前檔案所在目錄的上一層，以便正確找到 knowledge_base
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_DB_PATH = os.path.join(BASE_DIR, 'knowledge_base', 'chroma_db')
DEFAULT_PREF_PATH = os.path.join(BASE_DIR, 'knowledge_base', 'user_preferences.json')

class RecipeMatcher:
    def __init__(self, db_path=DEFAULT_DB_PATH, collection_name='recipes'):
        """
        初始化 RecipeMatcher
        """
        self.db_path = db_path
        self.client = chromadb.PersistentClient(path=self.db_path)
        
        # 先檢查 collection 是否存在於資料庫中，避免尚未建置時下載並載入 470MB 模型的卡頓
        collection_exists = False
        try:
            collections = [c.name for c in self.client.list_collections()]
            collection_exists = collection_name in collections
        except Exception:
            pass

        if not collection_exists:
            print(f"無法載入資料庫，請確認 {self.db_path} 是否存在且已執行 build_db.py")
            self.collection = None
            self.ef = None
        else:
            self.ef = embedding_functions.SentenceTransformerEmbeddingFunction(
                model_name="paraphrase-multilingual-MiniLM-L12-v2"
            )
            try:
                self.collection = self.client.get_collection(
                    name=collection_name,
                    embedding_function=self.ef
                )
            except Exception as e:
                print(f"載入 collection {collection_name} 失敗: {e}")
                self.collection = None

    def _get_dietary_dislikes(self, habit: str) -> list:
        # 簡單的飲食習慣對應忌口清單
        habit_mapping = {
            "純素": ["豬", "牛", "雞", "魚", "蝦", "蟹", "海鮮", "蛋", "奶", "蜂蜜", "五辛"],
            "蛋奶素": ["豬", "牛", "雞", "魚", "蝦", "蟹", "海鮮"],
            "生酮": ["米", "麵", "糖", "地瓜", "馬鈴薯", "麵包"]
        }
        for key in habit_mapping:
            if key in habit:
                return habit_mapping[key]
        return []

    def load_user_preferences(self, file_path=DEFAULT_PREF_PATH):
        """讀取使用者偏好文件"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"無法讀取使用者偏好文件: {e}")
            return {}

    def match_recipes(self, current_ingredients: list, dislikes: list, expiring_ingredients: list, top_k: int = 5):
        """
        根據現有食材、忌口清單與即將過期食材，檢索並推薦最適合的食譜。
        
        :param current_ingredients: 現有食材清單 (e.g. ['高麗菜', '雞蛋'])
        :param dislikes: 忌口或過敏清單 (e.g. ['辣椒', '海鮮'])
        :param expiring_ingredients: 即將過期需要優先消耗的食材 (e.g. ['豬肉'])
        :param top_k: 檢索回傳的最大數量
        :return: 推薦食譜的列表
        """
        if not self.collection:
            return {"error": "資料庫未初始化"}
            
        # 載入使用者偏好
        prefs = self.load_user_preferences()
        user_dislikes = prefs.get('dislikes', [])
        dietary_habit = prefs.get('dietary_habit', '')
        health_goal = prefs.get('health_goal', '')
        
        # 合併動態忌口與固定偏好
        all_dislikes = set(dislikes + user_dislikes + self._get_dietary_dislikes(dietary_habit))
            
        # 1. 組合查詢字串 (Query)
        # 為了讓即將過期的食材有較高的權重，我們在查詢中將其重複或特別強調
        query_parts = []
        if expiring_ingredients:
            query_parts.append(f"必須包含 {', '.join(expiring_ingredients)}")
        if current_ingredients:
            query_parts.append(f"可用食材: {', '.join(current_ingredients)}")
        
        # 加入使用者的健康目標來影響語意搜尋結果 (例如：「低卡路里」、「高蛋白」)
        if health_goal or dietary_habit:
            query_parts.append(f"符合目標: {health_goal} {dietary_habit}")
            
        query_string = " ".join(query_parts)
        if not query_string:
            query_string = "隨機食譜" # Fallback if empty
            
        print(f"檢索 Query: {query_string}")

        # 2. 向 ChromaDB 查詢
        # 多取一些結果再來做過濾
        results = self.collection.query(
            query_texts=[query_string],
            n_results=top_k * 3 
        )
        
        recommended_recipes = []
        
        if not results['metadatas'] or not results['metadatas'][0]:
            return []
            
        # 3. 忌口過濾邏輯與排序整理
        for metadata, distance in zip(results['metadatas'][0], results['distances'][0]):
            ingredients_json_str = metadata.get('ingredients', '[]')
            steps_json_str = metadata.get('steps', '[]')
            
            try:
                recipe_ingredients = json.loads(ingredients_json_str)
                recipe_steps = json.loads(steps_json_str)
            except:
                recipe_ingredients = []
                recipe_steps = []
                
            # 將食譜的所有食材轉成一個字串方便比對忌口
            recipe_ing_text = " ".join(recipe_ingredients)
            
            # 檢查是否有忌口食材
            has_dislike = False
            for dislike_item in all_dislikes:
                if dislike_item and (dislike_item in recipe_ing_text or dislike_item in metadata.get('title', '')):
                    has_dislike = True
                    break
                    
            if has_dislike:
                continue # 包含忌口食材，剔除此食譜
                
            # 解析營養成分
            nutrition_json_str = metadata.get('nutrition', '{}')
            try:
                nutrition_data = json.loads(nutrition_json_str)
            except:
                nutrition_data = {}

            # 格式化回傳結果
            recommended_recipes.append({
                "title": metadata.get('title', ''),
                "url": metadata.get('url', ''),
                "ingredients": recipe_ingredients,
                "steps": recipe_steps,
                "nutrition": nutrition_data,
                "score": 1.0 / (1.0 + distance) # 轉換距離為分數
            })
            
            if len(recommended_recipes) >= top_k:
                break
                
        return recommended_recipes

# 快速測試用 (不會被外部 import 執行)
if __name__ == "__main__":
    matcher = RecipeMatcher()
    res = matcher.match_recipes(
        current_ingredients=["高麗菜", "雞蛋"],
        dislikes=["辣椒", "豬肉"],
        expiring_ingredients=["番茄"],
        top_k=2
    )
    print(json.dumps(res, indent=2, ensure_ascii=False))
