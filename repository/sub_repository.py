from dto import Creator, Network, Sub
from repository import SocialRepository


class SubRepository(SocialRepository):
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

    def subscribe_for_many(self, actor: Creator, subscriptions: list[Creator]) -> bool:
        if not actor or not subscriptions or len(subscriptions) < 1:
            return False
        query = """
            INSERT INTO sub (contentmaker, subscriber)
            VALUES (%s, %s)
            ON CONFLICT (contentmaker, subscriber) DO NOTHING
        """
        data = [(sub.id, actor.id) for sub in subscriptions]
        rows = self.execute_batch_update(query, data)
        return rows > 0

    def create_friend(self, sub: Sub) -> bool:
        """Взаимная подписка (дружба)"""
        if sub.contentmaker_id == sub.subscriber_id:
            raise ValueError("Нельзя подписаться на самого себя")

        query = """
            INSERT INTO sub (contentmaker, subscriber)
            VALUES (%s, %s)
            ON CONFLICT (contentmaker, subscriber) DO NOTHING
        """
        rows = self.execute_update(query, (sub.contentmaker_id, sub.subscriber_id))
        rows += self.execute_update(query, (sub.subscriber_id, sub.contentmaker_id))
        return rows > 0

    def create_many_friends(self, subs: list[Sub]) -> bool:
        """Пакетная вставка подписок"""
        if not subs:
            return False

        query = """
            INSERT INTO sub (contentmaker, subscriber)
            VALUES (%s, %s)
            ON CONFLICT (contentmaker, subscriber) DO NOTHING
        """
        data = [(sub.contentmaker_id, sub.subscriber_id) for sub in subs]
        data.extend([(sub.subscriber_id, sub.contentmaker_id) for sub in subs])
        rows = self.execute_batch_update(query, data)
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

    def get_subscribers(
        self, contentmaker_id: int, skip: int = 0, limit: int = 100
    ) -> list[Creator]:
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

    def get_subscriptions(
        self, subscriber_id: int, skip: int = 0, limit: int = 100
    ) -> list[Creator]:
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
        return result[0]["count"] if result else 0

    def get_subscriptions_count(self, subscriber_id: int) -> int:
        """Количество подписок"""
        query = "SELECT COUNT(*) FROM sub WHERE subscriber = %s"
        result = self.execute_query(query, (subscriber_id,))
        return result[0]["count"] if result else 0

    def get_subs_count_over_network(self, network: Network):
        query = """SELECT COUNT(*) FROM sub
                join creator on sub.contentmaker=creator.id
                or sub.subscriber=creator.id
                WHERE creator.network_type = %s"""
        result = self.execute_query(query, (network.id,))
        return result[0]["count"] / 2 if result else 0

    def get_subs_by_network(self, network_type: int, skip: int = 0, limit: int = 100) -> list[Sub]:
        """Получить пользователей по типу сети"""
        query = """
                SELECT sub.contentmaker, sub.subscriber FROM sub
                join creator on sub.contentmaker=creator.id
                WHERE creator.network_type = %s
                ORDER BY creator.id
                LIMIT %s OFFSET %s
                """
        results = self.execute_query(query, (network_type, limit, skip))
        return [Sub.from_dict(r) for r in results]

    def get_subs_to_process(
        self, network: Network, limit: int = 1000, offset: int = 0
    ) -> tuple[list[Sub], int]:
        """Получает пользователей из базы для обработки"""
        result = self.get_subs_by_network(network.id, offset, limit)
        new_offset = offset + limit
        return result, new_offset
