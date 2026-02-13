# -*- coding: utf-8 -*-
"""
Action Handler - 机器人动作处理器

处理 move, attack, turn, remove 等动作
"""

import time
from typing import Dict, Tuple

from ..models import Position


class ActionHandler:
    """动作处理器"""

    def __init__(self, world_bounds: Tuple[float, float], collision_checker):
        self.world_bounds = world_bounds
        self._check_collision = collision_checker

    def move(self, machine: dict, params: dict, machine_id: str) -> dict:
        """移动动作"""
        direction = params.get('direction', [1, 0, 0])
        distance = params.get('distance', 1)

        # 标准化方向
        length = sum(d**2 for d in direction) ** 0.5
        if length == 0:
            return {'success': False, 'error': 'Invalid direction'}

        norm_dir = [d / length for d in direction]
        machine['facing_direction'] = [norm_dir[0], norm_dir[1]]

        if distance == 0:
            return {'success': True, 'result': 'Direction updated'}

        # 计算新位置
        current_pos = machine['position']
        new_x = round(current_pos[0] + norm_dir[0] * distance)
        new_y = round(current_pos[1] + norm_dir[1] * distance)
        new_z = round(current_pos[2] if len(current_pos) > 2 else 0)
        new_pos = Position(new_x, new_y, new_z)

        # 检查边界
        if not new_pos.is_within_bounds(self.world_bounds[0], self.world_bounds[1]):
            return {'success': False, 'error': 'Out of bounds'}

        # 检查碰撞
        if self._check_collision(new_pos, machine.get('size', 1.0), machine_id):
            return {'success': False, 'error': 'Collision detected'}

        machine['position'] = new_pos.to_list()
        machine['last_action'] = f'moved_to_{new_pos}'

        return {
            'success': True,
            'result': {
                'new_position': new_pos.to_list(),
                'facing_direction': machine['facing_direction']
            }
        }

    def attack(self, machine: dict, params: dict, machines: Dict, obstacles: Dict, machine_id: str) -> dict:
        """攻击动作"""
        damage = params.get('damage', 1)

        pos = machine['position']
        dx, dy = machine['facing_direction']
        start_x, start_y = int(pos[0]), int(pos[1])

        laser_path = [{'x': start_x, 'y': start_y}]
        hit_result = {'hit_type': 'none'}

        x, y = float(start_x), float(start_y)
        for _ in range(100):
            x = x + dx
            y = y + dy

            ix, iy = int(round(x)), int(round(y))

            if not (self.world_bounds[0] <= ix <= self.world_bounds[1] and
                    self.world_bounds[0] <= iy <= self.world_bounds[1]):
                break

            laser_path.append({'x': ix, 'y': iy})

            # 检查障碍物
            for obs_id, obs in obstacles.items():
                ox, oy = int(obs['position'][0]), int(obs['position'][1])
                if ox == ix and oy == iy:
                    hit_result = {'hit_type': 'obstacle', 'obstacle_id': obs_id}
                    break

            if hit_result['hit_type'] != 'none':
                break

            # 检查机器人
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
        """转向动作"""
        direction = params.get('direction', [1, 0])
        length = sum(d**2 for d in direction) ** 0.5
        if length == 0:
            return {'success': False, 'error': 'Invalid direction'}

        machine['facing_direction'] = [direction[0] / length, direction[1] / length]
        return {'success': True, 'result': {'facing_direction': machine['facing_direction']}}

