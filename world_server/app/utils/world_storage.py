# -*- coding: utf-8 -*-
"""
World Storage - 世界状态存储工具

处理持久化和障碍物初始化
"""

import json
import os
import random
from typing import Dict

from ..models import Position, Obstacle


class WorldStorage:
    """世界存储管理"""

    def __init__(self, save_path: str = "world_state.json"):
        self.save_path = save_path

    def save(self, machines: Dict, obstacles: Dict) -> bool:
        """保存世界状态"""
        try:
            import time
            data = {
                'machines': machines,
                'obstacles': obstacles,
                'saved_at': time.time()
            }
            with open(self.save_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"保存失败: {e}")
            return False

    def load(self) -> tuple:
        """加载世界状态，返回 (machines, obstacles, success)"""
        try:
            if os.path.exists(self.save_path):
                with open(self.save_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                print("✅ 加载世界状态成功")
                return data.get('machines', {}), data.get('obstacles', {}), True
        except Exception as e:
            print(f"加载失败: {e}")
        return {}, {}, False

    @staticmethod
    def create_default_obstacles(wall_size: int = 15) -> Dict[str, dict]:
        """创建默认障碍物"""
        obstacles = {}

        # 四面墙
        for i in range(-wall_size, wall_size + 1):
            obstacles[f"wall_top_{i}"] = Obstacle(f"wall_top_{i}", Position(i, wall_size, 0)).to_dict()
            obstacles[f"wall_bottom_{i}"] = Obstacle(f"wall_bottom_{i}", Position(i, -wall_size, 0)).to_dict()
            obstacles[f"wall_left_{i}"] = Obstacle(f"wall_left_{i}", Position(-wall_size, i, 0)).to_dict()
            obstacles[f"wall_right_{i}"] = Obstacle(f"wall_right_{i}", Position(wall_size, i, 0)).to_dict()

        # 随机障碍物
        random.seed(42)
        for i in range(20):
            while True:
                x = random.randint(-wall_size + 3, wall_size - 3)
                y = random.randint(-wall_size + 3, wall_size - 3)
                if abs(x) > 3 or abs(y) > 3:
                    obstacles[f"inner_{i}"] = Obstacle(f"inner_{i}", Position(x, y, 0)).to_dict()
                    break

        print(f"✅ 初始化 {len(obstacles)} 个障碍物")
        return obstacles

