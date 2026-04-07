from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any
from enum import Enum

class NetworkType(Enum):
    """Типы социальных сетей"""
    VK = "VKontakte"
    TWITTER = "X(Twitter)"
    TELEGRAM = "Telegram"

@dataclass
class Network:
    """Модель социальной сети"""
    id: Optional[int]
    network_name: str
    
    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v is not None}
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Network':
        return cls(**data)

