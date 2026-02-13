"""
World Service - 世界管理服务层

提供对 WorldManager 的封装接口，隐藏底层实现细节。
符合软件工程的封装原则，提供清晰的业务接口。
"""

from typing import Optional, Dict, List, Tuple
from app.agent.world_manager import world_manager, Position, MachineInfo, Obstacle
from app.logger import logger


class WorldService:
    """
    世界管理服务层

    封装 WorldManager 的操作，提供高层次的业务接口。
    所有对世界状态的访问都应该通过此服务层进行。
    """

    def __init__(self):
        """初始化世界服务"""
        self._world_manager = world_manager
        logger.info("WorldService initialized")

    # ==================== 机器人查询接口 ====================

    def get_all_machines_info(self) -> Dict[str, dict]:
        """
        获取所有机器人信息

        Returns:
            Dict[str, dict]: 机器人ID -> 机器人信息字典
        """
        machines = self._world_manager.get_all_machines()
        result = {}
        for machine_id, info in machines.items():
            result[machine_id] = self._format_machine_info(info)
        return result

    def get_machine_info(self, machine_id: str) -> Optional[dict]:
        """
        获取特定机器人信息

        Args:
            machine_id: 机器人ID

        Returns:
            Optional[dict]: 机器人信息字典，如果不存在则返回 None
        """
        info = self._world_manager.get_machine_info(machine_id)
        if info:
            return self._format_machine_info(info)
        return None

    def machine_exists(self, machine_id: str) -> bool:
        """
        检查机器人是否存在

        Args:
            machine_id: 机器人ID

        Returns:
            bool: 是否存在
        """
        return self._world_manager.get_machine_info(machine_id) is not None

    def get_nearby_machines(self, machine_id: str, radius: float = 10.0) -> List[dict]:
        """
        获取附近的机器人

        Args:
            machine_id: 中心机器人ID
            radius: 搜索半径

        Returns:
            List[dict]: 附近机器人信息列表
        """
        nearby = self._world_manager.get_nearby_machines(machine_id, radius)
        return [self._format_machine_info(info) for info in nearby]

    # ==================== 机器人管理接口 ====================

    def register_machine(
        self,
        machine_id: str,
        position: List[float],
        life_value: int = 10,
        machine_type: str = "generic",
        size: float = 1.0,
        facing_direction: Tuple[float, float] = (1.0, 0.0),
        owner: str = "",
        view_size: int = 3
    ) -> bool:
        """
        注册新机器人

        Args:
            machine_id: 机器人ID
            position: 位置坐标 [x, y, z]
            life_value: 生命值
            machine_type: 机器人类型
            size: 尺寸
            facing_direction: 朝向
            owner: 所有者ID
            view_size: 视野大小

        Returns:
            bool: 是否注册成功
        """
        try:
            pos = Position(*position)
            self._world_manager.register_machine(
                machine_id=machine_id,
                position=pos,
                life_value=life_value,
                machine_type=machine_type,
                size=size,
                facing_direction=facing_direction,
                owner=owner,
                view_size=view_size
            )
            logger.info(f"Machine {machine_id} registered successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to register machine {machine_id}: {e}")
            return False

    def remove_machine(self, machine_id: str) -> bool:
        """
        移除机器人

        Args:
            machine_id: 机器人ID

        Returns:
            bool: 是否移除成功
        """
        success = self._world_manager.remove_machine(machine_id)
        if success:
            logger.info(f"Machine {machine_id} removed")
        return success

    def remove_all_machines(self) -> int:
        """
        移除所有机器人

        Returns:
            int: 移除的机器人数量
        """
        machines = self._world_manager.get_all_machines()
        count = 0
        for machine_id in list(machines.keys()):
            if self._world_manager.remove_machine(machine_id):
                count += 1
        logger.info(f"Removed {count} machines")
        return count

    def update_machine_position(
        self,
        machine_id: str,
        new_position: List[float]
    ) -> Tuple[bool, List[str]]:
        """
        更新机器人位置

        Args:
            machine_id: 机器人ID
            new_position: 新位置 [x, y, z]

        Returns:
            Tuple[bool, List[str]]: (是否成功, 碰撞详情列表)
        """
        pos = Position(*new_position)
        return self._world_manager.update_machine_position_with_details(machine_id, pos)

    def update_machine_life(self, machine_id: str, life_change: int) -> bool:
        """
        更新机器人生命值

        Args:
            machine_id: 机器人ID
            life_change: 生命值变化（正数增加，负数减少）

        Returns:
            bool: 是否更新成功
        """
        return self._world_manager.update_machine_life(machine_id, life_change)

    def update_machine_action(self, machine_id: str, action: str) -> bool:
        """
        更新机器人最后动作

        Args:
            machine_id: 机器人ID
            action: 动作描述

        Returns:
            bool: 是否更新成功
        """
        return self._world_manager.update_machine_action(machine_id, action)

    # ==================== 障碍物查询接口 ====================

    def get_all_obstacles_info(self) -> Dict[str, dict]:
        """
        获取所有障碍物信息

        Returns:
            Dict[str, dict]: 障碍物ID -> 障碍物信息字典
        """
        obstacles = self._world_manager.get_all_obstacles()
        result = {}
        for obstacle_id, obstacle in obstacles.items():
            result[obstacle_id] = self._format_obstacle_info(obstacle)
        return result

    def get_obstacle_info(self, obstacle_id: str) -> Optional[dict]:
        """
        获取特定障碍物信息

        Args:
            obstacle_id: 障碍物ID

        Returns:
            Optional[dict]: 障碍物信息字典，如果不存在则返回 None
        """
        obstacle = self._world_manager.get_obstacle(obstacle_id)
        if obstacle:
            return self._format_obstacle_info(obstacle)
        return None

    def obstacle_exists(self, obstacle_id: str) -> bool:
        """
        检查障碍物是否存在

        Args:
            obstacle_id: 障碍物ID

        Returns:
            bool: 是否存在
        """
        return self._world_manager.get_obstacle(obstacle_id) is not None

    # ==================== 障碍物管理接口 ====================

    def add_obstacle(
        self,
        obstacle_id: str,
        position: List[float],
        size: float = 1.0,
        obstacle_type: str = "static"
    ) -> bool:
        """
        添加障碍物

        Args:
            obstacle_id: 障碍物ID
            position: 位置坐标 [x, y, z]
            size: 尺寸
            obstacle_type: 障碍物类型

        Returns:
            bool: 是否添加成功
        """
        try:
            pos = Position(*position)
            success = self._world_manager.add_obstacle(
                obstacle_id=obstacle_id,
                position=pos,
                size=size,
                obstacle_type=obstacle_type
            )
            if success:
                logger.info(f"Obstacle {obstacle_id} added successfully")
            else:
                logger.warning(f"Failed to add obstacle {obstacle_id} (collision or already exists)")
            return success
        except Exception as e:
            logger.error(f"Error adding obstacle {obstacle_id}: {e}")
            return False

    def remove_obstacle(self, obstacle_id: str) -> bool:
        """
        移除障碍物

        Args:
            obstacle_id: 障碍物ID

        Returns:
            bool: 是否移除成功
        """
        success = self._world_manager.remove_obstacle(obstacle_id)
        if success:
            logger.info(f"Obstacle {obstacle_id} removed")
        return success

    def remove_all_obstacles(self) -> None:
        """移除所有障碍物"""
        self._world_manager.clear_all_obstacles()
        logger.info("All obstacles removed")

    # ==================== 世界状态管理接口 ====================

    def reset_world(self) -> Dict[str, int]:
        """
        重置世界状态（移除所有机器人和障碍物）

        Returns:
            Dict[str, int]: 包含移除数量的统计信息
        """
        machines_count = self.remove_all_machines()
        self.remove_all_obstacles()

        logger.info(f"World reset: removed {machines_count} machines and all obstacles")

        return {
            "machines_removed": machines_count,
            "obstacles_removed": "all"
        }

    def get_world_bounds(self) -> Tuple[float, float]:
        """
        获取世界边界

        Returns:
            Tuple[float, float]: (最小值, 最大值)
        """
        return self._world_manager.world_bounds

    def get_world_dimensions(self) -> int:
        """
        获取世界维度

        Returns:
            int: 维度数量
        """
        return self._world_manager.world_dimensions

    # ==================== 碰撞检测接口 ====================

    def check_collision(
        self,
        position: List[float],
        size: float = 1.0,
        exclude_machine_id: Optional[str] = None
    ) -> Dict[str, any]:
        """
        检查指定位置是否会碰撞

        Args:
            position: 位置坐标 [x, y, z]
            size: 物体尺寸
            exclude_machine_id: 要排除的机器人ID（用于机器人移动时的检测）

        Returns:
            Dict: {"collision": bool, "details": List[str]}
        """
        pos = Position(*position)
        collision = self._world_manager.check_collision(pos, size, exclude_machine_id)
        details = self._world_manager.find_collision_details(pos, size, exclude_machine_id)

        return {
            "collision": collision,
            "details": details
        }

    # ==================== 私有辅助方法 ====================

    def _format_machine_info(self, info: MachineInfo) -> dict:
        """格式化机器人信息为字典"""
        return {
            "machine_id": info.machine_id,
            "position": list(info.position.coordinates),
            "life_value": info.life_value,
            "machine_type": info.machine_type,
            "owner": info.owner,
            "status": info.status,
            "last_action": info.last_action,
            "size": info.size,
            "facing_direction": list(info.facing_direction),
            "view_size": info.view_size,
            "visibility_radius": info.view_size  # 前端兼容字段
        }

    def _format_obstacle_info(self, obstacle: Obstacle) -> dict:
        """格式化障碍物信息为字典"""
        return {
            "obstacle_id": obstacle.obstacle_id,
            "position": list(obstacle.position.coordinates),
            "size": obstacle.size,
            "obstacle_type": obstacle.obstacle_type
        }


# 全局服务实例
world_service = WorldService()
