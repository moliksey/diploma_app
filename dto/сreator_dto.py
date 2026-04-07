from dataclasses import dataclass, asdict
from typing import Dict, Any, Optional

@dataclass
class Creator:
    """Модель создателя контента"""
    id: Optional[int]
    external_id: int
    is_person: bool
    network_type: int
    
    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v is not None}
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Creator':
        return cls(**data)
