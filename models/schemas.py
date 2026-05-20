from pydantic import BaseModel, Field
from typing import Optional, List

class Ingredient(BaseModel):
    name: str = Field(..., description="食材名稱，例如: 高麗菜、豬肉")
    quantity: float = Field(..., description="數量")
    unit: str = Field(..., description="單位，例如: g、kg、顆、包")
    purchase_date: Optional[str] = Field(None, description="購買日期，格式為 YYYY-MM-DD")
    expiry_date: Optional[str] = Field(None, description="過期日期，格式為 YYYY-MM-DD")
    category: Optional[str] = Field(None, description="食材類別，例如: 肉類、蔬菜類、海鮮類")

class Recipe(BaseModel):
    name: str = Field(..., description="食譜名稱，例如: 高麗菜炒豬肉")
    ingredients: List[Ingredient] = Field(..., description="所需食材列表")
    instructions: List[str] = Field(..., description="烹飪步驟列表")
    prep_time: Optional[int] = Field(None, description="準備時間，單位為分鐘")
    cook_time: Optional[int] = Field(None, description="烹煮時間，單位為分鐘")
    tags: Optional[List[str]] = Field(None, description="食譜標籤，例如: ['低鹽', '不吃辣', '快速料理']")

class ShoppingItem(BaseModel):
    name: str = Field(..., description="採買食材名稱")
    quantity: float = Field(..., description="建議採買數量")
    unit: str = Field(..., description="單位")
    reason: Optional[str] = Field(None, description="採買原因，例如: '食材即將過期且食譜缺件' 或 '庫存不足'")
