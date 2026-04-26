from typing import Any

from dto import Creator, Network
from repository.base_repository import BaseRepository


class CreatorRepository(BaseRepository):
    """Репозиторий для работы с создателями контента"""

    def create(self, creator: Creator) -> Creator:
        """Создать актора"""
        query = """
            INSERT INTO creator (external_id, is_person, network_type)
            VALUES (%s, %s, %s) ON CONFLICT (external_id)
            DO NOTHING
            RETURNING id
        """
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (creator.external_id, creator.is_person, creator.network_type))
                conn.commit()
                creator.id = cur.fetchone()[0]
                return creator

    def create_many_creators(self, creators: list[Creator]) -> list[Creator]:
        """Массовое создание акторов (оптимизировано)"""
        query = """
            INSERT INTO creator (external_id, is_person, network_type)
            VALUES (%s, %s, %s)
            ON CONFLICT (external_id)
            DO NOTHING
            RETURNING id
        """
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                # Подготавливаем данные
                values = [(c.external_id, c.is_person, c.network_type) for c in creators]

                # Массовая вставка
                cur.executemany(query, values)
                conn.commit()

                # Получаем все возвращенные ID
                results = cur.fetchall()

                # Обновляем ID в объектах
                for i, creator in enumerate(creators):
                    if i < len(results):
                        creator.id = results[i][0]

                return creators

    def get_by_id(self, creator_id: int) -> Creator | None:
        """Получить актора по ID"""
        query = """
            SELECT c.*, n.network_name
            FROM creator c
            LEFT JOIN network n ON c.network_type = n.id
            WHERE c.id = %s
        """
        result = self.execute_query(query, (creator_id,))
        return Creator.from_dict(result[0]) if result else None

    def get_by_external_id(self, external_id: int, network_type: int) -> Creator | None:
        """Получить актора по внешнему ID и типу сети"""
        query = """
            SELECT * FROM creator
            WHERE external_id = %s AND network_type = %s
        """
        result = self.execute_query(query, (external_id, network_type))
        return Creator.from_dict(result[0]) if result else None

    def get_all(self, skip: int = 0, limit: int = 100) -> list[Creator]:
        """Получить всех акторов"""
        query = """
            SELECT c.*, n.network_name
            FROM creator c
            LEFT JOIN network n ON c.network_type = n.id
            ORDER BY c.id LIMIT %s OFFSET %s
        """
        results = self.execute_query(query, (limit, skip))
        return [Creator.from_dict(r) for r in results]

    def get_persons_by_network(
        self, network_type: int, skip: int = 0, limit: int = 100
    ) -> list[Creator]:
        """Получить пользователей по типу сети"""
        query = """
                SELECT * FROM creator
                WHERE network_type = %s
                AND is_person =  true
                ORDER BY id
                LIMIT %s OFFSET %s
                """
        results = self.execute_query(query, (network_type, limit, skip))
        return [Creator.from_dict(r) for r in results]

    def get_by_network(self, network_type: int, skip: int = 0, limit: int = 100) -> list[Creator]:
        """Получить акторов по типу сети"""
        query = """
            SELECT * FROM creator
            WHERE network_type = %s
            ORDER BY id LIMIT %s OFFSET %s
        """
        results = self.execute_query(query, (network_type, limit, skip))
        return [Creator.from_dict(r) for r in results]

    def get_persons(self, skip: int = 0, limit: int = 100) -> list[Creator]:
        """Получить только людей"""
        query = """
            SELECT * FROM creator
            WHERE is_person = true
            ORDER BY id LIMIT %s OFFSET %s
        """
        results = self.execute_query(query, (limit, skip))
        return [Creator.from_dict(r) for r in results]

    def get_channels(self, skip: int = 0, limit: int = 100) -> list[Creator]:
        """Получить только каналы/паблики"""
        query = """
            SELECT * FROM creator
            WHERE is_person = false
            ORDER BY id LIMIT %s OFFSET %s
        """
        results = self.execute_query(query, (limit, skip))
        return [Creator.from_dict(r) for r in results]

    def get_unique_interactors_count(self, creator_id: int) -> int:
        """
        Возвращает количество уникальных пользователей, взаимодействовавших с creator_id:
        - подписчики (subscriber)
        - те, кто лайкнул его посты
        - те, кто оставил комментарии под его постами
        """
        query = """
            WITH user_posts AS (
                -- Получаем все посты пользователя
                SELECT id FROM note
                WHERE creator = %s
            ),
            unique_interactors AS (
                -- Подписчики (кто подписан на этого пользователя)
                SELECT subscriber AS actor_id
                FROM sub
                WHERE contentmaker = %s

                UNION

                -- Лайкнувшие его посты
                SELECT DISTINCT l.person AS actor_id
                FROM "like" l
                INNER JOIN user_posts up ON l.post = up.id

                UNION

                -- Комментаторы (авторы заметок, у которых parent = пост пользователя)
                SELECT DISTINCT n.creator AS actor_id
                FROM note n
                INNER JOIN user_posts up ON n.parent = up.id
                WHERE n.creator IS NOT NULL
            )
            SELECT COUNT(DISTINCT actor_id) FROM unique_interactors
            WHERE actor_id IS NOT NULL
        """
        result = self.execute_query(query, (creator_id, creator_id))
        return result[0]["count"] if result else 0

    def get_unique_interactors(self, creator_id: int) -> int:
        """
        Возвращает количество уникальных пользователей, взаимодействовавших с creator_id:
        - подписчики (subscriber)
        - те, кто лайкнул его посты
        - те, кто оставил комментарии под его постами
        """
        query = """
            WITH user_posts AS (
                -- Получаем все посты пользователя
                SELECT id FROM note
                WHERE creator = %s
            ),
            unique_interactors AS (
                -- Подписчики (кто подписан на этого пользователя)
                SELECT subscriber AS actor_id
                FROM sub
                WHERE contentmaker = %s

                UNION

                -- Лайкнувшие его посты
                SELECT DISTINCT l.person AS actor_id
                FROM "like" l
                INNER JOIN user_posts up ON l.post = up.id

                UNION

                -- Комментаторы (авторы заметок, у которых parent = пост пользователя)
                SELECT DISTINCT n.creator AS actor_id
                FROM note n
                INNER JOIN user_posts up ON n.parent = up.id
                WHERE n.creator IS NOT NULL
            )
            SELECT DISTINCT actor_id FROM unique_interactors
            WHERE actor_id IS NOT NULL
        """
        result = self.execute_query(query, (creator_id, creator_id))
        return result["actor_id"]

    def update(self, creator_id: int, **kwargs) -> Creator | None:
        """Обновить данные актора"""
        allowed_fields = ["external_id", "is_person", "network_type"]
        updates = {k: v for k, v in kwargs.items() if k in allowed_fields}

        if not updates:
            return self.get_by_id(creator_id)

        set_clause = ", ".join([f"{k} = %s" for k in updates.keys()])
        values = list(updates.values()) + [creator_id]

        query = f"UPDATE creator SET {set_clause} WHERE id = %s"
        rows = self.execute_update(query, tuple(values))
        return self.get_by_id(creator_id) if rows > 0 else None

    def delete(self, creator_id: int) -> bool:
        """Удалить актора"""
        query = "DELETE FROM creator WHERE id = %s"
        rows = self.execute_update(query, (creator_id,))
        return rows > 0

    def count_by_network(self, network_type: int) -> int:
        """Количество акторов в сети"""
        query = "SELECT COUNT(*) FROM creator WHERE network_type = %s"
        result = self.execute_query(query, (network_type,))
        return result[0]["count"] if result else 0

    def count_people_by_network(self, network_type: int) -> int:
        """Количество акторов в сети"""
        query = "SELECT COUNT(*) FROM creator WHERE network_type = %s and is_person =  true"
        result = self.execute_query(query, (network_type,))
        return result[0]["count"] if result else 0

    def get_users_to_process(
        self, network: Network, limit: int = 1000, offset: int = 0, isperson: bool = True
    ) -> tuple[list[Creator], int]:
        """Получает пользователей из базы для обработки"""
        if isperson:
            result = self.get_persons_by_network(network.id, offset, limit)
        else:
            result = self.get_by_network(network.id, offset, limit)

        new_offset = offset + limit
        return result, new_offset

    def get_statistics(self) -> dict[str, Any]:
        """Получить статистику по акторам"""
        query = """
            SELECT
                COUNT(*) as total_creators,
                COUNT(CASE WHEN is_person = true THEN 1 END) as persons,
                COUNT(CASE WHEN is_person = false THEN 1 END) as channels,
                n.network_name,
                COUNT(*) as count_per_network
            FROM creator c
            LEFT JOIN network n ON c.network_type = n.id
            GROUP BY n.network_name
        """
        results = self.execute_query(query)
        return {
            "total": sum(r["total_creators"] for r in results) if results else 0,
            "persons": results[0]["persons"] if results else 0,
            "channels": results[0]["channels"] if results else 0,
            "by_network": {r["network_name"]: r["count_per_network"] for r in results},
        }
