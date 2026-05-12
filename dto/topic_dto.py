from dataclasses import dataclass
from datetime import datetime


@dataclass
class Topic:
    """DTO для метаданных темы"""

    topic_id: int
    topic_name: str | None = None
    keywords: list[dict[str, float]] | None = None
    created_at: datetime | None = None
    id: int | None = None

    def __post_init__(self):
        """Преобразуем keywords в список словарей, если пришёл JSON"""
        if isinstance(self.keywords, str):
            import json

            self.keywords = json.loads(self.keywords)

    def to_dict(self) -> dict:
        """Преобразует DTO в словарь для вставки в БД"""
        import json

        result = {
            "topic_id": self.topic_id,
            "topic_name": self.topic_name,
        }

        if self.keywords:
            result["keywords"] = json.dumps(self.keywords)

        if self.created_at:
            result["created_at"] = self.created_at

        return result


@dataclass
class NoteTopic:
    """DTO для связи пост-тема"""

    note_id: int
    topic_id: int
    topic_probability: float
    is_thread_based: bool = True
    analyzed_at: datetime | None = None
    id: int | None = None

    def to_dict(self) -> dict:
        """Преобразует DTO в словарь для вставки в БД"""
        result = {
            "note_id": self.note_id,
            "topic_id": self.topic_id,
            "topic_probability": self.topic_probability,
            "is_thread_based": self.is_thread_based,
        }

        if self.analyzed_at:
            result["analyzed_at"] = self.analyzed_at

        return result
