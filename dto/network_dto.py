from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any


class NetworkType(Enum):
    """Типы социальных сетей"""

    VK = "VKontakte"
    TWITTER = "X(Twitter)"
    TELEGRAM = "Telegram"


@dataclass
class Network:
    """Модель социальной сети"""

    id: int | None
    network_name: str

    def to_dict(self) -> dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v is not None}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Network:
        return cls(**data)
