# -*- coding: utf-8 -*-
"""
Frontend Serializer - Frontend data serialization utility

Converts internal data formats to frontend-compatible formats
"""

from typing import Dict, List
from ..services.collision_service import SLOT_OFFSETS


class FrontendSerializer:
    """Frontend data serializer"""

    @staticmethod
    def serialize_machines(machines: Dict[str, dict]) -> List[dict]:
        """Serialize machine data to frontend format"""
        result = []
        for machine_id, machine_data in machines.items():
            result.append({
                'machine_id': machine_id,
                'position': list(machine_data.get('position', [0, 0, 0])),
                'life_value': machine_data.get('life_value', 10),
                'machine_type': machine_data.get('machine_type', 'worker'),
                'owner': machine_data.get('owner', ''),
                'status': machine_data.get('status', 'active'),
                'last_action': machine_data.get('last_action', ''),
                'size': machine_data.get('size', 1.0),
                'facing_direction': list(machine_data.get('facing_direction', [1.0, 0.0])),
                'view_size': machine_data.get('view_size', 3),
                'visibility_radius': machine_data.get('view_size', 3),
                'slots': machine_data.get('slots', {"top": None, "bottom": None, "left": None, "right": None}),
            })
        return result

    @staticmethod
    def serialize_obstacles(obstacles: Dict[str, dict]) -> List[dict]:
        """Serialize obstacle data to frontend format"""
        result = []
        for obstacle_id, obstacle_data in obstacles.items():
            result.append({
                'obstacle_id': obstacle_id,
                'position': list(obstacle_data.get('position', [0, 0, 0])),
                'size': obstacle_data.get('size', 1.0),
                'obstacle_type': obstacle_data.get('obstacle_type', 'static')
            })
        return result

    @staticmethod
    def serialize_carried_resources(machines: Dict[str, dict]) -> List[dict]:
        """Serialize all carried resources (with world coordinates)"""
        result = []
        for machine_id, machine_data in machines.items():
            pos = machine_data.get('position', [0, 0, 0])
            slots = machine_data.get('slots', {})
            for slot, resource in slots.items():
                if resource is None:
                    continue
                dx, dy = SLOT_OFFSETS[slot]
                result.append({
                    'holder_id': machine_id,
                    'slot': slot,
                    'position': [int(pos[0]) + dx, int(pos[1]) + dy, 0],
                    'size': resource.get('size', 1.0),
                    'obstacle_type': resource.get('obstacle_type', 'static'),
                })
        return result
