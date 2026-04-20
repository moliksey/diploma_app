from dto import Creator, Like, Network, Note
from repository import BaseRepository


class LikeRepository(BaseRepository):
    """Репозиторий для работы с лайками"""

    def like(self, post_id: int, person_id: int) -> bool:
        """Поставить лайк"""
        query = """
            INSERT INTO "like" (post, person)
            VALUES (%s, %s)
            ON CONFLICT (post, person) DO NOTHING
        """
        rows = self.execute_update(query, (post_id, person_id))
        return rows > 0

    def unlike(self, post_id: int, person_id: int) -> bool:
        """Убрать лайк"""
        query = 'DELETE FROM "like" WHERE post = %s AND person = %s'
        rows = self.execute_update(query, (post_id, person_id))
        return rows > 0

    def is_liked(self, post_id: int, person_id: int) -> bool:
        """Проверить, лайкнул ли пользователь пост"""
        query = 'SELECT 1 FROM "like" WHERE post = %s AND person = %s'
        result = self.execute_query(query, (post_id, person_id))
        return len(result) > 0

    def get_post_likes(self, post_id: int, skip: int = 0, limit: int = 100) -> list[Creator]:
        """Получить всех, кто лайкнул пост"""
        query = """
            SELECT c.*, n.network_name
            FROM "like" l
            JOIN creator c ON l.person = c.id
            LEFT JOIN network n ON c.network_type = n.id
            WHERE l.post = %s
            ORDER BY c.id
            LIMIT %s OFFSET %s
        """
        results = self.execute_query(query, (post_id, limit, skip))
        return [Creator.from_dict(r) for r in results]

    def create_many_likes(self, likes: list[Like]) -> bool:
        """Создать много лайков"""
        if not likes or len(likes) < 1:
            return False
        query = """
            INSERT INTO "like" (post, person)
            VALUES (%s, %s)
            ON CONFLICT (post, person) DO NOTHING
        """
        data = [(like.post, like.person) for like in likes]
        rows = self.execute_batch_update(query, data)
        return rows == len(likes)

    def get_user_likes(self, person_id: int, skip: int = 0, limit: int = 100) -> list[Note]:
        """Получить все посты, которые лайкнул пользователь"""
        query = """
            SELECT n.*, c.external_id as creator_external_id
            FROM "like" l
            JOIN note n ON l.post = n.id
            LEFT JOIN creator c ON n.creator = c.id
            WHERE l.person = %s
            ORDER BY n.id DESC
            LIMIT %s OFFSET %s
        """
        results = self.execute_query(query, (person_id, limit, skip))
        return [Note.from_dict(r) for r in results]

    def get_likes_count(self, post_id: int) -> int:
        """Количество лайков у поста"""
        query = 'SELECT COUNT(*) FROM "like" WHERE post = %s'
        result = self.execute_query(query, (post_id,))
        return result[0]["count"] if result else 0

    def get_user_likes_count(self, person_id: int) -> int:
        """Количество лайков пользователя"""
        query = 'SELECT COUNT(*) FROM "like" WHERE person = %s'
        result = self.execute_query(query, (person_id,))
        return result[0]["count"] if result else 0

    def get_likes_count_over_network(self, network: Network):
        query = 'SELECT COUNT(*) FROM "like" l join creator c on l.person=creator.id WHERE creator.network_type = %s'
        result = self.execute_query(query, (network.id,))
        return result[0]["count"] if result else 0

    def get_like_edges_to_process(
        self, network_type: int, skip: int = 0, limit: int = 100
    ) -> tuple[list[tuple[int, int]], int]:
        query = """
            SELECT c.id, cr.id FROM "like" l
            JOIN creator c ON l.person = c.id
            JOIN note n ON l.post = n.id
            JOIN creator cr ON n.creator = cr.id
            WHERE cr.network_type = %s
            ORDER BY cr.id
            LIMIT %s OFFSET %s
        """
        results = self.execute_query(query, (network_type, limit, skip))
        edges = [(row["c.id"], row["cr.id"]) for row in results] if results else []

        new_offset = skip + limit
        return edges, new_offset
