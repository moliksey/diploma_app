from dataclasses import asdict, dataclass
from typing import Any


@dataclass
class Creator:
    """Модель создателя контента"""

    id: int | None
    external_id: int
    is_person: bool
    network_type: int

    def to_dict(self) -> dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v is not None}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Creator:
        return cls(**data)
