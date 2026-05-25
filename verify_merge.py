import sys
sys.path.insert(0, '.')

# Test recipe tools fallback
from tools.recipe_tools import _fallback_recipe_search
result = _fallback_recipe_search(["高麗菜", "豬肉"])
print(f"Fallback recipes: {len(result)} found")
for r in result:
    print(f"  - {r['name']}")

# Test shopping tools
from tools.shopping_tools import check_expiry, generate_shopping_list
inventory = [
    {"name": "豬肉", "quantity": 200, "unit": "克", "expiry_date": "2026-05-26"},
    {"name": "高麗菜", "quantity": 1, "unit": "顆", "expiry_date": "2026-05-30"},
]
expiry_result = check_expiry(inventory)
print(f"\nExpiry check: {len(expiry_result)} items")
for item in expiry_result:
    print(f"  - {item['name']}: {item['status']} ({item['days_left']} days)")

# Test shopping list
shopping = generate_shopping_list(
    missing_ingredients=[{"name": "蒜頭", "quantity": 3, "unit": "瓣"}],
    low_stock_ingredients=[],
    budget_status="正常"
)
print(f"\nShopping list generated: {shopping['total_items']} items")
print(shopping['shopping_list_md'])

# Test inventory tools
from tools.inventory_tools import get_inventory, add_ingredient
inv = get_inventory()
print(f"\nCurrent inventory: {len(inv)} items")

print("\n=== All tests passed! ===")
