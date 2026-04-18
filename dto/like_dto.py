from dataclasses import asdict, dataclass
from typing import Any


@dataclass
class Like:
    """Модель лайка"""

    post: int
    person: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Like:
        return cls(**data)
