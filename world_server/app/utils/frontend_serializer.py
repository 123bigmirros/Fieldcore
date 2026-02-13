# -*- coding: utf-8 -*-
"""
Frontend Serializer - 前端数据序列化工具

将内部数据格式转换为前端需要的格式
"""

from typing import Dict, List


class FrontendSerializer:
    """前端数据序列化器"""

    @staticmethod
    def serialize_machines(machines: Dict[str, dict]) -> List[dict]:
        """
        序列化机器人数据为前端格式

        Args:
            machines: 机器人字典

        Returns:
            前端格式的机器人数组
        """
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
                'visibility_radius': machine_data.get('view_size', 3)  # 前端兼容字段
            })
        return result

    @staticmethod
    def serialize_obstacles(obstacles: Dict[str, dict]) -> List[dict]:
        """
        序列化障碍物数据为前端格式

        Args:
            obstacles: 障碍物字典

        Returns:
            前端格式的障碍物数组
        """
        result = []
        for obstacle_id, obstacle_data in obstacles.items():
            result.append({
                'obstacle_id': obstacle_id,
                'position': list(obstacle_data.get('position', [0, 0, 0])),
                'size': obstacle_data.get('size', 1.0),
                'obstacle_type': obstacle_data.get('obstacle_type', 'static')
            })
        return result

