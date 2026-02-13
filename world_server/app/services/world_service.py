# -*- coding: utf-8 -*-
"""
World Service - 世界管理服务（主服务）

协调各模块，提供统一 API
"""

from typing import Dict, List, Optional, Tuple
from threading import Lock

from ..models import Position, MachineInfo
from ..config import config
from ..handlers.action_handler import ActionHandler
from ..utils.world_storage import WorldStorage
from ..utils.frontend_serializer import FrontendSerializer
from .collision_service import CollisionService
from .view_service import ViewService
from .command_queue_service import command_queue_service


class WorldService:
    """世界管理服务 - 单例"""

    _instance: Optional["WorldService"] = None
    _lock = Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, 'initialized'):
            return

        self.world_bounds = config.WORLD_BOUNDS
        self._machines: Dict[str, dict] = {}
        self._obstacles: Dict[str, dict] = {}
        self._data_lock = Lock()

        # 初始化子模块
        self._storage = WorldStorage()
        self._collision_service = CollisionService(self._machines, self._obstacles)
        self._actions = ActionHandler(self.world_bounds, self._collision_service.check_collision)
        self._view_service = ViewService(self._machines, self._obstacles)
        self._serializer = FrontendSerializer()

        # 加载或初始化
        machines, obstacles, loaded = self._storage.load()
        if loaded:
            self._machines = machines
            self._obstacles = obstacles
        else:
            self._obstacles = WorldStorage.create_default_obstacles()

        # 初始化命令队列服务
        command_queue_service.set_execute_callback(self._execute_action_internal)
        command_queue_service.start_consumer()

        # 为已存在的 machines 创建队列
        for machine_id in self._machines.keys():
            command_queue_service.create_queue(machine_id)

        self.initialized = True

    # ==================== 核心 API ====================

    def register_machine(
        self,
        machine_id: str,
        position: List[float],
        owner: str = "",
        life_value: int = config.DEFAULT_LIFE_VALUE,
        machine_type: str = config.DEFAULT_MACHINE_TYPE,
        size: float = config.DEFAULT_SIZE,
        facing_direction: Tuple[float, float] = (1.0, 0.0),
        view_size: int = config.DEFAULT_VIEW_SIZE
    ) -> Tuple[bool, str]:
        """注册机器人"""
        with self._data_lock:
            if machine_id in self._machines:
                return False, "Machine already exists"

            pos = Position(*position)
            if self._collision_service.check_collision(pos, size):
                return False, "Position has collision"

            # 确保 view_size 是奇数且至少为 1
            view_size = max(1, int(view_size))
            if view_size % 2 == 0:
                view_size += 1

            machine = MachineInfo(
                machine_id=machine_id,
                position=pos,
                life_value=life_value,
                machine_type=machine_type,
                owner=owner,
                size=size,
                facing_direction=facing_direction,
                view_size=view_size,
            )
            self._machines[machine_id] = machine.to_dict()

            # 为新的 machine 创建命令队列
            command_queue_service.create_queue(machine_id)

            return True, ""

    def _execute_action_internal(self, machine_id: str, action: str, params: dict) -> dict:
        """
        内部方法：实际执行动作（由命令队列服务调用）

        注意：这个方法会在消费者线程中被调用，需要考虑线程安全
        """
        with self._data_lock:
            if machine_id not in self._machines:
                return {'success': False, 'error': 'Machine not found'}

            machine = self._machines[machine_id]
            if machine.get('status') != 'active':
                return {'success': False, 'error': f"Machine not active: {machine.get('status')}"}

            if action == 'move':
                return self._actions.move(machine, params, machine_id)
            elif action == 'attack':
                return self._actions.attack(machine, params, self._machines, self._obstacles, machine_id)
            elif action == 'turn':
                return self._actions.turn(machine, params)
            elif action == 'remove':
                del self._machines[machine_id]
                command_queue_service.remove_queue(machine_id)
                return {'success': True, 'result': 'Machine removed'}
            else:
                return {'success': False, 'error': f'Unknown action: {action}'}

    def enqueue_command(self, machine_id: str, action: str, params: dict) -> dict:
        """
        将命令添加到队列

        Args:
            machine_id: 机器ID
            action: 动作类型
            params: 动作参数

        Returns:
            包含成功状态的字典
        """
        with self._data_lock:
            if machine_id not in self._machines:
                return {'success': False, 'error': 'Machine not found'}

        success = command_queue_service.enqueue_command(machine_id, action, params)
        if success:
            return {'success': True, 'message': 'Command enqueued'}
        else:
            return {'success': False, 'error': 'Command queue is full'}

    def save_world(self) -> bool:
        """保存世界"""
        with self._data_lock:
            return self._storage.save(self._machines, self._obstacles)

    def get_machine_view(self, machine_id: str) -> Optional[dict]:
        """获取视野"""
        with self._data_lock:
            return self._view_service.get_machine_view(machine_id)

    # ==================== 调试方法 ====================

    def get_all_machines(self) -> dict:
        """获取所有机器人（原始格式）"""
        with self._data_lock:
            return dict(self._machines)

    def get_all_obstacles(self) -> dict:
        """获取所有障碍物（原始格式）"""
        with self._data_lock:
            return dict(self._obstacles)

    def reset_world(self) -> dict:
        """重置世界"""
        with self._data_lock:
            count = len(self._machines)
            # 清理所有命令队列
            for machine_id in list(self._machines.keys()):
                command_queue_service.remove_queue(machine_id)
            self._machines.clear()
            self._obstacles = WorldStorage.create_default_obstacles()
            return {'machines_removed': count}

    def get_machine(self, machine_id: str) -> Optional[dict]:
        """获取单个机器信息"""
        with self._data_lock:
            return self._machines.get(machine_id)

    # ==================== 前端数据接口 ====================

    def get_machines_for_frontend(self) -> List[dict]:
        """获取所有机器人数据（前端格式）"""
        with self._data_lock:
            return self._serializer.serialize_machines(self._machines)

    def get_obstacles_for_frontend(self) -> List[dict]:
        """获取所有障碍物数据（前端格式）"""
        with self._data_lock:
            return self._serializer.serialize_obstacles(self._obstacles)


# 全局实例
world_service = WorldService()
