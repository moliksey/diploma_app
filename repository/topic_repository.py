import json

from dto import *
from repository import SocialRepository


class TopicRepository(SocialRepository):
    """Репозиторий для работы с темами тредов"""

    def save_topic(self, topic_dto: Topic) -> int:
        """
        Сохраняет или обновляет тему треда

        Returns:
            ID записи
        """
        query = """
            INSERT INTO thread_topic (thread_id, topic_id, topic_name, topic_probability, keywords)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (thread_id) DO UPDATE SET
                topic_id = EXCLUDED.topic_id,
                topic_name = EXCLUDED.topic_name,
                topic_probability = EXCLUDED.topic_probability,
                keywords = EXCLUDED.keywords,
                analyzed_at = NOW()
            RETURNING id
        """

        keywords_json = json.dumps(topic_dto.keywords) if topic_dto.keywords else None
        return self.execute_update(
            query,
            (
                topic_dto.thread_id,
                topic_dto.topic_id,
                topic_dto.topic_name,
                topic_dto.topic_probability,
                keywords_json,
            ),
        )

    def get_topic_by_thread_id(self, thread_id: int) -> Topic | None:
        """Получает тему по ID треда"""
        query = """
            SELECT id, thread_id, topic_id, topic_name, topic_probability, keywords, analyzed_at
            FROM thread_topic
            WHERE thread_id = %s
        """

        result = self.execute_query(query, (thread_id,))
        if result:
            return Topic(**result[0])
        return None

    def get_topics_by_topic_id(self, topic_id: int, limit: int = 100) -> list[Topic]:
        """Получает все треды с указанным topic_id"""
        query = """
            SELECT id, thread_id, topic_id, topic_name, topic_probability, keywords, analyzed_at
            FROM thread_topic
            WHERE topic_id = %s
            ORDER BY analyzed_at DESC
            LIMIT %s
        """

        results = self.execute_query(query, (topic_id, limit))
        return [Topic(**row) for row in results]

    def get_all_topics(self, limit: int = 1000, offset: int = 0) -> list[Topic]:
        """Получает все темы тредов с пагинацией"""
        query = """
            SELECT id, thread_id, topic_id, topic_name, topic_probability, keywords, analyzed_at
            FROM thread_topic
            ORDER BY analyzed_at DESC
            LIMIT %s OFFSET %s
        """

        results = self.execute_query(query, (limit, offset))
        return [Topic(**row) for row in results]

    def get_topics_statistics(self) -> list[dict]:
        """
        Получает статистику по темам (сколько тредов в каждой теме, средняя уверенность)
        """
        query = """
            SELECT
                topic_id,
                topic_name,
                COUNT(*) as threads_count,
                AVG(topic_probability) as avg_probability,
                MIN(analyzed_at) as first_seen,
                MAX(analyzed_at) as last_seen
            FROM thread_topic
            WHERE topic_id != -1  -- Исключаем выбросы
            GROUP BY topic_id, topic_name
            ORDER BY threads_count DESC
        """

        return self.execute_query(query)

    def get_outliers(self, limit: int = 100) -> list[Topic]:
        """Получает треды-выбросы (topic_id = -1)"""
        query = """
            SELECT id, thread_id, topic_id, topic_name, topic_probability, keywords, analyzed_at
            FROM thread_topic
            WHERE topic_id = -1
            ORDER BY analyzed_at DESC
            LIMIT %s
        """

        results = self.execute_query(query, (limit,))
        return [Topic(**row) for row in results]

    def delete_topic_by_thread_id(self, thread_id: int) -> bool:
        """Удаляет тему по ID треда"""
        query = "DELETE FROM thread_topic WHERE thread_id = %s"
        rows_affected = self.execute_update(query, (thread_id,))
        return rows_affected > 0

    def update_topic_name(self, topic_id: int, new_name: str) -> int:
        """
        Обновляет название для всех тредов с указанным topic_id
        Returns:
            Количество обновленных записей
        """
        query = """
            UPDATE thread_topic
            SET topic_name = %s
            WHERE topic_id = %s
        """
        return self.execute_update(query, (new_name, topic_id))

    def get_unanalyzed_threads(self, network_id: int, limit: int = 100) -> list[dict]:
        """
        Получает корневые посты (треды), которые ещё не были проанализированы
        """
        query = """
            SELECT
                n.id as thread_id,
                n.msg as content,
                n.creator as creator_id,
                n.created_at
            FROM note n
            LEFT JOIN thread_topic tt ON n.id = tt.thread_id
            WHERE n.parent IS NULL  -- Только корневые посты
                AND n.msg IS NOT NULL
                AND n.msg != ''
                AND n.creator IN (SELECT id FROM creator WHERE network_type = %s)
                AND tt.id IS NULL   -- Нет в таблице тем
            ORDER BY n.created_at DESC
            LIMIT %s
        """

        return self.execute_query(query, (network_id, limit))
