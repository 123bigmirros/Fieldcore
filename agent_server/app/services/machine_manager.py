# -*- coding: utf-8 -*-
"""
Machine Manager - Machine Agent 管理

负责 Machine Agent 的创建、查询、删除和命令执行
"""

import sys
import os

# 添加项目根目录
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from threading import Lock
from typing import Dict, List, Optional, Tuple

from app.agent.machine import MachineAgent
from app.agent.world_manager import Position
from app.service.world_client import world_client
from app.service.position_utils import find_random_valid_position
from app.logger import logger

import asyncio

from ..config import config
from ..models.agent import MachineInfo


class MachineManager:
    """Machine Agent 管理器 - 单例"""

    _instance = None
    _lock = Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, '_initialized'):
            return

        self._machines: Dict[str, MachineAgent] = {}
        self._data_lock = Lock()
        self._initialized = True

    def create(
        self,
        machine_id: str,
        owner_id: str,
        position: List[float] = None
    ) -> Tuple[bool, str]:
        """
        创建 Machine Agent

        Args:
            machine_id: 机器人 ID
            owner_id: 所属 Human ID
            position: 位置坐标（可选，为 None 时自动寻找）

        Returns:
            (success, error_message)
        """
        with self._data_lock:
            if machine_id in self._machines:
                return False, f"Machine {machine_id} already exists"

            try:
                # 自动寻找位置
                if position is None:
                    position = find_random_valid_position()
                    if not position:
                        return False, "Cannot find valid position"

                # 注册到 World Server
                success, error = world_client.register_machine(
                    machine_id=machine_id,
                    position=position,
                    owner=owner_id,
                    life_value=10,
                    machine_type="worker"
                )

                if not success:
                    return False, error

                # 创建 Machine Agent
                machine = MachineAgent(
                    machine_id=machine_id,
                    location=Position(*position),
                    life_value=10
                )

                asyncio.run(machine.initialize(
                    connection_type="http_api",
                    server_url=config.MCP_SERVER_URL
                ))

                self._machines[machine_id] = machine

                logger.info(f"✅ Machine {machine_id} 创建成功")
                return True, ""

            except Exception as e:
                logger.error(f"创建 Machine 失败: {e}")
                return False, str(e)

    def get(self, machine_id: str) -> Optional[MachineAgent]:
        """获取 Machine Agent 实例"""
        with self._data_lock:
            return self._machines.get(machine_id)

    def get_info(self, machine_id: str) -> Optional[dict]:
        """获取 Machine 信息"""
        with self._data_lock:
            if machine_id not in self._machines:
                return None

            # 从 World Server 获取最新状态
            machine_info = world_client.get_machine(machine_id)
            if not machine_info:
                return None

            return MachineInfo(
                agent_id=machine_id,
                owner_id=machine_info.get('owner', ''),
                position=machine_info.get('position', [0, 0, 0]),
                life_value=machine_info.get('life_value', 10)
            ).to_dict()

    def get_all(self) -> Dict[str, dict]:
        """获取所有 Machine 信息"""
        # 先获取机器ID列表（快速操作，持有锁时间短）
        with self._data_lock:
            machine_ids = list(self._machines.keys())

        if not machine_ids:
            return {}

        # 在锁外进行网络请求，避免长时间持有锁
        result = {}
        try:
            # 优化：只调用一次 get_all_machines，避免重复请求
            logger.info(f"🌐 批量获取 {len(machine_ids)} 个机器的信息")
            all_machines = world_client.get_all_machines()
            logger.info(f"✅ 从 World Server 获取到 {len(all_machines) if isinstance(all_machines, dict) else 0} 个机器数据")

            if not isinstance(all_machines, dict):
                logger.warning(f"⚠️ get_all_machines 返回了非字典类型: {type(all_machines)}")
                all_machines = {}

            for machine_id in machine_ids:
                machine_info = all_machines.get(machine_id)
                if machine_info:
                    result[machine_id] = MachineInfo(
                        agent_id=machine_id,
                        owner_id=machine_info.get('owner', ''),
                        position=machine_info.get('position', [0, 0, 0]),
                        life_value=machine_info.get('life_value', 10)
                    ).to_dict()
                else:
                    logger.warning(f"⚠️ 机器 {machine_id} 在 World Server 中未找到")
        except Exception as e:
            logger.error(f"❌ 批量获取所有 Machine 信息失败: {e}", exc_info=True)
            # 降级：如果批量获取失败，回退到逐个获取
            logger.info("🔄 降级到逐个获取机器信息")
            for machine_id in machine_ids:
                try:
                    info = self.get_info(machine_id)
                    if info:
                        result[machine_id] = info
                except Exception as e2:
                    logger.error(f"获取机器 {machine_id} 信息失败: {e2}")
        return result

    def exists(self, machine_id: str) -> bool:
        """检查 Machine 是否存在"""
        with self._data_lock:
            return machine_id in self._machines

    def delete(self, machine_id: str) -> Tuple[bool, str]:
        """删除 Machine Agent"""
        with self._data_lock:
            if machine_id not in self._machines:
                return False, f"Machine {machine_id} not found"

            try:
                # 从 World Server 移除
                world_client.remove_machine(machine_id)

                # 删除本地实例
                del self._machines[machine_id]

                logger.info(f"🧹 Machine {machine_id} 已删除")
                return True, ""

            except Exception as e:
                logger.error(f"删除 Machine 失败: {e}")
                return False, str(e)

    def send_command(self, machine_id: str, command: str) -> Tuple[bool, str]:
        """向 Machine 发送命令"""
        with self._data_lock:
            if machine_id not in self._machines:
                return False, f"Machine {machine_id} not found"

            try:
                machine = self._machines[machine_id]
                result = asyncio.run(machine.run(command))
                return True, result
            except Exception as e:
                return False, str(e)

    def update_position(self, machine_id: str, position: List[float]) -> Tuple[bool, str]:
        """更新 Machine 位置"""
        if machine_id not in self._machines:
            return False, f"Machine {machine_id} not found"

        return world_client.update_machine_position(machine_id, position)

    def update_life(self, machine_id: str, life_change: int) -> Tuple[bool, str]:
        """更新 Machine 生命值"""
        if machine_id not in self._machines:
            return False, f"Machine {machine_id} not found"

        success = world_client.update_machine_life(machine_id, life_change)
        return success, "" if success else "Failed to update life"


# 全局实例
machine_manager = MachineManager()
