# -*- coding: utf-8 -*-
"""
Agent Service - Agent 管理服务门面

统一对外提供 Agent（Human/Machine）的管理接口
内部委托给 HumanManager 和 MachineManager 处理
"""

from threading import Lock
from typing import Dict, List, Optional, Tuple

from app.logger import logger

from .human_manager import human_manager
from .machine_manager import machine_manager


class AgentService:
    """
    Agent 管理服务 - 门面模式

    提供统一的 Agent 管理接口，内部委托给各专门的 Manager 处理
    """

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
        self._initialized = True

    # ==================== 统一创建接口 ====================

    def create_agent(
        self,
        agent_type: str,
        agent_id: str,
        owner_id: str = None,
        machine_count: int = 3,
        position: List[float] = None,
        user_id: str = None
    ) -> Tuple[bool, dict]:
        """
        统一的 Agent 创建接口

        Args:
            agent_type: Agent 类型 ("human" 或 "machine")
            agent_id: Agent ID
            owner_id: 所属 Human ID（machine 必需）
            machine_count: 机器人数量（human 可选，默认 3）
            position: 位置坐标（machine 可选）
            user_id: 用户 ID（可选，用于建立映射关系）

        Returns:
            (success, result_dict)
        """
        if not agent_type or not agent_id:
            return False, {"error": "agent_type and agent_id are required"}

        if agent_type == "human":
            return self._create_human_with_machines(agent_id, machine_count, user_id)

        elif agent_type == "machine":
            if not owner_id:
                return False, {"error": "owner_id is required for machine"}
            return self._create_machine(agent_id, owner_id, position)

        else:
            return False, {"error": f"Invalid agent_type: {agent_type}"}

    def _create_human_with_machines(
        self,
        human_id: str,
        machine_count: int,
        user_id: str = None
    ) -> Tuple[bool, dict]:
        """创建 Human 及其下属机器"""
        # 创建 Human
        success, error = human_manager.create(human_id)
        if not success:
            return False, {"error": error}

        # 建立 user_id 映射
        if user_id:
            self._set_user_human_mapping(user_id, human_id)

        # 创建机器
        actual_count = 0
        for i in range(machine_count):
            machine_id = f"{human_id}_robot_{i+1:02d}"
            m_success, m_error = machine_manager.create(machine_id, human_id)
            if m_success:
                human_manager.add_machine(human_id, machine_id)
                actual_count += 1
            else:
                logger.warning(f"⚠️ 机器人 {machine_id} 创建失败: {m_error}")

        return True, {
            "agent_id": human_id,
            "agent_type": "human",
            "machine_count": actual_count
        }

    def _create_machine(
        self,
        machine_id: str,
        owner_id: str,
        position: List[float] = None
    ) -> Tuple[bool, dict]:
        """创建单个机器"""
        if not human_manager.exists(owner_id):
            return False, {"error": f"Owner {owner_id} not found"}

        success, error = machine_manager.create(machine_id, owner_id, position)
        if not success:
            return False, {"error": error}

        human_manager.add_machine(owner_id, machine_id)

        return True, {
            "agent_id": machine_id,
            "agent_type": "machine",
            "owner_id": owner_id
        }

    def _set_user_human_mapping(self, user_id: str, human_id: str):
        """建立 user_id 和 human_id 的映射"""
        try:
            from .auth_service import auth_service
            auth_service.set_user_human_mapping(user_id, human_id)
        except Exception as e:
            logger.warning(f"建立 user_id 和 human_id 映射失败: {e}")

    # ==================== 查询接口 ====================

    def get_agent_info(self, agent_id: str) -> Optional[dict]:
        """获取 Agent 信息"""
        # 先检查 Human
        info = human_manager.get_info(agent_id)
        if info:
            return info

        # 再检查 Machine
        return machine_manager.get_info(agent_id)

    def get_all_agents(self) -> Dict[str, dict]:
        """获取所有 Agent 信息"""
        from app.logger import logger
        logger.info("🔍 开始获取所有 Agent 信息")
        result = {}
        try:
            logger.info("📋 获取所有 Human 信息")
            human_result = human_manager.get_all()
            result.update(human_result)
            logger.info(f"✅ 获取到 {len(human_result)} 个 Human")
        except Exception as e:
            logger.error(f"❌ 获取 Human 信息失败: {e}", exc_info=True)

        try:
            logger.info("🤖 获取所有 Machine 信息")
            machines = machine_manager.get_all()
            result.update(machines)
            logger.info(f"✅ 获取到 {len(machines)} 个 Machine")
        except Exception as e:
            logger.error(f"❌ 获取 Machine 信息失败: {e}", exc_info=True)

        logger.info(f"✅ 总共获取到 {len(result)} 个 Agent")
        return result

    # ==================== 更新接口 ====================

    def update_agent_info(self, agent_id: str, updates: dict) -> Tuple[bool, str]:
        """更新 Agent 信息"""
        # Human 更新
        if human_manager.exists(agent_id):
            # Human 目前只支持元数据更新
            return True, ""

        # Machine 更新
        if machine_manager.exists(agent_id):
            if 'position' in updates:
                success, error = machine_manager.update_position(agent_id, updates['position'])
                if not success:
                    return False, error

            if 'life_value' in updates:
                info = machine_manager.get_info(agent_id)
                if info:
                    current_life = info.get('life_value', 10)
                    change = updates['life_value'] - current_life
                    machine_manager.update_life(agent_id, change)

            return True, ""

        return False, f"Agent {agent_id} not found"

    # ==================== 命令执行 ====================

    def send_command(self, agent_id: str, command: str) -> Tuple[bool, str]:
        """向 Agent 发送命令"""
        # Human 命令
        if human_manager.exists(agent_id):
            return human_manager.send_command(agent_id, command)

        # # Machine 命令
        # if machine_manager.exists(agent_id):
        #     return machine_manager.send_command(agent_id, command)

        return False, f"Agent {agent_id} not found"

    # ==================== 删除接口 ====================

    def delete_agent(self, agent_id: str) -> Tuple[bool, str]:
        """删除 Agent"""
        # Human 删除
        if human_manager.exists(agent_id):
            # 先获取关联的机器列表
            machine_ids = human_manager.get_machines(agent_id)

            # 删除所有关联的机器
            for m_id in machine_ids:
                machine_manager.delete(m_id)

            # 删除 Human
            return human_manager.delete(agent_id)

        # Machine 删除
        if machine_manager.exists(agent_id):
            # 从所属 Human 的列表中移除
            info = machine_manager.get_info(agent_id)
            if info:
                owner_id = info.get('owner_id')
                if owner_id:
                    human_manager.remove_machine(owner_id, agent_id)

            return machine_manager.delete(agent_id)

        return False, f"Agent {agent_id} not found"

    # ==================== 兼容旧接口 ====================

    def create_human(self, human_id: str, machine_count: int = 3, user_id: str = None) -> Tuple[bool, str, int]:
        """创建 Human Agent（兼容旧接口）"""
        success, result = self._create_human_with_machines(human_id, machine_count, user_id)
        if success:
            return True, human_id, result.get('machine_count', 0)
        return False, result.get('error', 'Unknown error'), 0

    def create_machine(self, machine_id: str, owner_id: str, position: List[float] = None) -> Tuple[bool, str]:
        """创建 Machine Agent（兼容旧接口）"""
        success, result = self._create_machine(machine_id, owner_id, position)
        if success:
            return True, ""
        return False, result.get('error', 'Unknown error')


# 全局实例
agent_service = AgentService()
