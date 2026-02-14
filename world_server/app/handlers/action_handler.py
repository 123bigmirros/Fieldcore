# -*- coding: utf-8 -*-
"""
Action Handler - Machine action handler

Handles move, attack, turn, remove, grab, drop actions
"""

import time
from typing import Dict, Tuple

from ..models import Position
from ..services.collision_service import SLOT_OFFSETS, CollisionService


class ActionHandler:
    """Action handler"""

    def __init__(self, world_bounds: Tuple[float, float], collision_checker):
        self.world_bounds = world_bounds
        self._check_collision = collision_checker

    def _ensure_slots(self, machine: dict):
        """Ensure machine has a slots field"""
        if 'slots' not in machine:
            machine['slots'] = {"top": None, "bottom": None, "left": None, "right": None}

    def _get_adjacent_pos(self, machine: dict, direction: str) -> Position:
        """Get adjacent cell position by direction"""
        pos = machine['position']
        dx, dy = SLOT_OFFSETS[direction]
        return Position(int(pos[0]) + dx, int(pos[1]) + dy, 0)

    def move(self, machine: dict, params: dict, machine_id: str) -> dict:
        """Move action"""
        self._ensure_slots(machine)
        direction = params.get('direction', [1, 0, 0])
        distance = params.get('distance', 1)

        # Normalize direction
        length = sum(d**2 for d in direction) ** 0.5
        if length == 0:
            return {'success': False, 'error': 'Invalid direction'}

        norm_dir = [d / length for d in direction]
        machine['facing_direction'] = [norm_dir[0], norm_dir[1]]

        if distance == 0:
            return {'success': True, 'result': 'Direction updated'}

        # Calculate new position
        current_pos = machine['position']
        new_x = round(current_pos[0] + norm_dir[0] * distance)
        new_y = round(current_pos[1] + norm_dir[1] * distance)
        new_z = round(current_pos[2] if len(current_pos) > 2 else 0)
        new_pos = Position(new_x, new_y, new_z)

        # Check bounds
        if not new_pos.is_within_bounds(self.world_bounds[0], self.world_bounds[1]):
            return {'success': False, 'error': 'Out of bounds'}

        # Check machine body collision
        if self._check_collision(new_pos, machine.get('size', 1.0), machine_id):
            return {'success': False, 'error': 'Collision detected'}

        # Check carried resource target position collision
        for slot, resource in machine['slots'].items():
            if resource is None:
                continue
            sdx, sdy = SLOT_OFFSETS[slot]
            slot_target = Position(new_x + sdx, new_y + sdy, 0)
            if self._check_collision(slot_target, resource.get('size', 1.0), machine_id):
                return {'success': False, 'error': f'Carried resource collision at slot {slot}'}

        machine['position'] = new_pos.to_list()
        machine['last_action'] = f'moved_to_{new_pos}'

        return {
            'success': True,
            'result': {
                'new_position': new_pos.to_list(),
                'facing_direction': machine['facing_direction']
            }
        }

    def grab(self, machine: dict, params: dict, obstacles: Dict, machine_id: str) -> dict:
        """Grab a resource"""
        self._ensure_slots(machine)
        direction = params.get('direction')
        if direction not in SLOT_OFFSETS:
            return {'success': False, 'error': f'Invalid direction: {direction}. Use top/bottom/left/right'}

        # Check if slot is empty
        if machine['slots'][direction] is not None:
            return {'success': False, 'error': f'Slot {direction} is already occupied'}

        # Calculate adjacent cell
        target_pos = self._get_adjacent_pos(machine, direction)
        tx, ty = int(target_pos.x), int(target_pos.y)

        # Find obstacle at this position
        found_id = None
        for obs_id, obs in obstacles.items():
            if int(obs['position'][0]) == tx and int(obs['position'][1]) == ty:
                found_id = obs_id
                break

        if found_id is None:
            return {'success': False, 'error': f'No resource at {direction} ({tx}, {ty})'}

        # Remove from world and store in slot
        resource_data = obstacles.pop(found_id)
        resource_data['original_id'] = found_id
        machine['slots'][direction] = resource_data
        machine['last_action'] = f'grab_{direction}'

        return {
            'success': True,
            'result': {
                'grabbed': found_id,
                'direction': direction,
                'slots': dict(machine['slots'])
            }
        }

    def drop(self, machine: dict, params: dict, obstacles: Dict, machine_id: str) -> dict:
        """Drop a resource"""
        self._ensure_slots(machine)
        direction = params.get('direction')
        if direction not in SLOT_OFFSETS:
            return {'success': False, 'error': f'Invalid direction: {direction}. Use top/bottom/left/right'}

        # Check if slot has a resource
        resource = machine['slots'][direction]
        if resource is None:
            return {'success': False, 'error': f'Slot {direction} is empty'}

        # Calculate target cell
        target_pos = self._get_adjacent_pos(machine, direction)

        # Check target position collision (excluding self)
        if self._check_collision(target_pos, resource.get('size', 1.0), machine_id):
            return {'success': False, 'error': f'Cannot drop: collision at ({target_pos.x}, {target_pos.y})'}

        # Remove from slot and place back into world
        resource['position'] = target_pos.to_list()
        obs_id = resource.pop('original_id', f'resource_{int(time.time()*1000)}')
        obstacles[obs_id] = resource
        machine['slots'][direction] = None
        machine['last_action'] = f'drop_{direction}'

        return {
            'success': True,
            'result': {
                'dropped': obs_id,
                'direction': direction,
                'position': target_pos.to_list()
            }
        }

    def attack(self, machine: dict, params: dict, machines: Dict, obstacles: Dict, machine_id: str) -> dict:
        """Attack action"""
        damage = params.get('damage', 1)

        pos = machine['position']
        dx, dy = machine['facing_direction']
        start_x, start_y = int(pos[0]), int(pos[1])

        laser_path = [{'x': start_x, 'y': start_y}]
        hit_result = {'hit_type': 'none'}

        # Precompute world coordinates of all carried resources
        carried_positions = {}
        for m_id, m in machines.items():
            for slot, res in m.get('slots', {}).items():
                if res is not None:
                    sdx, sdy = SLOT_OFFSETS[slot]
                    cx = int(m['position'][0]) + sdx
                    cy = int(m['position'][1]) + sdy
                    carried_positions[(cx, cy)] = {'holder_id': m_id, 'slot': slot}

        x, y = float(start_x), float(start_y)
        for _ in range(100):
            x = x + dx
            y = y + dy

            ix, iy = int(round(x)), int(round(y))

            if not (self.world_bounds[0] <= ix <= self.world_bounds[1] and
                    self.world_bounds[0] <= iy <= self.world_bounds[1]):
                break

            laser_path.append({'x': ix, 'y': iy})

            # Check obstacles
            for obs_id, obs in obstacles.items():
                ox, oy = int(obs['position'][0]), int(obs['position'][1])
                if ox == ix and oy == iy:
                    hit_result = {'hit_type': 'obstacle', 'obstacle_id': obs_id}
                    break

            if hit_result['hit_type'] != 'none':
                break

            # Check carried resources
            if (ix, iy) in carried_positions:
                info = carried_positions[(ix, iy)]
                hit_result = {'hit_type': 'carried_resource', 'holder_id': info['holder_id'], 'slot': info['slot']}
                break

            # Check machines
            for m_id, m in machines.items():
                if m_id == machine_id or m.get('status') != 'active':
                    continue
                mx, my = int(m['position'][0]), int(m['position'][1])
                if mx == ix and my == iy:
                    hit_result = {'hit_type': 'machine', 'machine_id': m_id}
                    m['life_value'] -= damage
                    if m['life_value'] <= 0:
                        m['status'] = 'destroyed'
                        hit_result['destroyed'] = True
                    break

            if hit_result['hit_type'] != 'none':
                break

        machine['last_action'] = f'attack_{time.time()}'

        return {
            'success': True,
            'result': {
                'laser_path': laser_path,
                'hit_result': hit_result,
                'damage': damage if hit_result.get('machine_id') else 0
            }
        }

    def turn(self, machine: dict, params: dict) -> dict:
        """Turn action"""
        direction = params.get('direction', [1, 0])
        length = sum(d**2 for d in direction) ** 0.5
        if length == 0:
            return {'success': False, 'error': 'Invalid direction'}

        machine['facing_direction'] = [direction[0] / length, direction[1] / length]
        return {'success': True, 'result': {'facing_direction': machine['facing_direction']}}
