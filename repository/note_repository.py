from typing import Any

from dto.network_dto import Network
from dto.note_dto import Note
from repository.base_repository import SocialRepository


class NoteRepository(SocialRepository):
    """Репозиторий для работы с постами"""

    def create(self, note: Note) -> Note:
        """Создать пост"""
        query = """
            INSERT INTO note (msg, img, parent, creator, external_id)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
        """
        note.id = self.execute_query(
            query, (note.msg, note.img, note.parent, note.creator, note.external_id)
        )
        return note

    def create_many_posts(self, notes: list[Note]) -> Note:
        """Создать посты"""
        if not notes or len(notes) < 1:
            return False
        query = """
            INSERT INTO note (msg, img, parent, creator, external_id)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
        """
        data = [(note.msg, note.img, note.parent, note.creator, note.external_id) for note in notes]
        rows = self.execute_batch_update(query, data)
        return rows == len(notes)

    def get_by_network(self, network_type: int, skip: int = 0, limit: int = 100) -> list[Note]:
        """Получить акторов по типу сети"""
        query = """
            SELECT note.id, note.msg, note.img, note.parent, note.creator, note.external_i
            FROM creator join note on note.creator=creator.id
            WHERE network_type = %s
            ORDER BY note.id LIMIT %s OFFSET %s
        """
        results = self.execute_query(query, (network_type, limit, skip))
        return [
            Note(
                r["note.id"],
                r["note.msg"],
                r["note.img"],
                r["note.parent"],
                r["note.creator"],
                r["note.external_id"],
            )
            for r in results
        ]

    def get_posts_to_process(
        self, network: Network, limit: int = 1000, offset: int = 0, isperson: bool = True
    ) -> tuple[list[Note], int]:
        """Получает пользователей из базы для обработки"""
        result = self.get_by_network(network.id, offset, limit)
        new_offset = offset + limit
        return result, new_offset

    def get_by_id(self, note_id: int) -> Note | None:
        """Получить пост по ID"""
        query = """
            SELECT n.*, c.external_id as creator_external_id,
                   c.is_person, nw.network_name
            FROM note n
            LEFT JOIN creator c ON n.creator = c.id
            LEFT JOIN network nw ON c.network_type = nw.id
            WHERE n.id = %s
        """
        result = self.execute_query(query, (note_id,))
        return Note.from_dict(result[0]) if result else None

    def get_by_external_id(self, external_id: int) -> Note | None:
        """Получить пост по внешнему ID"""
        query = "SELECT * FROM note WHERE external_id = %s"
        result = self.execute_query(query, (external_id,))
        return Note.from_dict(result[0]) if result else None

    def get_by_creator(self, creator_id: int, skip: int = 0, limit: int = 100) -> list[Note]:
        """Получить все посты создателя"""
        query = """
            SELECT * FROM note
            WHERE creator = %s
            ORDER BY id DESC
            LIMIT %s OFFSET %s
        """
        results = self.execute_query(query, (creator_id, limit, skip))
        return [Note.from_dict(r) for r in results]

    def get_replies(self, parent_id: int, skip: int = 0, limit: int = 100) -> list[Note]:
        """Получить ответы на пост"""
        query = """
            SELECT * FROM note
            WHERE parent = %s
            ORDER BY id
            LIMIT %s OFFSET %s
        """
        results = self.execute_query(query, (parent_id, limit, skip))
        return [Note.from_dict(r) for r in results]

    def get_replies_count_by_creator(self, creator_id: int) -> int:
        """Получить количество комментариев актора"""
        query = """
            SELECT count(*) FROM note
            WHERE parent IS NOT NULL and creator = %s
        """
        result = self.execute_query(query, (creator_id,))
        return result[0]["count"] if result else 0

    def get_replies_count_by_creator_to_actor(self, creator_id: int, actor_id: int) -> int:
        """Получить ответы на пост"""
        query = query = """
        WITH RECURSIVE comments_hierarchy AS (
            -- Базовый уровень: все посты actor_id
            SELECT
                id,
                creator,
                parent
            FROM note
            WHERE creator = %s

            UNION ALL

            -- Рекурсивно получаем все комментарии и реплаи на эти посты
            SELECT
                n.id,
                n.creator,
                n.parent
            FROM note n
            INNER JOIN comments_hierarchy ch ON n.parent = ch.id
        )
        SELECT COUNT(*)
        FROM comments_hierarchy
        WHERE creator = %s
        """
        result = self.execute_query(query, (actor_id, creator_id))
        return result[0]["count"] if result else 0

    def get_user_comments_count(self, user_id: int) -> int:
        """Получить ответы на пост"""
        query = """
            SELECT count(*) FROM note
            WHERE parent IS NOT NULL
            and creator = %s
        """
        result = self.execute_query(query, (user_id,))
        return result[0]["count"] if result else 0

    def get_thread(self, note_id: int) -> list[Note]:
        """Получить всю ветку обсуждения"""
        query = """
            WITH RECURSIVE thread AS (
                SELECT * FROM note WHERE id = %s
                UNION ALL
                SELECT n.* FROM note n
                INNER JOIN thread t ON n.parent = t.id
            )
            SELECT * FROM thread ORDER BY id
        """
        results = self.execute_query(query, (note_id,))
        return [Note.from_dict(r) for r in results]

    def get_all(self, skip: int = 0, limit: int = 100) -> list[Note]:
        """Получить все посты"""
        query = """
            SELECT n.*, c.external_id as creator_external_id
            FROM note n
            LEFT JOIN creator c ON n.creator = c.id
            ORDER BY n.id DESC
            LIMIT %s OFFSET %s
        """
        results = self.execute_query(query, (limit, skip))
        return [Note.from_dict(r) for r in results]

    def update(self, note_id: int, **kwargs) -> Note | None:
        """Обновить пост"""
        allowed_fields = ["msg", "img"]
        updates = {k: v for k, v in kwargs.items() if k in allowed_fields and v is not None}

        if not updates:
            return self.get_by_id(note_id)

        set_clause = ", ".join([f"{k} = %s" for k in updates.keys()])
        values = list(updates.values()) + [note_id]

        query = f"UPDATE note SET {set_clause} WHERE id = %s"
        rows = self.execute_update(query, tuple(values))
        return self.get_by_id(note_id) if rows > 0 else None

    def delete(self, note_id: int) -> bool:
        """Удалить пост (каскадно удалит все ответы)"""
        query = "DELETE FROM note WHERE id = %s"
        rows = self.execute_update(query, (note_id,))
        return rows > 0

    def get_comments_count_over_network(self, network: Network):
        query = "SELECT COUNT(*) FROM note n join creator c on n.creator=c.id WHERE parent IS NOT NULL and c.network_type = %s"
        result = self.execute_query(query, (network.id,))
        return result[0]["count"] if result else 0

    def get_comment_edges_to_process(
        self, network_type: int, skip: int = 0, limit: int = 100
    ) -> tuple[list[tuple[int, int]], int]:
        query = """
            SELECT c.id, cr.id FROM note n
            join creator c on n.creator=c.id
            JOIN note no ON n.parent = no.id
            JOIN creator cr ON no.creator = cr.id
            WHERE cr.network_type = %s
            ORDER BY cr.id
            LIMIT %s OFFSET %s
        """
        results = self.execute_query(query, (network_type, limit, skip))
        edges = [(row["c.id"], row["cr.id"]) for row in results] if results else []

        new_offset = skip + limit
        return edges, new_offset

    def save_topic(self, topic_dto) -> int:
        """
        Сохраняет метаданные темы
        """
        query = """
            INSERT INTO topic (topic_id, topic_name, keywords)
            VALUES (%s, %s, %s)
            ON CONFLICT (topic_id) DO UPDATE SET
                topic_name = EXCLUDED.topic_name,
                keywords = EXCLUDED.keywords
            RETURNING id
        """
        import json
        keywords_json = json.dumps(topic_dto.keywords) if topic_dto.keywords else None
        result = self.execute_query(
            query,
            (
                topic_dto.topic_id,
                topic_dto.topic_name,
                keywords_json,
            ),
        )
        return result[0]["id"] if result else None

    def save_note_topic(self, note_topic_dto) -> int:
        """
        Сохраняет связь пост-тема
        """
        query = """
            INSERT INTO note_topic (note_id, topic_id, topic_probability, is_thread_based)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (note_id) DO UPDATE SET
                topic_id = EXCLUDED.topic_id,
                topic_probability = EXCLUDED.topic_probability,
                analyzed_at = NOW()
            RETURNING id
        """
        result = self.execute_query(
            query,
            (
                note_topic_dto.note_id,
                note_topic_dto.topic_id,
                note_topic_dto.topic_probability,
                note_topic_dto.is_thread_based,
            ),
        )
        return result[0]["id"] if result else None

    def get_threads_to_analize(self, network_id: int, limit: int = 100, offset: int = 0) -> tuple[list[dict], int]:
        """
        Получает корневые посты (треды) для анализа
        """
        query = """
            SELECT
                n.id as id,
                n.msg as msg,
                n.creator as creator,
                n.created_at
            FROM note n
            WHERE n.parent IS NULL  -- Только корневые посты
                AND n.msg IS NOT NULL
                AND n.msg != ''
                AND n.creator IN (SELECT id FROM creator WHERE network_type = %s)
            ORDER BY n.created_at DESC
            LIMIT %s OFFSET %s
        """
        results = self.execute_query(query, (network_id, limit, offset))
        threads = [dict(row) for row in results] if results else []
        new_offset = offset + len(threads)
        return threads, new_offset

    def get_threads_count(self, network_id: int) -> int:
        """
        Получает количество тредов для сети
        """
        query = """
            SELECT COUNT(*) as count
            FROM note n
            WHERE n.parent IS NULL
                AND n.msg IS NOT NULL
                AND n.msg != ''
                AND n.creator IN (SELECT id FROM creator WHERE network_type = %s)
        """
        result = self.execute_query(query, (network_id,))
        return result[0]["count"] if result else 0

    def get_unanalyzed_posts(self, network_id: int, limit: int = 100) -> list[dict]:
        """
        Получает неанализированные посты
        """
        query = """
            SELECT
                n.id,
                n.msg,
                n.parent,
                n.creator,
                n.created_at
            FROM note n
            LEFT JOIN note_topic nt ON n.id = nt.note_id
            WHERE n.msg IS NOT NULL
                AND n.msg != ''
                AND n.creator IN (SELECT id FROM creator WHERE network_type = %s)
                AND nt.id IS NULL
            ORDER BY n.created_at DESC
            LIMIT %s
        """
        results = self.execute_query(query, (network_id, limit))
        return [dict(row) for row in results] if results else []

    def get_topic_metadata(self, topic_ids: list[int]) -> dict[int, dict[str, Any]]:
        """Получить метаданные тем"""
        if not topic_ids:
            return {}

        query = """
            SELECT topic_id, topic_name, keywords
            FROM topic
            WHERE topic_id = ANY(%s)
        """
        results = self.execute_query(query, (topic_ids,))
        return {
            row["topic_id"]: {
                "topic_name": row.get("topic_name"),
                "keywords": row.get("keywords"),
            }
            for row in results
        }

    def get_user_topic_records(self, network_type_id: int) -> list[dict[str, Any]]:
        """Получить пользовательские связи постов с темами"""
        query = """
            SELECT
                n.creator AS creator_id,
                nt.topic_id AS topic_id,
                nt.note_id AS note_id
            FROM note_topic nt
            JOIN note n ON nt.note_id = n.id
            JOIN creator c ON n.creator = c.id
            WHERE c.network_type = %s
        """
        return self.execute_query(query, (network_type_id,))

    def get_likes_by_note(self) -> dict[int, int]:
        """Получить количество лайков по каждому посту"""
        query = """
            SELECT post AS note_id, COUNT(*) AS likes_count
            FROM "like"
            GROUP BY post
        """
        results = self.execute_query(query)
        return {row["note_id"]: row["likes_count"] for row in results}

    def get_comments_by_note(self) -> dict[int, int]:
        """Получить количество комментариев по каждому посту"""
        query = """
            SELECT parent AS note_id, COUNT(*) AS comments_count
            FROM note
            WHERE parent IS NOT NULL
            GROUP BY parent
        """
        results = self.execute_query(query)
        return {row["note_id"]: row["comments_count"] for row in results}
