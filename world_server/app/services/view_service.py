# -*- coding: utf-8 -*-
"""
View Service - Vision/visibility service

Handles machine field-of-view calculations
"""

from typing import Dict, Optional
from .collision_service import SLOT_OFFSETS


class ViewService:
    """Vision service"""

    def __init__(self, machines: Dict, obstacles: Dict):
        self._machines = machines
        self._obstacles = obstacles

    def get_machine_view(self, machine_id: str) -> Optional[dict]:
        """Get a machine's field of view"""
        if machine_id not in self._machines:
            return None

        machine = self._machines[machine_id]
        pos = machine['position']
        center_x, center_y = int(pos[0]), int(pos[1])
        view_size = machine.get('view_size', 3)
        half = view_size // 2

        cells = []
        for y_off in range(half, -half - 1, -1):
            row = []
            for x_off in range(-half, half + 1):
                cell = self._get_cell_info(center_x + x_off, center_y + y_off, machine_id)
                row.append(cell)
            cells.append(row)

        return {
            'machine_id': machine_id,
            'center': [center_x, center_y],
            'view_size': view_size,
            'cells': cells
        }

    def _get_cell_info(self, x: int, y: int, viewer_id: str) -> dict:
        """Get cell info at a given coordinate"""
        cell = {'x': x, 'y': y, 'terrain': 'empty'}

        # Check obstacles
        for obs_id, obs in self._obstacles.items():
            if int(obs['position'][0]) == x and int(obs['position'][1]) == y:
                cell['terrain'] = 'obstacle'
                cell['obstacle_id'] = obs_id
                cell['obstacle_type'] = obs.get('obstacle_type', 'static')
                cell['size'] = obs.get('size', 1.0)
                return cell

        # Check machines
        for m_id, m in self._machines.items():
            if int(m['position'][0]) == x and int(m['position'][1]) == y:
                cell['terrain'] = 'self' if m_id == viewer_id else 'machine'
                cell['machine_id'] = m_id
                if m_id != viewer_id:
                    cell['machine_type'] = m.get('machine_type')
                    cell['status'] = m.get('status')
                return cell

        # Check carried resources
        for m_id, m in self._machines.items():
            slots = m.get('slots', {})
            for slot, resource in slots.items():
                if resource is None:
                    continue
                dx, dy = SLOT_OFFSETS[slot]
                rx = int(m['position'][0]) + dx
                ry = int(m['position'][1]) + dy
                if rx == x and ry == y:
                    cell['terrain'] = 'carried_resource'
                    cell['holder_id'] = m_id
                    cell['slot'] = slot
                    return cell

        return cell
