# -*- coding: utf-8 -*-
"""机器人模型 - 表示世界中的机器人实体"""

from typing import Optional, Tuple
from dataclasses import dataclass, field
from .position import Position


@dataclass
class MachineInfo:
    """机器人信息"""
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

    def to_dict(self) -> dict:
        """转换为字典"""
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
        }

    @classmethod
    def from_dict(cls, data: dict) -> "MachineInfo":
        """从字典创建"""
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
        )

