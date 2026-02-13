# -*- coding: utf-8 -*-
"""障碍物模型 - 表示世界中的障碍物"""

from dataclasses import dataclass
from .position import Position


@dataclass
class Obstacle:
    """障碍物信息"""
    obstacle_id: str
    position: Position
    size: float = 1.0
    obstacle_type: str = "static"

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            'obstacle_id': self.obstacle_id,
            'position': self.position.to_list(),
            'size': self.size,
            'obstacle_type': self.obstacle_type
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Obstacle":
        """从字典创建"""
        return cls(
            obstacle_id=data['obstacle_id'],
            position=Position(*data['position']),
            size=data.get('size', 1.0),
            obstacle_type=data.get('obstacle_type', 'static')
        )

