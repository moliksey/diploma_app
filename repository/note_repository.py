from dto.network_dto import Network
from dto.note_dto import Note
from repository.base_repository import BaseRepository


class NoteRepository(BaseRepository):
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
