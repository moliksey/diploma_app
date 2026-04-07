from dataclasses import dataclass, asdict
from typing import Dict, Any, Optional

@dataclass
class Note:
    """Модель поста/заметки"""
    id: Optional[int]
    msg: Optional[str]
    img: Optional[str]
    parent: Optional[int]
    creator: Optional[int]
    external_id: int
    
    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v is not None}
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Note':
        return cls(**data)