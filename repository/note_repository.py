from psycopg2.extras import RealDictCursor
from typing import List, Dict, Any, Tuple
from dto.creator_dto import Note

class NoteRepository(BaseRepository):
    """Репозиторий для работы с постами"""
    
    def create(self, note: Note) -> Note:
        """Создать пост"""
        query = """
            INSERT INTO note (msg, img, parent, creator, external_id) 
            VALUES (%s, %s, %s, %s, %s) 
            RETURNING id
        """
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (
                    note.msg, note.img, note.parent, 
                    note.creator, note.external_id
                ))
                conn.commit()
                note.id = cur.fetchone()[0]
                return note
    
    def get_by_id(self, note_id: int) -> Optional[Note]:
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
    
    def get_by_external_id(self, external_id: int) -> Optional[Note]:
        """Получить пост по внешнему ID"""
        query = "SELECT * FROM note WHERE external_id = %s"
        result = self.execute_query(query, (external_id,))
        return Note.from_dict(result[0]) if result else None
    
    def get_by_creator(self, creator_id: int, skip: int = 0, limit: int = 100) -> List[Note]:
        """Получить все посты создателя"""
        query = """
            SELECT * FROM note 
            WHERE creator = %s 
            ORDER BY id DESC 
            LIMIT %s OFFSET %s
        """
        results = self.execute_query(query, (creator_id, limit, skip))
        return [Note.from_dict(r) for r in results]
    
    def get_replies(self, parent_id: int, skip: int = 0, limit: int = 100) -> List[Note]:
        """Получить ответы на пост"""
        query = """
            SELECT * FROM note 
            WHERE parent = %s 
            ORDER BY id 
            LIMIT %s OFFSET %s
        """
        results = self.execute_query(query, (parent_id, limit, skip))
        return [Note.from_dict(r) for r in results]
    
    def get_thread(self, note_id: int) -> List[Note]:
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
    
    def get_all(self, skip: int = 0, limit: int = 100) -> List[Note]:
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
    
    def update(self, note_id: int, **kwargs) -> Optional[Note]:
        """Обновить пост"""
        allowed_fields = ['msg', 'img']
        updates = {k: v for k, v in kwargs.items() if k in allowed_fields and v is not None}
        
        if not updates:
            return self.get_by_id(note_id)
        
        set_clause = ', '.join([f"{k} = %s" for k in updates.keys()])
        values = list(updates.values()) + [note_id]
        
        query = f"UPDATE note SET {set_clause} WHERE id = %s"
        rows = self.execute_update(query, tuple(values))
        return self.get_by_id(note_id) if rows > 0 else None
    
    def delete(self, note_id: int) -> bool:
        """Удалить пост (каскадно удалит все ответы)"""
        query = "DELETE FROM note WHERE id = %s"
        rows = self.execute_update(query, (note_id,))
        return rows > 0