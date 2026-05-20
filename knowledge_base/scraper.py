import requests
from bs4 import BeautifulSoup
import json
import time

def scrape_icook_search(query, max_pages=1):
    recipes = []
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    print(f"正在搜尋愛料理 (iCook) 關鍵字: {query}")
    
    for page in range(1, max_pages + 1):
        url = f"https://icook.tw/search/{query}/?page={page}"
        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find recipe cards (this structure may change over time on iCook)
            recipe_cards = soup.find_all('li', class_='browse-recipe-item')
            
            for card in recipe_cards:
                try:
                    # Title
                    title_elem = card.find('h2', class_='browse-recipe-name')
                    title = title_elem.text.strip() if title_elem else "未知食譜"
                    
                    # URL
                    link_elem = card.find('a', class_='browse-recipe-link')
                    recipe_url = "https://icook.tw" + link_elem['href'] if link_elem else ""
                    
                    # Ingredients
                    ingredients_elem = card.find('p', class_='browse-recipe-content-ingredient')
                    if ingredients_elem:
                        ingredients_text = ingredients_elem.text.strip()
                        # e.g., "食材：高麗菜、豬肉、醬油" -> extract after "："
                        if "：" in ingredients_text:
                            ingredients_list = [i.strip() for i in ingredients_text.split("：", 1)[1].split("、")]
                        else:
                            ingredients_list = [i.strip() for i in ingredients_text.split("、")]
                    else:
                        ingredients_list = []
                        
                    if title and recipe_url:
                        recipes.append({
                            "title": title,
                            "url": recipe_url,
                            "ingredients": ingredients_list,
                            "steps": [f"請參考詳細食譜頁面: {recipe_url}"] # Placeholder for steps as search page doesn't have full steps
                        })
                except Exception as e:
                    print(f"解析單個食譜時發生錯誤: {e}")
                    continue
                    
            time.sleep(1) # Be polite
        except Exception as e:
            print(f"爬取搜尋頁面失敗 {url}: {e}")
            
    return recipes

def generate_mock_data():
    """Fallback mock data if scraping fails or gets blocked."""
    print("產生模擬食譜資料 (Mock Data)...")
    return [
        {
            "title": "高麗菜炒肉片",
            "url": "https://example.com/recipe/1",
            "ingredients": ["高麗菜", "豬肉", "蒜頭", "鹽", "醬油"],
            "steps": ["1. 高麗菜切塊，豬肉切片。", "2. 熱鍋下油，爆香蒜頭。", "3. 放入豬肉炒至變色。", "4. 加入高麗菜翻炒。", "5. 加入鹽和醬油調味，炒熟即可。"],
            "nutrition": {"calories": 350, "protein": 20, "fat": 25, "carbs": 10}
        },
        {
            "title": "番茄炒蛋",
            "url": "https://example.com/recipe/2",
            "ingredients": ["番茄", "雞蛋", "蔥", "鹽", "糖"],
            "steps": ["1. 番茄切塊，雞蛋打散。", "2. 炒熟雞蛋，盛出備用。", "3. 炒番茄至軟爛出汁。", "4. 加入雞蛋混合，加鹽糖調味。", "5. 撒上蔥花即可。"],
            "nutrition": {"calories": 250, "protein": 15, "fat": 15, "carbs": 12}
        },
        {
            "title": "清炒高麗菜",
            "url": "https://example.com/recipe/3",
            "ingredients": ["高麗菜", "蒜頭", "鹽"],
            "steps": ["1. 高麗菜切塊。", "2. 爆香蒜頭。", "3. 加入高麗菜大火快炒。", "4. 加鹽調味即可。"],
            "nutrition": {"calories": 100, "protein": 2, "fat": 5, "carbs": 8}
        },
        {
            "title": "香辣蒜泥白肉",
            "url": "https://example.com/recipe/4",
            "ingredients": ["豬肉", "蒜末", "醬油", "辣椒", "香油"],
            "steps": ["1. 豬肉燙熟切片。", "2. 混合蒜末、醬油、辣椒、香油成醬汁。", "3. 醬汁淋在豬肉片上。"],
            "nutrition": {"calories": 400, "protein": 25, "fat": 30, "carbs": 5}
        },
        {
            "title": "麻婆豆腐",
            "url": "https://example.com/recipe/5",
            "ingredients": ["豆腐", "豬絞肉", "豆瓣醬", "花椒", "辣椒", "蒜末", "蔥"],
            "steps": ["1. 豆腐切塊。", "2. 炒熟豬絞肉。", "3. 加入豆瓣醬、花椒、辣椒、蒜末爆香。", "4. 加水煮滾，放入豆腐。", "5. 勾芡後撒上蔥花。"],
            "nutrition": {"calories": 450, "protein": 22, "fat": 35, "carbs": 15}
        },
        {
            "title": "生酮蒜香鮭魚",
            "url": "https://example.com/recipe/6",
            "ingredients": ["鮭魚", "蒜末", "橄欖油", "鹽", "黑胡椒"],
            "steps": ["1. 鮭魚兩面撒上鹽與黑胡椒。", "2. 熱鍋下橄欖油，煎熟鮭魚。", "3. 最後加入蒜末爆香即可。"],
            "nutrition": {"calories": 380, "protein": 30, "fat": 28, "carbs": 1}
        },
        {
            "title": "純素花椰菜濃湯",
            "url": "https://example.com/recipe/7",
            "ingredients": ["花椰菜", "馬鈴薯", "燕麥奶", "鹽", "黑胡椒"],
            "steps": ["1. 花椰菜與馬鈴薯切塊蒸熟。", "2. 放入果汁機，加入燕麥奶打成泥。", "3. 倒回鍋中加熱，加鹽與黑胡椒調味。"],
            "nutrition": {"calories": 200, "protein": 6, "fat": 4, "carbs": 30}
        }
    ]

if __name__ == "__main__":
    queries = ["高麗菜", "豬肉", "雞蛋"]
    all_recipes = []
    
    # Attempt to scrape
    for q in queries:
        scraped = scrape_icook_search(q, max_pages=1)
        all_recipes.extend(scraped)
        
    # Deduplicate by URL
    unique_recipes = {r['url']: r for r in all_recipes}.values()
    all_recipes = list(unique_recipes)
    
    # Fallback if scraping gets blocked
    if len(all_recipes) == 0:
        print("無法從網站抓取資料，使用備用(Mock)食譜資料。")
        all_recipes = generate_mock_data()
    else:
        print(f"成功抓取 {len(all_recipes)} 筆食譜資料！")
        
    # Save to JSON
    output_file = "recipes_data.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_recipes, f, ensure_ascii=False, indent=2)
        
    print(f"食譜資料已儲存至 {output_file}")
