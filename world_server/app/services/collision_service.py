# -*- coding: utf-8 -*-
"""
Collision Service - Collision detection service
"""

from typing import Dict, Optional
from ..models import Position


# Slot direction offsets
SLOT_OFFSETS = {
    "top": (0, 1),
    "bottom": (0, -1),
    "left": (-1, 0),
    "right": (1, 0),
}


class CollisionService:
    """Collision detection service"""

    def __init__(self, machines: Dict, obstacles: Dict):
        self._machines = machines
        self._obstacles = obstacles

    @staticmethod
    def get_slot_world_position(machine: dict, slot: str) -> Position:
        """Calculate the world position of a slot's resource"""
        pos = machine['position']
        dx, dy = SLOT_OFFSETS[slot]
        return Position(int(pos[0]) + dx, int(pos[1]) + dy, 0)

    def check_collision(
        self,
        position: Position,
        size: float = 1.0,
        exclude_id: Optional[str] = None
    ) -> bool:
        """
        Check if a position has a collision

        Checks: obstacles, other machines, resources carried by other machines
        """
        # Check collision with obstacles
        for obs in self._obstacles.values():
            obs_pos = Position(*obs['position'])
            if position.distance_to(obs_pos) < max(size, obs['size']) * 0.5:
                return True

        # Check collision with other machines + their carried resources
        for m_id, m in self._machines.items():
            if m_id == exclude_id or m.get('status') != 'active':
                continue
            m_pos = Position(*m['position'])
            if position.distance_to(m_pos) < max(size, m.get('size', 1.0)) * 0.5:
                return True

            # Check resources carried by this machine
            slots = m.get('slots', {})
            for slot, resource in slots.items():
                if resource is None:
                    continue
                res_pos = self.get_slot_world_position(m, slot)
                if position.distance_to(res_pos) < max(size, resource.get('size', 1.0)) * 0.5:
                    return True

        return False
