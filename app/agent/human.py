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
    TASK_ANALYSIS_PROMPT,
    COMMAND_ERROR_PROMPT,
    TASK_COMPLETION_PROMPT,
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

    # 移除了本地机器人管理，改为通过MCP工具获取

    # 执行状态跟踪（删除命令队列相关属性）
    current_task: Optional[str] = None

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
        直接初始化流程 - 连接到MCP服务器并创建机器人
        """
        connection_type = kwargs.get("connection_type", "http_api")

        if connection_type == "internal":
            # 内部连接模式 - 直接使用服务器实例
            server_instance = kwargs.get("server_instance")
            if server_instance:
                self.mcp_clients = {"internal": server_instance}
                self.available_tools = list(server_instance.tools.keys())
                logger.info(f"Human Commander {self.human_id} 使用内部连接模式")
            else:
                raise ValueError("Internal connection requires server_instance")
        else:
            # 外部连接模式
            if not kwargs or connection_type == "http_api":
                kwargs = {
                    "connection_type": "http_api",
                    "server_url": "http://localhost:8003"
                }
            # 初始化MCP连接
            await super().initialize(**kwargs)

        # 创建指定数量的机器人（如果machine_count > 0）
        if self.machine_count > 0:
            await self.create_machines(self.machine_count)

        logger.info(f"✅ Human Commander {self.human_id} 初始化完成，MCP连接正常")

    async def create_machines(self, machine_count: int) -> None:
        """创建指定数量的机器人到MCP服务器"""
        try:
            logger.info(f"🤖 创建 {machine_count} 个机器人...")

            for i in range(machine_count):
                machine_id = f"robot_{i+1:02d}"

                # 简单的位置分配：网格排列，确保整数坐标
                # 按行排列，每行3个机器人
                row = i // 3
                col = i % 3
                x = float(col - 1)  # -1, 0, 1
                y = float(row)      # 0, 1, 2, ...
                position = [x, y, 0.0]

                # 基本朝向
                facing_direction = [1.0, 0.0]

                # 注册机器人到MCP服务器（传递owner信息）
                result = await self.call_tool(
                    "mcp_python_register_machine",
                    machine_id=machine_id,
                    position=position,
                    life_value=10,
                    machine_type="worker",
                    size=1.0,
                    facing_direction=facing_direction,
                    owner=self.human_id
                )

                logger.info(f"  ✅ 创建机器人: {machine_id} 在位置 {position}")

        except Exception as e:
            logger.error(f"创建机器人失败: {e}")
            raise

    # 删除_find_safe_positions方法 - 这个复杂逻辑应该移到工具层

    # 删除_register_machines_to_control_tool方法 - 不需要手动注册

    # 删除send_command_to_machine方法 - 不再使用命令队列模式

    # 删除wait_for_command_completion方法 - 不再使用命令队列模式

    async def get_machine_status(self, machine_id: str) -> dict:
        """获取机器人状态"""
        try:
            result = await self.call_tool("mcp_python_get_machine_info", machine_id=machine_id)
            # 从ToolResult中提取output
            data = result.output if hasattr(result, 'output') else str(result)
            return {"status": "success", "data": data}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    async def call_tool(self, tool_name: str, **kwargs) -> Any:
        kwargs["caller_id"] = self.human_id
        """重写call_tool方法以支持内部连接模式"""
        # 添加调试日志
        from app.logger import logger
        logger.info(f"🎯 Human Agent {self.human_id} calling tool '{tool_name}' with caller_id='{kwargs.get('caller_id', 'NOT_SET')}')")
        if "internal" in self.mcp_clients:
            # 内部连接模式 - 直接调用服务器方法
            server_instance = self.mcp_clients["internal"]
            try:
                result = await server_instance.server.call_tool(tool_name, kwargs)
                return result
            except Exception as e:
                logger.error(f"Error calling tool '{tool_name}' internally: {e}")
                raise
        else:
            # 外部连接模式 - 使用父类方法
            return await super().call_tool(tool_name, **kwargs)

    async def get_all_machines(self) -> dict:
        """获取所有机器人状态"""
        try:
            result = await self.call_tool("mcp_python_get_all_machines")
            # 从ToolResult中提取output
            data = result.output if hasattr(result, 'output') else str(result)
            return {"status": "success", "data": data}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    async def analyze_task(self, task: str) -> None:
        """分析任务并添加分析提示"""
        from app.schema import Message
        self.memory.add_message(Message.system_message(
            TASK_ANALYSIS_PROMPT.format(task=task)
        ))
        self.current_task = task

    async def complete_task_verification(self) -> None:
        """添加任务完成验证提示"""
        from app.schema import Message
        self.memory.add_message(Message.system_message(TASK_COMPLETION_PROMPT))

    async def run(self, request: Optional[str] = None) -> str:
        """
        直接处理自然语言指令
        """
        try:
            logger.info(f"🎯 Human Commander {self.human_id} 接收任务: {request}")

            # 机器人信息直接通过MCP工具获取，无需缓存

            # 分析任务
            if request:
                await self.analyze_task(request)

            # 构建当前状态信息
            status_info = "机器人由MCP服务器管理"

            # 添加状态消息
            from app.schema import Message
            self.memory.add_message(Message.system_message(
                f"🎯 当前任务状态：{status_info}\n"
                f"📋 任务要求：{request}\n\n"
                f"💡 请使用可用工具分析当前状态并执行任务。"
            ))

            # 使用父类的智能执行
            result = await super().run(request)

            # 任务完成后进行验证
            await self.complete_task_verification()

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


# 便捷创建函数
async def create_human_commander(human_id: str = None,
                               machine_count: int = 3,
                               mcp_connection_params: dict = None) -> HumanAgent:
    """
    便捷创建和初始化Human Commander

    Args:
        human_id: 指挥官ID
        machine_count: 要创建的机器人数量
        mcp_connection_params: MCP连接参数，如果为None则使用默认参数

    Returns:
        已初始化的Human Commander
    """
    commander = HumanAgent(
        human_id=human_id,
        machine_count=machine_count
    )

    if mcp_connection_params:
        await commander.initialize(**mcp_connection_params)
    else:
        await commander.initialize()

    return commander
