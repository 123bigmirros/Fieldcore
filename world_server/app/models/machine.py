# -*- coding: utf-8 -*-
"""Machine model - Represents a machine entity in the world"""

from typing import Optional, Tuple
from dataclasses import dataclass, field
from .position import Position


@dataclass
class MachineInfo:
    """Machine info"""
    machine_id: str
    position: Position
    life_value: int = 10
    machine_type: str = "generic"
    owner: str = ""
    status: str = "active"
    last_action: Optional[str] = None
    size: float = 1.0
    facing_direction: Tuple[float, float] = field(default_factory=lambda: (1.0, 0.0))
    view_size: int = 3
    slots: dict = field(default_factory=lambda: {"top": None, "bottom": None, "left": None, "right": None})

    def to_dict(self) -> dict:
        """Convert to dict"""
        return {
            'machine_id': self.machine_id,
            'position': self.position.to_list(),
            'life_value': self.life_value,
            'machine_type': self.machine_type,
            'owner': self.owner,
            'status': self.status,
            'last_action': self.last_action,
            'size': self.size,
            'facing_direction': list(self.facing_direction),
            'view_size': self.view_size,
            'slots': dict(self.slots),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "MachineInfo":
        """Create from dict"""
        default_slots = {"top": None, "bottom": None, "left": None, "right": None}
        slots = data.get('slots', default_slots)
        # Ensure all four keys exist
        for key in default_slots:
            if key not in slots:
                slots[key] = None
        return cls(
            machine_id=data['machine_id'],
            position=Position(*data['position']),
            life_value=data.get('life_value', 10),
            machine_type=data.get('machine_type', 'generic'),
            owner=data.get('owner', ''),
            status=data.get('status', 'active'),
            last_action=data.get('last_action'),
            size=data.get('size', 1.0),
            facing_direction=tuple(data.get('facing_direction', [1.0, 0.0])),
            view_size=int(data.get('view_size', 3)),
            slots=slots,
        )

