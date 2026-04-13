from typing import List
from dto.сreator_dto import Creator
from repository.base_repository import BaseRepository
class SubRepository(BaseRepository):
    """Репозиторий для работы с подписками"""
    
    def subscribe(self, contentmaker_id: int, subscriber_id: int) -> bool:
        """Подписаться на создателя"""
        if contentmaker_id == subscriber_id:
            raise ValueError("Нельзя подписаться на самого себя")
        
        query = """
            INSERT INTO sub (contentmaker, subscriber) 
            VALUES (%s, %s)
            ON CONFLICT (contentmaker, subscriber) DO NOTHING
        """
        rows = self.execute_update(query, (contentmaker_id, subscriber_id))
        return rows > 0
    
    def unsubscribe(self, contentmaker_id: int, subscriber_id: int) -> bool:
        """Отписаться от создателя"""
        query = "DELETE FROM sub WHERE contentmaker = %s AND subscriber = %s"
        rows = self.execute_update(query, (contentmaker_id, subscriber_id))
        return rows > 0
    
    def is_subscribed(self, contentmaker_id: int, subscriber_id: int) -> bool:
        """Проверить подписку"""
        query = """
            SELECT 1 FROM sub 
            WHERE contentmaker = %s AND subscriber = %s
        """
        result = self.execute_query(query, (contentmaker_id, subscriber_id))
        return len(result) > 0
    
    def get_subscribers(self, contentmaker_id: int, skip: int = 0, limit: int = 100) -> List[Creator]:
        """Получить подписчиков создателя"""
        query = """
            SELECT c.*, n.network_name
            FROM sub s
            JOIN creator c ON s.subscriber = c.id
            LEFT JOIN network n ON c.network_type = n.id
            WHERE s.contentmaker = %s
            ORDER BY c.id
            LIMIT %s OFFSET %s
        """
        results = self.execute_query(query, (contentmaker_id, limit, skip))
        return [Creator.from_dict(r) for r in results]
    
    def get_subscriptions(self, subscriber_id: int, skip: int = 0, limit: int = 100) -> List[Creator]:
        """Получить на кого подписан пользователь"""
        query = """
            SELECT c.*, n.network_name
            FROM sub s
            JOIN creator c ON s.contentmaker = c.id
            LEFT JOIN network n ON c.network_type = n.id
            WHERE s.subscriber = %s
            ORDER BY c.id
            LIMIT %s OFFSET %s
        """
        results = self.execute_query(query, (subscriber_id, limit, skip))
        return [Creator.from_dict(r) for r in results]
    
    def get_subscribers_count(self, contentmaker_id: int) -> int:
        """Количество подписчиков"""
        query = "SELECT COUNT(*) FROM sub WHERE contentmaker = %s"
        result = self.execute_query(query, (contentmaker_id,))
        return result[0]['count'] if result else 0
    
    def get_subscriptions_count(self, subscriber_id: int) -> int:
        """Количество подписок"""
        query = "SELECT COUNT(*) FROM sub WHERE subscriber = %s"
        result = self.execute_query(query, (subscriber_id,))
        return result[0]['count'] if result else 0
