from dataclasses import asdict, dataclass
from typing import Any


@dataclass
class Sub:
    """Модель подписки"""

    contentmaker: int
    subscriber: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Sub:
        return cls(**data)
