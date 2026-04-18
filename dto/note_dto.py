from dataclasses import asdict, dataclass
from typing import Any


@dataclass
class Note:
    """Модель поста/заметки"""

    id: int | None
    msg: str | None
    img: str | None
    parent: int | None
    creator: int | None
    external_id: int

    def to_dict(self) -> dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v is not None}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Note:
        return cls(**data)
