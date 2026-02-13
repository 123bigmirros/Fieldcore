# -*- coding: utf-8 -*-
"""
Human Manager - Human Agent 管理

负责 Human Agent 的创建、查询、删除和命令执行
"""

import sys
import os

# 添加项目根目录
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from threading import Lock
from typing import Dict, List, Optional, Tuple

from app.agent.human import HumanAgent
from app.logger import logger

import asyncio

from ..config import config
from ..models.agent import HumanInfo


class HumanManager:
    """Human Agent 管理器 - 单例"""

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

        self._humans: Dict[str, HumanAgent] = {}
        self._human_machines: Dict[str, List[str]] = {}  # human_id -> [machine_id, ...]
        self._data_lock = Lock()
        self._initialized = True

    def create(self, human_id: str) -> Tuple[bool, str]:
        """
        创建 Human Agent

        Args:
            human_id: Human ID

        Returns:
            (success, error_message)
        """
        with self._data_lock:
            if human_id in self._humans:
                return False, f"Human {human_id} already exists"

            try:
                human = HumanAgent(
                    human_id=human_id,
                    machine_count=0
                )

                asyncio.run(human.initialize(
                    connection_type="http_api",
                    server_url=config.MCP_SERVER_URL
                ))

                self._humans[human_id] = human
                self._human_machines[human_id] = []

                logger.info(f"✅ Human {human_id} 创建成功")
                return True, ""

            except Exception as e:
                logger.error(f"创建 Human 失败: {e}")
                return False, str(e)

    def get(self, human_id: str) -> Optional[HumanAgent]:
        """获取 Human Agent 实例"""
        with self._data_lock:
            return self._humans.get(human_id)

    def get_info(self, human_id: str) -> Optional[dict]:
        """获取 Human 信息"""
        with self._data_lock:
            if human_id not in self._humans:
                return None

            return HumanInfo(
                agent_id=human_id,
                agent_type="human",
                machine_ids=self._human_machines.get(human_id, [])
            ).to_dict()

    def get_all(self) -> Dict[str, dict]:
        """获取所有 Human 信息"""
        with self._data_lock:
            result = {}
            # 直接构建信息，避免调用 get_info() 导致死锁
            for human_id in self._humans:
                result[human_id] = HumanInfo(
                    agent_id=human_id,
                    agent_type="human",
                    machine_ids=self._human_machines.get(human_id, [])
                ).to_dict()
            return result

    def exists(self, human_id: str) -> bool:
        """检查 Human 是否存在"""
        with self._data_lock:
            return human_id in self._humans

    def delete(self, human_id: str) -> Tuple[bool, str]:
        """删除 Human Agent"""
        with self._data_lock:
            if human_id not in self._humans:
                return False, f"Human {human_id} not found"

            try:
                human = self._humans[human_id]
                asyncio.run(human.cleanup())

                del self._humans[human_id]

                # 返回关联的机器列表，供外部处理
                machine_ids = self._human_machines.pop(human_id, [])

                logger.info(f"🧹 Human {human_id} 已删除")
                return True, ""

            except Exception as e:
                logger.error(f"删除 Human 失败: {e}")
                return False, str(e)

    def send_command(self, human_id: str, command: str) -> Tuple[bool, str]:
        """向 Human 发送命令"""
        with self._data_lock:
            if human_id not in self._humans:
                return False, f"Human {human_id} not found"

            try:
                human = self._humans[human_id]
                result = asyncio.run(human.run(command))
                return True, result
            except Exception as e:
                return False, str(e)

    def add_machine(self, human_id: str, machine_id: str):
        """添加机器到 Human 的管理列表"""
        with self._data_lock:
            if human_id in self._human_machines:
                if machine_id not in self._human_machines[human_id]:
                    self._human_machines[human_id].append(machine_id)

    def remove_machine(self, human_id: str, machine_id: str):
        """从 Human 的管理列表中移除机器"""
        with self._data_lock:
            if human_id in self._human_machines:
                if machine_id in self._human_machines[human_id]:
                    self._human_machines[human_id].remove(machine_id)

    def get_machines(self, human_id: str) -> List[str]:
        """获取 Human 管理的机器列表"""
        with self._data_lock:
            return self._human_machines.get(human_id, []).copy()


# 全局实例
human_manager = HumanManager()
