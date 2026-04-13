"""Конфигурация приложения"""
import os
from dataclasses import dataclass
from typing import Dict, Any

@dataclass
class DatabaseConfig:
    """Конфигурация подключения к БД"""
    host: str = os.getenv('DB_HOST', 'localhost')
    port: int = int(os.getenv('DB_PORT', 5432))
    database: str = os.getenv('DB_NAME', 'social_network')
    user: str = os.getenv('DB_USER', 'postgres')
    password: str = os.getenv('DB_PASSWORD', 'password')
    
    def to_dict(self) -> Dict[str, Any]:
        """Конвертация в словарь для psycopg2"""
        return {
            'host': self.host,
            'port': self.port,
            'database': self.database,
            'user': self.user,
            'password': self.password
        }

# Глобальная конфигурация
DB_CONFIG = DatabaseConfig()
VK_TOKEN = os.getenv('VK_TOKEN', 'а где?')