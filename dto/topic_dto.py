from dataclasses import dataclass
from datetime import datetime


@dataclass
class Topic:
    """DTO для темы треда"""

    thread_id: int
    topic_id: int
    topic_name: str | None = None
    topic_probability: float | None = None
    keywords: list[dict[str, float]] | None = None
    analyzed_at: datetime | None = None
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
            "thread_id": self.thread_id,
            "topic_id": self.topic_id,
            "topic_name": self.topic_name,
            "topic_probability": self.topic_probability,
        }

        if self.keywords:
            result["keywords"] = json.dumps(self.keywords)

        if self.analyzed_at:
            result["analyzed_at"] = self.analyzed_at

        return result
