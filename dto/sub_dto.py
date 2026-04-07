from dataclasses import dataclass, asdict
from typing import Dict, Any

@dataclass
class Sub:
    """Модель подписки"""
    contentmaker: int
    subscriber: int
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Sub':
        return cls(**data)