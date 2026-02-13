# -*- coding: utf-8 -*-
"""
View Service - 视野服务

处理机器人的视野计算
"""

from typing import Dict, Optional


class ViewService:
    """视野服务"""

    def __init__(self, machines: Dict, obstacles: Dict):
        """
        初始化视野服务

        Args:
            machines: 机器人字典
            obstacles: 障碍物字典
        """
        self._machines = machines
        self._obstacles = obstacles

    def get_machine_view(self, machine_id: str) -> Optional[dict]:
        """
        获取机器人的视野

        Args:
            machine_id: 机器ID

        Returns:
            视野数据字典，如果机器不存在返回 None
        """
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
        """获取单元格信息"""
        cell = {'x': x, 'y': y, 'terrain': 'empty'}

        # 检查障碍物
        for obs_id, obs in self._obstacles.items():
            if int(obs['position'][0]) == x and int(obs['position'][1]) == y:
                cell['terrain'] = 'obstacle'
                cell['obstacle_id'] = obs_id
                return cell

        # 检查机器人
        for m_id, m in self._machines.items():
            if int(m['position'][0]) == x and int(m['position'][1]) == y:
                cell['terrain'] = 'self' if m_id == viewer_id else 'machine'
                cell['machine_id'] = m_id
                if m_id != viewer_id:
                    cell['machine_type'] = m.get('machine_type')
                    cell['status'] = m.get('status')
                return cell

        return cell

