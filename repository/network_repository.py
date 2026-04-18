from base_repository import BaseRepository

from dto.network_dto import Network


class NetworkRepository(BaseRepository):
    """Репозиторий для работы с социальными сетями"""

    def create(self, network: Network) -> Network:
        """Создать социальную сеть"""
        query = """
            INSERT INTO network (network_name)
            VALUES (%s)
            RETURNING id
        """
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (network.network_name,))
                conn.commit()
                network.id = cur.fetchone()[0]
                return network

    def get_by_id(self, network_id: int) -> Network | None:
        """Получить сеть по ID"""
        query = "SELECT * FROM network WHERE id = %s"
        result = self.execute_query(query, (network_id,))
        return Network.from_dict(result[0]) if result else None

    def get_by_name(self, name: str) -> Network | None:
        """Получить сеть по названию"""
        query = "SELECT * FROM network WHERE network_name = %s"
        result = self.execute_query(query, (name,))
        return Network.from_dict(result[0]) if result else None

    def get_all(self, skip: int = 0, limit: int = 100) -> list[Network]:
        """Получить все сети"""
        query = "SELECT * FROM network ORDER BY id LIMIT %s OFFSET %s"
        results = self.execute_query(query, (limit, skip))
        return [Network.from_dict(r) for r in results]

    def delete(self, network_id: int) -> bool:
        """Удалить сеть"""
        query = "DELETE FROM network WHERE id = %s"
        rows = self.execute_update(query, (network_id,))
        return rows > 0

    def get_or_create(self, network_name: str) -> Network:
        """Получить или создать сеть"""
        existing = self.get_by_name(network_name)
        if existing:
            return existing
        return self.create(Network(id=None, network_name=network_name))

    def createOrIgnore(self, network_name: str):
        """Создать сеть"""
        existing = self.get_by_name(network_name)
        if not existing:
            self.create(Network(id=None, network_name=network_name))
