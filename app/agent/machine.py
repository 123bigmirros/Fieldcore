"""
Machine Agent - 智能机器人，执行来自Human Agent的本地任务
"""

import asyncio
import json
import time
import uuid
from typing import Any, Dict, List, Optional

from pydantic import Field

from app.agent.mcp import MCPAgent
from app.agent.world_manager import Position
from app.logger import logger
from app.schema import AgentState
from app.prompt.machine import (
    SYSTEM_PROMPT,
    NEXT_STEP_PROMPT,
    COMMAND_LISTENER_PROMPT,
    MOVE_COMMAND_PROMPT,
    ACTION_COMMAND_PROMPT,
    ENVIRONMENT_CHECK_PROMPT,
    COMMAND_ERROR_PROMPT,
    STATUS_UPDATE_PROMPT,
    LISTENER_START_PROMPT
)


class MachineAgent(MCPAgent):
    """
    智能机器人Agent - 由Human Agent直接管理

    具备以下核心能力：
    - 精确的3D空间移动控制
    - 智能环境感知和分析
    - 灵活的动作执行系统
    - 实时状态监控和报告
    - 高效的命令响应机制
    """

    name: str = "smart_machine"
    description: str = "智能机器人，能够在虚拟世界中移动并执行各种任务"

    # 使用prompt文件中的提示词
    system_prompt: str = SYSTEM_PROMPT
    next_step_prompt: str = NEXT_STEP_PROMPT

    # Agent类型
    agent_type: str = "machine"

    # 机器人特有属性
    machine_id: str = Field(default_factory=lambda: f"machine_{uuid.uuid4().hex[:8]}")
    location: Position = Field(default_factory=lambda: Position(0.0, 0.0, 0.0))
    life_value: int = Field(default=10)
    machine_type: str = Field(default="worker")
    size: float = Field(default=1.0)  # 机器人大小（碰撞检测半径）

    # 执行状态跟踪（保留基本属性）
    command_history: List[Dict[str, Any]] = Field(default_factory=list)
    last_action: Optional[str] = None

    def __init__(self,
                 machine_id: Optional[str] = None,
                 location: Optional[Position] = None,
                 life_value: int = 10,
                 machine_type: str = "worker",
                 size: float = 1.0,
                 **kwargs):
        """
        直接初始化 - 不需要判断变量

        Args:
            machine_id: 机器人ID，可选
            location: 初始位置，可选
            life_value: 生命值
            machine_type: 机器人类型
            size: 机器人大小（碰撞检测半径）
        """
        super().__init__(**kwargs)

        # 设置机器人特有属性
        if machine_id:
            self.machine_id = machine_id
        if location:
            self.location = location
        self.life_value = life_value
        self.machine_type = machine_type
        self.size = size

        logger.info(f"🤖 Smart Machine {self.machine_id} 已创建 at {self.location} (size: {self.size})")

    # 删除initialize方法 - Machine Agent由MCP服务器直接创建和管理

    # 删除initialize_with_shared_connection方法 - 不再使用共享连接模式

    # 删除register_machine方法 - 由MCP服务器处理注册

    async def update_system_prompt(self) -> None:
        """更新系统提示词包含当前机器人信息"""
        x, y, z = self.location.coordinates[0], self.location.coordinates[1], self.location.coordinates[2] if len(self.location.coordinates) > 2 else 0.0
        formatted_prompt = self.system_prompt.format(
            machine_id=self.machine_id,
            machine_type=self.machine_type,
            current_position=f"({x}, {y}, {z})",
            life_value=self.life_value
        )

        from app.schema import Message
        self.memory.add_message(Message.system_message(formatted_prompt))

    # 删除remove_from_world方法 - 很少使用，由MCP服务器管理

    async def think(self) -> bool:
        """重写think方法以支持内部连接模式"""
        if hasattr(self, '_internal_server'):
            # 内部连接模式 - 跳过MCP连接检查，直接使用ToolCallAgent的think
            from app.agent.toolcall import ToolCallAgent
            return await ToolCallAgent.think(self)
        else:
            # 外部连接模式 - 使用父类方法
            return await super().think()

    async def cleanup(self, *args, **kwargs):
        """清理机器人资源 - 内部连接模式不需要清理MCP连接"""
        if hasattr(self, '_internal_server'):
            # 内部连接模式，不需要断开连接
            logger.info(f"Machine {self.machine_id} cleanup completed (internal mode)")
        else:
            # 外部连接模式，调用父类清理
            await super().cleanup(*args, **kwargs)

    def _should_finish_execution(self, name: str, **kwargs) -> bool:
        """确定工具执行是否应该结束agent"""
        # 检查生命值是否过低
        if self.life_value <= 0:
            return True

        # 调用父类方法
        return super()._should_finish_execution(name, **kwargs)

    # 删除start_command_listener方法 - 不再使用listener模式

    # 删除_listen_for_commands方法 - 不再使用listener模式

    # 删除_preempt_and_execute_command方法 - 不再使用挤占式执行

    # 删除_process_single_command方法 - 不再使用listener模式

    # 删除_execute_command方法 - 不再使用listener模式，改用_direct_control

    # 删除stop_command_listener方法 - 不再使用listener模式

    # 删除get_pending_commands方法 - 命令监听器中已有相同功能

    # 删除execute_command方法 - 与_execute_command重复，使用_process_single_command代替

    async def process_command_type(self, command_type: str, parameters: Dict[str, Any]) -> str:
        """处理不同类型的命令"""
        if command_type == "move_to":
            return await self.handle_move_to_command(parameters)
        elif command_type == "perform_action":
            # 兼容旧的perform_action命令，转换为具体攻击类型
            action = parameters.get("action", "")
            if action == "laser_attack":
                return await self.handle_laser_attack_command(parameters)
            else:
                return f"不支持的动作类型: {action}"
        elif command_type == "check_environment":
            return await self.handle_environment_check_command(parameters)
        elif command_type == "laser_attack":
            return await self.handle_laser_attack_command(parameters)
        else:
            return f"未知命令类型: {command_type}"

    async def handle_move_to_command(self, parameters: Dict[str, Any]) -> str:
        """处理移动命令，使用安全的step_movement"""
        try:
            position = parameters.get("position", [])
            if len(position) >= 2:
                x, y = position[0], position[1]
                z = position[2] if len(position) > 2 else 0.0

                # 添加移动提示
                from app.schema import Message
                current_x, current_y, current_z = self.location.coordinates[0], self.location.coordinates[1], self.location.coordinates[2] if len(self.location.coordinates) > 2 else 0.0
                self.memory.add_message(Message.system_message(
                    MOVE_COMMAND_PROMPT.format(
                        target_position=f"({x}, {y}, {z})",
                        current_position=f"({current_x}, {current_y}, {current_z})"
                    )
                ))

                # 计算移动方向和距离
                current_pos = self.location.coordinates
                direction = [
                    x - current_pos[0],
                    y - current_pos[1],
                    z - (current_pos[2] if len(current_pos) > 2 else 0.0)
                ]
                distance = (direction[0]**2 + direction[1]**2 + direction[2]**2) ** 0.5

                if distance > 0:
                    # 使用安全的step_movement
                    result = await self.call_tool(
                        "step_movement",
                        machine_id=self.machine_id,
                        direction=direction,
                        distance=distance
                    )

                    # 更新本地位置（step_movement会自动更新世界位置）
                    self.location = Position(x, y, z)
                    self.last_action = f"move_to({x}, {y}, {z})"

                    await self.update_status()
                    return f"Machine {self.machine_id} 已安全移动到 ({x}, {y}, {z})"
                else:
                    return f"Machine {self.machine_id} 已在目标位置"
            else:
                return "无效的位置参数"

        except Exception as e:
            return f"移动命令失败: {str(e)}"

    # Note: Generic action handling removed - use specific action tools like laser_attack

    async def handle_environment_check_command(self, parameters: Dict[str, Any]) -> str:
        """处理环境检查命令"""
        try:
            check_type = parameters.get("check_type", "general")
            radius = parameters.get("radius", 3.0)

            # 添加环境检查提示
            from app.schema import Message
            current_x, current_y, current_z = self.location.coordinates[0], self.location.coordinates[1], self.location.coordinates[2] if len(self.location.coordinates) > 2 else 0.0
            self.memory.add_message(Message.system_message(
                ENVIRONMENT_CHECK_PROMPT.format(
                    check_type=check_type,
                    radius=radius,
                    current_position=f"({current_x}, {current_y}, {current_z})"
                )
            ))

            # 使用MCP工具检查环境
            result = await self.call_tool(
                "check_environment",
                machine_id=self.machine_id,
                radius=radius
            )

            self.last_action = f"check_environment({check_type})"
            await self.update_status()
            return f"Machine {self.machine_id} 环境检查完成 (半径: {radius})"

        except Exception as e:
            return f"环境检查失败: {str(e)}"

    async def handle_laser_attack_command(self, parameters: Dict[str, Any]) -> str:
        """处理激光攻击命令"""
        try:
            range_val = parameters.get("range", 5.0)
            damage = parameters.get("damage", 1)

            # 使用MCP工具执行激光攻击
            result = await self.call_tool(
                "laser_attack",
                machine_id=self.machine_id,
                range=range_val,
                damage=damage
            )

            self.last_action = f"laser_attack(range:{range_val}, damage:{damage})"
            await self.update_status()
            return f"Machine {self.machine_id} 发射激光攻击 (射程: {range_val}, 伤害: {damage})"

        except Exception as e:
            return f"激光攻击失败: {str(e)}"

    async def call_tool(self, tool_name: str, **kwargs) -> Any:
        """重写call_tool方法以支持内部连接模式"""
        if hasattr(self, '_internal_server'):
            # 内部连接模式 - 直接调用服务器方法
            server_instance = self._internal_server
            try:
                # 去掉mcp_python_前缀，因为内部调用不需要
                actual_tool_name = tool_name
                if tool_name.startswith("mcp_python_"):
                    actual_tool_name = tool_name[11:]  # 移除"mcp_python_"前缀

                result = await server_instance.call_tool(actual_tool_name, kwargs)
                return result
            except Exception as e:
                logger.error(f"Error calling tool '{tool_name}' internally: {e}")
                raise
        else:
            # 外部连接模式 - 使用父类方法
            return await super().call_tool(tool_name, **kwargs)

    async def update_status(self) -> None:
        """更新机器人状态"""
        # 更新世界管理器中的last_action
        if self.last_action:
            try:
                # 内部连接模式，直接调用服务器方法
                if hasattr(self, '_internal_server'):
                    self._internal_server.world_manager.update_machine_action(self.machine_id, self.last_action)
                else:
                    await self.call_tool(
                        "mcp_python_update_machine_action",
                        machine_id=self.machine_id,
                        action=self.last_action
                    )
            except Exception as e:
                logger.warning(f"Failed to update machine action: {e}")

        # 添加状态更新提示
        from app.schema import Message
        x, y, z = self.location.coordinates[0], self.location.coordinates[1], self.location.coordinates[2] if len(self.location.coordinates) > 2 else 0.0
        self.memory.add_message(Message.system_message(
            STATUS_UPDATE_PROMPT.format(
                machine_id=self.machine_id,
                new_position=f"({x}, {y}, {z})",
                life_value=self.life_value,
                last_action=self.last_action or "无"
            )
        ))

    async def run(self, request: Optional[str] = None) -> str:
        """
        运行机器人Agent或启动命令监听器
        """
        try:
            # 强制重置状态到IDLE，避免重复调用时的状态冲突
            if self.state != AgentState.IDLE:
                logger.warning(f"Machine {self.machine_id} 状态从 {self.state} 重置为 IDLE")
                self.state = AgentState.IDLE
                self.current_step = 0  # 重置步数计数器

            # 检查机器人是否仍然活跃
            try:
                # 内部连接模式，直接查询世界管理器
                if hasattr(self, '_internal_server'):
                    machine_info = self._internal_server.world_manager.get_machine_info(self.machine_id)
                    if not machine_info:
                        return f"Machine {self.machine_id} 不活跃"
                else:
                    machine_info_result = await self.call_tool("mcp_python_get_machine_info", machine_id=self.machine_id)
                    if "not found" in str(machine_info_result).lower():
                        return f"Machine {self.machine_id} 不活跃"
            except Exception as e:
                logger.warning(f"检查机器人状态失败: {e}")

            # 更新系统提示词包含当前状态
            await self.update_system_prompt()

            # 添加当前状态信息
            from app.schema import Message
            self.memory.add_message(Message.system_message(
                f"🎯 当前状态：位置 {self.location}, 生命值 {self.life_value}\n"
                f"📊 执行历史：{len(self.command_history)} 个命令\n"
                f"💡 请使用可用工具响应请求。"
            ))

            # 使用父类MCP agent执行
            result = await super().run(request)
            return result

        except Exception as e:
            logger.error(f"❌ Machine {self.machine_id} 执行错误: {e}")
            # 确保异常时也重置状态
            self.state = AgentState.IDLE
            self.current_step = 0
            return f"Machine {self.machine_id} 遇到错误: {str(e)}"


# 删除create_smart_machine函数 - Machine Agent现在由MCP服务器创建
