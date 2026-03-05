"""
Modèle de données pour une page de stratégies
"""
import uuid
from dataclasses import dataclass, field


@dataclass
class Page:
    """Représente une page/catégorie de stratégies"""
    
    name: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    icon: str = "📊"
    order: int = 0
    
    def to_dict(self) -> dict:
        """Convertit la page en dictionnaire pour la sauvegarde"""
        return {
            'id': self.id,
            'name': self.name,
            'icon': self.icon,
            'order': self.order
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Page':
        """Crée une page depuis un dictionnaire"""
        return cls(
            id=data.get('id', str(uuid.uuid4())),
            name=data['name'],
            icon=data.get('icon', '📊'),
            order=data.get('order', 0)
        )
