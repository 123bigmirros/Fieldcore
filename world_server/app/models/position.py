# -*- coding: utf-8 -*-
"""位置模型 - 表示世界中的坐标位置"""

from typing import Tuple
from dataclasses import dataclass


@dataclass
class Position:
    """表示多维空间中的位置（使用整数坐标）"""
    coordinates: Tuple[float, ...]

    def __init__(self, *coords: float):
        """初始化位置，坐标自动四舍五入为整数"""
        self.coordinates = tuple(float(round(coord)) for coord in coords)

    def distance_to(self, other: "Position") -> float:
        """计算到另一个位置的欧几里得距离"""
        if len(self.coordinates) != len(other.coordinates):
            raise ValueError("位置必须具有相同的维度")
        return sum((a - b) ** 2 for a, b in zip(self.coordinates, other.coordinates)) ** 0.5

    def square_distance_to(self, other: "Position") -> float:
        """计算切比雪夫距离（方形可见性）"""
        if len(self.coordinates) != len(other.coordinates):
            raise ValueError("位置必须具有相同的维度")
        return max(abs(a - b) for a, b in zip(self.coordinates, other.coordinates))

    def is_within_bounds(self, min_val: float, max_val: float) -> bool:
        """检查位置是否在边界内"""
        return all(min_val <= coord <= max_val for coord in self.coordinates)

    def to_list(self) -> list:
        """转换为列表"""
        return list(self.coordinates)

    def __str__(self) -> str:
        return f"({', '.join(map(str, self.coordinates))})"

    def __repr__(self) -> str:
        return f"Position{self.coordinates}"

