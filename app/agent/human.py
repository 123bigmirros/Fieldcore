"""
Human Agent - 智能指挥官，负责分解任务并协调多个机器人完成任务
"""

import json
import uuid
from typing import Any, Dict, List, Optional

from pydantic import Field

from app.agent.mcp import MCPAgent
from app.logger import logger
from app.prompt.human import (
    SYSTEM_PROMPT,
    NEXT_STEP_PROMPT,
    COMMAND_ERROR_PROMPT,
    MACHINE_DISCOVERY_PROMPT
)


class HumanAgent(MCPAgent):
    """
    智能Human Agent - 直接创建和管理Machine Agent
    """

    name: str = "human_commander"
    description: str = "智能指挥官，负责协调和控制多个机器人完成复杂任务"

    # 使用prompt文件中的提示词
    system_prompt: str = SYSTEM_PROMPT
    next_step_prompt: str = NEXT_STEP_PROMPT

    # Agent类型
    agent_type: str = "human"

    # Human特有属性
    human_id: str = Field(default_factory=lambda: f"commander_{uuid.uuid4().hex[:8]}")



    def __init__(self,
                 human_id: Optional[str] = None,
                 machine_count: int = 3,
                 **kwargs):
        """
        直接初始化 - 不需要判断变量

        Args:
            human_id: 指挥官ID，可选
            machine_count: 要创建的机器人数量
        """
        super().__init__(**kwargs)

        if human_id:
            self.human_id = human_id

        # 存储machine_count供initialize使用
        self.machine_count = machine_count

        logger.info(f"🤖 Human Commander {self.human_id} 已创建")

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

        logger.info(f"✅ Human Commander {self.human_id} 初始化完成")

    async def _update_system_message_with_tool_details(self) -> None:
        """动态更新系统消息，添加工具信息"""
        if not self.mcp_clients or not self.mcp_clients.tool_map:
            return
        # 生成工具列表，只显示Human Agent专用工具
        tools_list = []
        for tool_name, tool_info in self.mcp_clients.tool_map.items():
            # 只显示以human_开头的工具
            if tool_name.startswith('human_') or tool_name.startswith('mcp_python_human_'):
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

    async def create_machine_at_position(self, machine_id: str, position: list) -> bool:
        """在指定位置创建单个机器人"""
        try:
            # 注册机器人到MCP服务器
            result = await self.call_tool(
                "mcp_python_register_machine",
                machine_id=machine_id,
                position=position,
                life_value=10,
                machine_type="worker",
                size=1.0,
                facing_direction=[1.0, 0.0],
                owner=self.human_id
            )
            logger.info(f"  ✅ 创建机器人: {machine_id} 在位置 {position}")
            return True
        except Exception as e:
            logger.error(f"创建机器人 {machine_id} 失败: {e}")
            return False




    async def call_tool(self, tool_name: str, **kwargs) -> Any:
        """调用工具，自动添加caller_id"""
        kwargs["caller_id"] = self.human_id
        return await super().call_tool(tool_name, **kwargs)



    async def run(self, request: Optional[str] = None) -> str:
        """
        直接处理自然语言指令
        """
        try:
            logger.info(f"🎯 Human Commander {self.human_id} 接收任务: {request}")

            # 使用父类的智能执行
            result = await super().run(request)

            logger.info(f"✅ Human Commander {self.human_id} 任务完成")
            return result

        except Exception as e:
            logger.error(f"❌ Human Commander {self.human_id} 执行错误: {e}")
            return f"Human Commander {self.human_id} 遇到错误: {str(e)}"

    # 删除update_machine_cache方法 - 不需要缓存，直接通过工具获取

    # 删除recycle_all_machines方法 - 占位符方法，无实际作用

    async def cleanup(self, *args, **kwargs):
        """清理资源 - 空实现，避免自动删除机器人"""
        # 不做任何实际清理，避免自动删除机器人
        pass


