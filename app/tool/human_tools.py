"""
Tools specific to Human agents for controlling and coordinating machines.
"""

import json
from typing import Any, Dict, List, Optional

from app.service.world_service import world_service
from app.tool.base import BaseTool, ToolResult


class BaseMachineControlTool(BaseTool):
    """基础机器人控制工具类，提供共享的验证和执行逻辑"""

    def __init__(self, mcp_server: Optional[Any] = None):
        super().__init__()
        # MCP server reference for direct Machine Agent access
        object.__setattr__(self, '_mcp_server', mcp_server)

    async def _validate_and_execute(
        self,
        machine_id: str,
        command: str,
        offline: bool,
        caller_id: str = "",
        **kwargs
    ) -> ToolResult:
        """验证机器人状态并执行命令的共享逻辑"""
        try:
            from app.logger import logger
            mode = "async" if offline else "sync"
            logger.info(f"🔧 {self.name} called ({mode} mode) with caller_id: '{caller_id}' for machine: {machine_id}")

            # Check if machine exists in world through world_service
            machine_info = world_service.get_machine_info(machine_id)
            if not machine_info:
                return ToolResult(
                    error=f"Machine {machine_id} not found in world registry"
                )

            # Check ownership if caller_id is provided
            if caller_id and machine_info["owner"] and machine_info["owner"] != caller_id:
                return ToolResult(
                    error=f"Access denied: Machine {machine_id} belongs to {machine_info['owner']}, not {caller_id}"
                )

            # Check if machine is active
            if machine_info["status"] != "active":
                return ToolResult(
                    error=f"Machine {machine_id} is not active (status: {machine_info['status']})"
                )

            # 通过RQ队列控制机器人
            result = self._enqueue_command(machine_id, command, offline=offline, caller_id=caller_id)

            return ToolResult(output=result)

        except Exception as e:
            return ToolResult(error=f"Machine control failed: {str(e)}")

    def _enqueue_command(self, machine_id: str, command: str, offline: bool, caller_id: str = "") -> str:
        """
        通过RQ消息队列控制机器人

        Args:
            machine_id: 机器人ID
            command: 命令内容
            offline: 是否离线执行（True=异步，False=同步等待）
            caller_id: 调用者ID
        """
        try:
            from app.logger import logger
            logger.info(f"🚀 Enqueueing command (offline={offline}) for machine {machine_id}")

            # 获取MCP服务器引用
            mcp_server = getattr(self, '_mcp_server', None)

            if mcp_server:
                if offline:
                    # 离线模式：仅确认命令已发送给机器人，不等待结果
                    job_id = mcp_server.enqueue_command(machine_id, command, offline=True, human_id=caller_id)
                    return f"✅ Long-term command queued for machine {machine_id}: '{command}' (job_id: {job_id}). The machine will execute this task in the background."
                else:
                    # 在线模式：等待机器人完整执行ReAct过程并返回结果
                    result = mcp_server.enqueue_command(machine_id, command, offline=False, human_id=caller_id)
                    return f"✅ Machine {machine_id} completed short-term command. Result: {result}"
            else:
                return f"❌ MCP server not available for machine {machine_id}"

        except Exception as e:
            return f"❌ Failed to queue command for {machine_id}: {str(e)}"


class SendShortCommandTool(BaseMachineControlTool):
    """发送短期命令工具 - 同步执行，等待完成返回结果"""

    name: str = "human_send_short_command"
    description: str = """Send a short-term command to a machine and wait for completion.
Use this for quick tasks that should complete within seconds (e.g., check status, move one step, quick scan).
The tool will block until the machine finishes executing and returns the result."""

    parameters: dict = {
        "type": "object",
        "properties": {
            "machine_id": {
                "type": "string",
                "description": "The ID of the machine to control",
            },
            "command": {
                "type": "string",
                "description": "The short-term command to send (e.g., 'check your status', 'move forward one step')",
            },
            "caller_id": {
                "type": "string",
                "description": "ID of the human agent calling this tool (automatically injected)",
                "default": ""
            },
        },
        "required": ["machine_id", "command"],
    }

    async def execute(self, machine_id: str, command: str, caller_id: str = "", **kwargs) -> ToolResult:
        """执行短期命令 - 同步等待完成"""
        return await self._validate_and_execute(
            machine_id=machine_id,
            command=command,
            offline=False,  # 短期命令使用同步模式
            caller_id=caller_id,
            **kwargs
        )


class SendLongCommandTool(BaseMachineControlTool):
    """发送长期命令工具 - 异步执行，立即返回任务ID"""

    name: str = "human_send_long_command"
    description: str = """Send a long-term command to a machine for asynchronous execution.
Use this for complex or time-consuming tasks (e.g., 'explore the area', 'patrol for 10 minutes', 'search for targets').
The tool will return immediately with a job_id, and the machine will execute the task in the background."""

    parameters: dict = {
        "type": "object",
        "properties": {
            "machine_id": {
                "type": "string",
                "description": "The ID of the machine to control",
            },
            "command": {
                "type": "string",
                "description": "The long-term command to send (e.g., 'patrol the perimeter', 'search for enemies')",
            },
            "caller_id": {
                "type": "string",
                "description": "ID of the human agent calling this tool (automatically injected)",
                "default": ""
            },
        },
        "required": ["machine_id", "command"],
    }

    async def execute(self, machine_id: str, command: str, caller_id: str = "", **kwargs) -> ToolResult:
        """执行长期命令 - 异步执行，立即返回"""
        return await self._validate_and_execute(
            machine_id=machine_id,
            command=command,
            offline=True,  # 长期命令使用异步模式
            caller_id=caller_id,
            **kwargs
        )
