"""
Machine Agent - 智能机器人，执行来自Human Agent的本地任务
"""

import asyncio
import json
import time
import uuid
from typing import Any, Dict, List, Optional, Tuple

from pydantic import Field, PrivateAttr

from app.agent.mcp import MCPAgent
from app.agent.world_manager import Position
from app.logger import logger
from app.schema import AgentState
from app.service.map_manager import map_manager
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
    local_map: Dict[str, Any] = Field(default_factory=dict)

    _map_manager: Any = PrivateAttr(default_factory=lambda: map_manager)

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
        self._map_manager.register_machine(
            self.machine_id,
            self._extract_xy_from_position(self.location),
        )
        self.refresh_local_map()

    async def initialize(self, **kwargs) -> None:
        """
        初始化流程 - 连接到MCP服务器
        """
        # HTTP API连接
        if not kwargs or kwargs.get("connection_type") == "http_api":
            kwargs = {
                "connection_type": "http_api",
                "server_url": "http://localhost:8003"
            }

        # 初始化MCP连接
        await super().initialize(**kwargs)

        # 动态添加工具信息到系统消息
        await self._update_system_message_with_tool_details()

        logger.info(f"✅ Smart Machine {self.machine_id} 初始化完成")

    async def _update_system_message_with_tool_details(self) -> None:
        """动态更新系统消息，添加工具信息"""
        if not self.mcp_clients or not self.mcp_clients.tool_map:
            return
        # 生成工具列表，只显示Machine Agent专用工具
        tools_list = []
        for tool_name, tool_info in self.mcp_clients.tool_map.items():
            # 只显示以machine_开头的工具
            if tool_name.startswith('machine_') or tool_name.startswith('mcp_python_machine_'):
                # 兼容两种工具格式：字典和HTTPMCPTool对象
                if hasattr(tool_info, 'description'):
                    description = tool_info.description
                    tools_list.append(f"- {tool_name}: {description}")
        tools_text = "\n".join(tools_list)
        # 更新系统消息
        if self.memory.messages and self.memory.messages[0].role == "system":
            content = self.memory.messages[0].content
            base_prompt = content.split("\n\nAvailable MCP tools:")[0]
            new_content = f"{base_prompt}\n\n🔧 当前可用工具:\n{tools_text}"
            from app.schema import Message
            self.memory.messages[0] = Message.system_message(new_content)

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

    def refresh_local_map(self) -> None:
        """同步机器人的本地地图快照。"""
        self.local_map = self._map_manager.get_machine_map_snapshot(self.machine_id)

    @staticmethod
    def _extract_xy_from_position(position: Position) -> Tuple[float, float]:
        """从Position对象中提取平面坐标。"""
        coords = position.coordinates
        x_coord = float(coords[0]) if coords else 0.0
        y_coord = float(coords[1]) if len(coords) > 1 else 0.0
        return x_coord, y_coord



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

            self.refresh_local_map()

            # 检查机器人是否仍然活跃
            try:

                machine_info_result = await self.call_tool("mcp_python_machine_get_self_status", machine_id=self.machine_id)
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
            self.refresh_local_map()
            return result

        except Exception as e:
            logger.error(f"❌ Machine {self.machine_id} 执行错误: {e}")
            # 确保异常时也重置状态
            self.state = AgentState.IDLE
            self.current_step = 0
            return f"Machine {self.machine_id} 遇到错误: {str(e)}"


# 删除create_smart_machine函数 - Machine Agent现在由MCP服务器创建
