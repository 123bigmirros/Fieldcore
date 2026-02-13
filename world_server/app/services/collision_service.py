# -*- coding: utf-8 -*-
"""
Collision Service - 碰撞检测服务
"""

from typing import Dict, Optional
from ..models import Position


class CollisionService:
    """碰撞检测服务"""

    def __init__(self, machines: Dict, obstacles: Dict):
        """
        初始化碰撞检测服务

        Args:
            machines: 机器人字典
            obstacles: 障碍物字典
        """
        self._machines = machines
        self._obstacles = obstacles

    def check_collision(
        self,
        position: Position,
        size: float = 1.0,
        exclude_id: Optional[str] = None
    ) -> bool:
        """
        检查位置是否发生碰撞

        Args:
            position: 要检查的位置
            size: 物体大小
            exclude_id: 排除的机器ID（用于检查自身移动）

        Returns:
            True 如果发生碰撞，False 否则
        """
        # 检查与障碍物的碰撞
        for obs in self._obstacles.values():
            obs_pos = Position(*obs['position'])
            if position.distance_to(obs_pos) < max(size, obs['size']) * 0.5:
                return True

        # 检查与其他机器的碰撞
        for m_id, m in self._machines.items():
            if m_id == exclude_id or m.get('status') != 'active':
                continue
            m_pos = Position(*m['position'])
            if position.distance_to(m_pos) < max(size, m.get('size', 1.0)) * 0.5:
                return True

        return False

