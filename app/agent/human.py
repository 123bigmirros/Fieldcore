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

    # 直接拥有Machine Agent实例
    machines: Dict[str, Any] = Field(default_factory=dict)  # machine_id -> MachineAgent实例
    machine_info_cache: Dict[str, Any] = Field(default_factory=dict)

    # 执行状态跟踪
    current_task: Optional[str] = None
    active_commands: Dict[str, str] = Field(default_factory=dict)  # command_id -> machine_id

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

        self.machine_count = machine_count

        logger.info(f"🤖 Human Commander {self.human_id} 已创建，将管理 {machine_count} 个机器人")

    async def initialize(self, **kwargs) -> None:
        """
        直接初始化流程 - 连接到现有的MCP服务器并创建机器人
        """
        # 如果没有提供连接参数，连接到现有的MCP服务器
        if not kwargs:
            # 连接到现有的MCP服务器，而不是启动新的
            # 使用HTTP连接连接到已经运行的MCP服务器
            kwargs = {
                "connection_type": "http_api",
                "server_url": "http://localhost:8003"
            }

        # 初始化MCP连接
        await super().initialize(**kwargs)

        # 直接创建并添加机器人
        await self.create_machines()

        logger.info(f"✅ Human Commander {self.human_id} 初始化完成，拥有 {len(self.machines)} 个机器人")

    async def create_machines(self) -> None:
        """直接创建机器人Agent"""
        try:
            # 导入MachineAgent
            from app.agent.machine import MachineAgent
            from app.agent.world_manager import Position

            for i in range(self.machine_count):
                machine_id = f"robot_{i+1:02d}"

                # 创建机器人Agent实例（不使用自动判断变量）
                machine = MachineAgent(
                    machine_id=machine_id,
                    location=Position(0.0, 0.0, 0.0),
                    life_value=10,
                    machine_type="worker",
                    agent_type="machine"  # 为Machine Agent设置正确的agent_type
                )

                # 共享Human Agent的MCP连接，但通过agent_type控制工具访问权限
                machine.mcp_clients = self.mcp_clients
                machine.available_tools = self.available_tools

                # 直接注册机器人（不需要重新初始化MCP连接）
                await machine.register_machine()

                # 启动Machine Agent的命令监听器
                await machine.start_command_listener()

                # 添加到管理列表
                self.machines[machine_id] = machine

                logger.info(f"  🤖 创建并注册机器人: {machine_id}")

        except Exception as e:
            logger.error(f"创建机器人失败: {e}")

    async def send_command_to_machine(self, machine_id: str, command_type: str, parameters: dict = None) -> dict:
        """向机器人发送命令"""
        try:
            result = await self.call_tool(
                "mcp_python_send_command_to_machine",
                machine_id=machine_id,
                command_type=command_type,
                parameters=parameters or {}
            )

            if hasattr(result, 'output') and result.output:
                # 尝试解析command_id用于跟踪
                try:
                    result_data = json.loads(result.output)
                    command_id = result_data.get("command_id")
                    if command_id:
                        self.active_commands[command_id] = machine_id
                except:
                    pass
                return {"status": "success", "data": result.output}
            else:
                return {"status": "success", "data": str(result)}
        except Exception as e:
            # 添加错误处理提示
            from app.schema import Message
            self.memory.add_message(Message.system_message(
                COMMAND_ERROR_PROMPT.format(error=str(e))
            ))
            return {"status": "error", "message": str(e)}

    async def wait_for_command_completion(self, command_id: str, timeout: int = 30) -> dict:
        """等待命令完成"""
        try:
            result = await self.call_tool(
                "mcp_python_wait_for_command_completion",
                command_id=command_id,
                timeout=timeout
            )

            # 从活动命令列表中移除已完成的命令
            if command_id in self.active_commands:
                del self.active_commands[command_id]

            # 从ToolResult中提取output
            data = result.output if hasattr(result, 'output') else str(result)
            return {"status": "success", "data": data}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    async def get_machine_status(self, machine_id: str) -> dict:
        """获取机器人状态"""
        try:
            result = await self.call_tool("mcp_python_get_machine_info", machine_id=machine_id)
            # 从ToolResult中提取output
            data = result.output if hasattr(result, 'output') else str(result)
            return {"status": "success", "data": data}
        except Exception as e:
            return {"status": "error", "message": str(e)}

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

            # 更新机器人信息缓存
            await self.update_machine_cache()

            # 分析任务
            if request:
                await self.analyze_task(request)

            # 构建当前状态信息
            status_info = f"当前拥有 {len(self.machines)} 个机器人: {', '.join(self.machines.keys())}"
            active_commands_info = f"活动命令数: {len(self.active_commands)}"

            # 添加状态消息
            from app.schema import Message
            self.memory.add_message(Message.system_message(
                f"🎯 当前任务状态：{status_info}\n"
                f"📊 执行状态：{active_commands_info}\n"
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

    async def update_machine_cache(self) -> None:
        """更新机器人信息缓存"""
        for machine_id in list(self.machines.keys()):
            try:
                result = await self.call_tool("mcp_python_get_machine_info", machine_id=machine_id)
                # 从ToolResult中提取output
                result_str = result.output if hasattr(result, 'output') and result.output else str(result)

                if result and "not found" not in result_str.lower():
                    try:
                        machine_data = json.loads(result_str)
                        self.machine_info_cache[machine_id] = machine_data
                    except json.JSONDecodeError:
                        pass
                else:
                    # 机器人不存在，从管理列表移除
                    if machine_id in self.machines:
                        del self.machines[machine_id]
                    if machine_id in self.machine_info_cache:
                        del self.machine_info_cache[machine_id]

            except Exception as e:
                logger.warning(f"更新机器人 {machine_id} 信息失败: {e}")

    async def cleanup(self) -> None:
        """清理资源"""
        try:
            # 停止所有机器人的命令监听器
            for machine in self.machines.values():
                try:
                    await machine.stop_command_listener()
                except Exception as e:
                    logger.warning(f"停止机器人 {machine.machine_id} 监听器失败: {e}")

            # 清理所有机器人
            for machine in self.machines.values():
                try:
                    await machine.cleanup()
                except Exception as e:
                    logger.warning(f"清理机器人 {machine.machine_id} 失败: {e}")

            # 清理Human Agent
            await super().cleanup()

            logger.info(f"🧹 Human Commander {self.human_id} 已清理")

        except Exception as e:
            logger.error(f"Human Agent清理失败: {e}")


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
