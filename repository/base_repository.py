import psycopg2 
from psycopg2.extras import RealDictCursor
from typing import List, Dict, Any, Tuple
from contextlib import contextmanager

class SocialRepository:
    """Repository for social mining data"""
    def __init__(self, db_params: Dict[str, Any]):
        self.db_params = db_params
    
    @contextmanager
    def _get_connection(self):
        """Контекстный менеджер для соединения с БД"""
        conn = psycopg2.connect(**self.db_params)
        try:
            yield conn
        finally:
            conn.close()
            
    def execute_query(self, query: str, params: tuple = ()) -> List[Dict[str, Any]]:
        """Выполнить SELECT запрос"""
        with self._get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(query, params)
                return cur.fetchall()
    
    def execute_update(self, query: str, params: tuple = ()) -> int:
        """Выполнить INSERT/UPDATE/DELETE запрос"""
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, params)
                conn.commit()
                return cur.rowcount
    
    def execute_insert(self, query: str, params: tuple = ()) -> int:
        """Выполнить INSERT и вернуть ID"""
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, params)
                conn.commit()
                return cur.fetchone()[0] if cur.description else cur.lastrowid
