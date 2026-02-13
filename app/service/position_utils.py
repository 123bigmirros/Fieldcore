# -*- coding: utf-8 -*-
"""
位置工具模块 - 提供位置查找和验证相关的工具函数
"""

import random
from typing import Optional, List

from app.service.world_client import world_client
from app.logger import logger


def find_random_valid_position(max_attempts: int = 50, map_range: int = 14) -> Optional[List[float]]:
    """
    在地图范围内找到一个合法的随机位置

    Args:
        max_attempts: 最大尝试次数
        map_range: 地图范围（默认 14，表示 -13 到 13）

    Returns:
        合法位置的坐标列表 [x, y, z]，如果找不到则返回 None
    """
    for _ in range(max_attempts):
        x = random.randint(-map_range + 1, map_range - 1)
        y = random.randint(-map_range + 1, map_range - 1)
        position = [float(x), float(y), 0.0]

        try:
            result = world_client.check_collision(position, 1.0)
            if not result.get('collision', True):
                logger.info(f"找到合法位置: {position}")
                return position
        except Exception as e:
            logger.warning(f"碰撞检测失败 {position}: {e}")
            continue

    logger.error(f"尝试了 {max_attempts} 次都无法找到合法位置")
    return None

