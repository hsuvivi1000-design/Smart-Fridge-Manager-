import os
import re
import logging

logger = logging.getLogger(__name__)

# 載入環境變數以支援 .env 檔案
try:
    import dotenv
    dotenv.load_dotenv(override=True)
except ImportError:
    pass

CATEGORIES_LIST = ["蔬菜", "肉類", "海鮮", "水果", "乳製品", "冷凍食品/火鍋料", "調味料", "其他"]

# 本機規則庫：用於在沒有 API Key 或網路異常時作為備援
LOCAL_MAPPING = {
    # 肉類優先
    r".*(肉|排|腸|培根|火腿|雞|鴨|鵝|豬|牛|羊|翅|腿).*": "肉類",
    # 海鮮
    r".*(魚|蝦|蟹|貝|蛤|蚵|軟小卷|魷魚|海帶).*": "海鮮",
    # 蔬菜
    r".*(菜|菇|蘿蔔|筍|椒|茄|瓜|蔥|蒜|薑|豆芽|芹|萵苣|菠菜).*": "蔬菜",
    # 水果
    r".*(橘|蘋|蕉|莓|桃|梨|李|橙|檸|檬|芒果|鳳梨|葡萄).*": "水果",
    # 乳製品
    r".*(奶|乳|起司|芝司|優格|乾酪|奶油).*": "乳製品",
    # 冷凍食品/火鍋料
    r".*(餃|丸|包子|饅頭|薯條|雞塊|火鍋料|冷凍).*": "冷凍食品/火鍋料",
    # 調味料
    r".*(油|鹽|糖|醬|醋|蜜|粉|膏|汁|咖哩).*": "調味料",
}

EXACT_MAPPING = {
    "蘋果": "水果",
    "香蕉": "水果",
    "西瓜": "水果",
    "番茄": "水果",
    "奇異果": "水果",
    "草莓": "水果",
    "牛奶": "乳製品",
    "鮮奶": "乳製品",
    "起司": "乳製品",
    "黃油": "乳製品",
    "雞蛋": "其他",
    "蛋": "其他",
    "豆腐": "其他",
}

def classify_local(name: str) -> str:
    """本機語意規則比對"""
    if name in EXACT_MAPPING:
        return EXACT_MAPPING[name]
    
    for pattern, cat in LOCAL_MAPPING.items():
        if re.search(pattern, name):
            return cat
            
    return "其他"

def classify_ingredient(name: str) -> str:
    """
    透過 Gemini AI 自動判定食材分類。
    若無 API Key 或連線失敗，則降級為本地規則匹配。
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        # 沒有 key 時，本機靜態分類
        return classify_local(name)
        
    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        
        prompt = f"""
        你是一個廚房食材分類助手。請將以下食材名稱分類到以下類別之一：
        蔬菜, 肉類, 海鮮, 水果, 乳製品, 冷凍食品/火鍋料, 調味料, 其他

        食材名稱："{name}"
        請只回答符合上述八分類之一的名稱，不要有任何其他文字、引號、說明或標點符號。
        """
        
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(prompt)
        result = response.text.strip()
        
        # 移除多餘字元與符號
        result = re.sub(r'[^\w\s/]', '', result).strip()
        
        if result in CATEGORIES_LIST:
            return result
        else:
            # 傳回的結果不合規則，使用本機匹配
            return classify_local(name)
            
    except Exception as e:
        # 發生異常，安全降級
        return classify_local(name)
