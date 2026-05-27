from app.expiry_agent import estimate_expiry_date

tests = [
    ("高麗菜", "蔬菜"),
    ("菠菜", "蔬菜"),
    ("胡蘿蔔", "蔬菜"),
    ("馬鈴薯", "蔬菜"),
    ("洋蔥", "蔬菜"),
    ("豬肉", "肉類"),
    ("鮭魚", "海鮮"),
    ("牛奶", "乳製品"),
    ("醬油", "調味料"),
    ("蝦餃", "冷凍食品/火鍋料"),
]

print("=" * 62)
print(f"  食材        一級分類    細分類別              保存天數  到期日")
print("=" * 62)
for name, cat in tests:
    expiry, sub_cat, days = estimate_expiry_date(name, cat, "2026-05-27")
    print(f"  {name:<10} {cat:<10} {sub_cat:<20} {days} 天  {expiry}")
