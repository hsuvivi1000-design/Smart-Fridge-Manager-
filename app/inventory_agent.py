from app.database import execute_query, init_db
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class InventoryAgent:
    def __init__(self):
        # 確保資料庫與資料表已經初始化
        init_db()

    def log_action(self, action_type: str, ingredient_name: str, quantity: float, unit: str, details: str = None):
        """[Create] 記錄歷史異動到 action_history"""
        query = '''
            INSERT INTO action_history (action_type, ingredient_name, quantity, unit, details)
            VALUES (?, ?, ?, ?, ?)
        '''
        params = (action_type, ingredient_name, quantity, unit, details)
        try:
            execute_query(query, params)
        except Exception as e:
            logger.error(f"❌ 無法記錄歷史異動: {e}")

    def add_ingredient(self, name: str, category: str, quantity: float, unit: str, purchase_date: str, expiry_date: str, status: str = 'fresh', min_quantity: float = None) -> int:
        """
        [Create] 食材入庫
        """
        # 放寬單位限制，支援日常單位
        VALID_UNITS = [
            "克", "公斤", "毫克", "公升", "毫升",
            "個", "顆", "把", "包", "盒", "瓶", "罐",
            "片", "條", "塊", "串", "根", "束", "份",
            "盤", "碗", "杯", "袋", "籃", "粒",
        ]
        if unit not in VALID_UNITS:
            raise ValueError(f"不支援的單位「{unit}」。僅支援：{', '.join(VALID_UNITS)}")

        # 智慧預設安全臨界值
        if min_quantity is None:
            if unit in ["克", "毫克", "毫升"]:
                min_quantity = 100.0
            elif unit in ["公斤", "公升", "個", "顆", "把", "包", "盒", "瓶", "罐", "片", "條", "塊", "串", "根", "束", "份", "盤", "碗", "杯", "袋", "籃", "粒"]:
                min_quantity = 1.0
            else:
                min_quantity = 0.0

        query = '''
            INSERT INTO inventory (name, category, quantity, unit, purchase_date, expiry_date, status, min_quantity)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        '''
        params = (name, category, quantity, unit, purchase_date, expiry_date, status, min_quantity)
        item_id = execute_query(query, params)
        logger.info(f"✅ 食材入庫成功: {name} (ID: {item_id}), 數量: {quantity} {unit}, 安全存量: {min_quantity} {unit}")
        
        # 紀錄歷史
        self.log_action("ADD", name, quantity, unit, f"食材入庫，類別: {category}，安全存量: {min_quantity}")
        return item_id

    def update_min_quantity(self, item_id: int, min_quantity: float):
        """
        [Update] 更新食材安全臨界存量
        """
        item = self.get_ingredient(item_id)
        if not item:
            logger.error(f"❌ 找不到食材 (ID: {item_id})")
            return

        query = '''
            UPDATE inventory 
            SET min_quantity = ?, updated_at = CURRENT_TIMESTAMP 
            WHERE id = ?
        '''
        execute_query(query, (min_quantity, item_id))
        logger.info(f"🔄 食材安全存量更新成功 (ID: {item_id}), 新安全存量: {min_quantity}")
        
        # 紀錄歷史
        self.log_action("UPDATE_MIN_QTY", item['name'], min_quantity, item['unit'], f"更新安全存量臨界值（原安全存量: {item.get('min_quantity', 0.0)} -> 新安全存量: {min_quantity}）")

    def get_all_inventory(self) -> list:
        """
        [Read] 查詢所有庫存
        """
        query = 'SELECT * FROM inventory'
        return execute_query(query, fetch=True)

    def get_ingredient(self, item_id: int) -> dict:
        """
        [Read] 查詢單一食材
        """
        query = 'SELECT * FROM inventory WHERE id = ?'
        result = execute_query(query, (item_id,), fetch=True)
        return result[0] if result else None

    def update_quantity(self, item_id: int, new_quantity: float):
        """
        [Update] 更新食材數量 (覆蓋)
        """
        item = self.get_ingredient(item_id)
        if not item:
            logger.error(f"❌ 找不到食材 (ID: {item_id})")
            return

        old_quantity = item['quantity']
        query = '''
            UPDATE inventory 
            SET quantity = ?, updated_at = CURRENT_TIMESTAMP 
            WHERE id = ?
        '''
        execute_query(query, (new_quantity, item_id))
        logger.info(f"🔄 食材數量更新成功 (ID: {item_id}), 新數量: {new_quantity}")
        
        # 紀錄歷史
        self.log_action("UPDATE_QTY", item['name'], new_quantity, item['unit'], f"手動調整數量（原庫存: {old_quantity}）")

    def update_ingredient(self, item_id: int, category: str, quantity: float, expiry_date: str):
        """
        [Update] 更新食材分類、數量與過期時間
        """
        item = self.get_ingredient(item_id)
        if not item:
            logger.error(f"❌ 找不到食材 (ID: {item_id})")
            return

        query = '''
            UPDATE inventory 
            SET category = ?, quantity = ?, expiry_date = ?, updated_at = CURRENT_TIMESTAMP 
            WHERE id = ?
        '''
        execute_query(query, (category, quantity, expiry_date, item_id))
        logger.info(f"🔄 食材更新成功 (ID: {item_id})")
        
        # 紀錄歷史
        self.log_action("UPDATE_QTY", item['name'], quantity, item['unit'], f"編輯食材（分類: {category}, 數量: {quantity}, 過期日: {expiry_date}）")

    def consume_ingredient(self, item_id: int, amount: float):
        """
        [Update] 消耗食材 (扣減數量)
        """
        item = self.get_ingredient(item_id)
        if not item:
            logger.error(f"❌ 找不到食材 (ID: {item_id})")
            raise ValueError(f"找不到食材 (ID: {item_id})")

        current_quantity = item['quantity']
        if amount > current_quantity:
            logger.error(f"❌ 消耗量 ({amount}) 大於庫存量 ({current_quantity})")
            raise ValueError(f"庫存不足，無法消耗！目前僅剩: {current_quantity} {item['unit']}")

        new_quantity = current_quantity - amount
        
        # 直接執行庫存更新，不透過手動 update_quantity 避免產生重複歷史
        query = '''
            UPDATE inventory 
            SET quantity = ?, updated_at = CURRENT_TIMESTAMP 
            WHERE id = ?
        '''
        execute_query(query, (new_quantity, item_id))
        logger.info(f"🍽️ 食材消耗成功 (ID: {item_id}), 消耗了: {amount} {item['unit']}, 剩餘: {new_quantity} {item['unit']}")
        
        # 紀錄歷史
        self.log_action("CONSUME", item['name'], amount, item['unit'], f"消耗食材，原庫存: {current_quantity} -> 剩餘: {new_quantity}")

    def delete_ingredient(self, item_id: int):
        """
        [Delete] 刪除食材 / 出庫
        """
        item = self.get_ingredient(item_id)
        if item:
            query = 'DELETE FROM inventory WHERE id = ?'
            execute_query(query, (item_id,))
            logger.info(f"🗑️ 食材出庫/刪除成功 (ID: {item_id})")
            
            # 紀錄歷史
            self.log_action("DELETE", item['name'], item['quantity'], item['unit'], "刪除食材/出庫")

    def get_expiring_ingredients(self, target_date: str) -> list:
        """
        [Read] 查詢即將過期或已過期的食材
        """
        query = 'SELECT * FROM inventory WHERE expiry_date <= ?'
        return execute_query(query, (target_date,), fetch=True)

    def get_action_history(self) -> list:
        """
        [Read] 取得所有異動歷史紀錄
        """
        query = 'SELECT * FROM action_history ORDER BY id DESC'
        return execute_query(query, fetch=True)
