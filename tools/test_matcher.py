from recipe_matcher import RecipeMatcher
import json

def test():
    print("初始化 RecipeMatcher...")
    matcher = RecipeMatcher()
    
    # 測試情境 1: 正常檢索
    print("\n--- 測試 1: 正常檢索 ---")
    current = ["高麗菜"]
    dislikes = []
    expiring = ["豬肉"]
    print(f"輸入 -> 現有: {current}, 忌口: {dislikes}, 快過期: {expiring}")
    
    res1 = matcher.match_recipes(current_ingredients=current, dislikes=dislikes, expiring_ingredients=expiring, top_k=2)
    print("推薦結果:")
    for i, r in enumerate(res1):
        print(f" {i+1}. {r['title']} (分數: {r['score']:.4f})")
        print(f"    食材: {', '.join(r['ingredients'])}")
        
    # 測試情境 2: 忌口過濾
    print("\n--- 測試 2: 忌口過濾 (不吃豬肉) ---")
    current = ["高麗菜"]
    dislikes = ["豬肉"]
    expiring = []
    print(f"輸入 -> 現有: {current}, 忌口: {dislikes}, 快過期: {expiring}")
    
    res2 = matcher.match_recipes(current_ingredients=current, dislikes=dislikes, expiring_ingredients=expiring, top_k=3)
    print("推薦結果:")
    for i, r in enumerate(res2):
        print(f" {i+1}. {r['title']} (分數: {r['score']:.4f})")
        print(f"    食材: {', '.join(r['ingredients'])}")
        # 驗證是否真的沒有豬肉
        assert not any("豬肉" in ing for ing in r['ingredients']), f"錯誤！推薦食譜 {r['title']} 包含了忌口食材！"
        
    print("\n測試通過！RecipeMatcher 運作正常。")

if __name__ == "__main__":
    test()
