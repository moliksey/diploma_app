from dataclasses import dataclass, asdict
from typing import Dict, Any

@dataclass
class Like:
    """Модель лайка"""
    post: int
    person: int
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Like':
        return cls(**data)