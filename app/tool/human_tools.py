"""
Tools specific to Human agents for controlling and coordinating machines.
"""

import json
from typing import Any, Dict, List, Optional

from app.agent.world_manager import world_manager
from app.tool.base import BaseTool, ToolResult


class ControlMachineTool(BaseTool):
    """Tool for controlling machines through text commands."""

    name: str = "human_control_machine"
    description: str = "Send text commands to a machine for execution."
    parameters: dict = {
        "type": "object",
        "properties": {
            "machine_id": {
                "type": "string",
                "description": "The ID of the machine to control",
            },
            "command": {
                "type": "string",
                "description": "The text command to send to the machine",
            },
            "offline": {
                "type": "boolean",
                "description": "Whether to execute offline (true: fire-and-forget, false: wait for completion)",
                "default": False
            },
            "caller_id": {
                "type": "string",
                "description": "ID of the human agent calling this tool (automatically injected)",
                "default": ""
            },
        },
        "required": ["machine_id", "command"],
    }

    def __init__(self, machine_registry: Optional[Dict[str, Any]] = None, mcp_server: Optional[Any] = None):
        super().__init__()
        # MCP server reference for direct Machine Agent access
        object.__setattr__(self, '_mcp_server', mcp_server)

    async def execute(self, machine_id: str, command: str, offline: bool = False, caller_id: str = "", **kwargs) -> ToolResult:
        """Execute machine control command."""
        try:
            from app.logger import logger
            logger.info(f"🔧 ControlMachineTool.execute called with caller_id: '{caller_id}' for machine: {machine_id}")

            # Check if machine exists in world
            machine_info = world_manager.get_machine_info(machine_id)
            if not machine_info:
                return ToolResult(
                    error=f"Machine {machine_id} not found in world registry"
                )

            # Check ownership if caller_id is provided
            if caller_id and machine_info.owner and machine_info.owner != caller_id:
                return ToolResult(
                    error=f"Access denied: Machine {machine_id} belongs to {machine_info.owner}, not {caller_id}"
                )

            # Check if machine is active
            if machine_info.status != "active":
                return ToolResult(
                    error=f"Machine {machine_id} is not active (status: {machine_info.status})"
                )

            # 通过RQ队列控制机器人
            result = self._direct_control(machine_id, command, offline=offline, caller_id=caller_id)

            return ToolResult(output=result)

        except Exception as e:
            return ToolResult(error=f"Machine control failed: {str(e)}")

    def _direct_control(self, machine_id: str, command: str, offline: bool = False, caller_id: str = "") -> str:
        """
        通过RQ消息队列控制机器人

        Args:
            machine_id: 机器人ID
            command: 命令内容
            offline: 是否离线执行（True=火拼即忘，False=等待完整执行结果）
            caller_id: 调用者ID
        """
        try:
            from app.logger import logger
            logger.info(f"🚀 _direct_control called with caller_id: '{caller_id}' for machine: {machine_id}")

            # 获取MCP服务器引用
            mcp_server = getattr(self, '_mcp_server', None)

            if mcp_server:
                if offline:
                    # 离线模式：仅确认命令已发送给机器人，不等待结果
                    job_id = mcp_server.enqueue_command(machine_id, command, offline=offline, human_id=caller_id)
                    return f"Command sent to machine {machine_id}: '{command}' - executing offline (job_id: {job_id})"
                else:
                    # 在线模式：等待机器人完整执行ReAct过程并返回结果
                    result = mcp_server.enqueue_command(machine_id, command, offline=offline, human_id=caller_id)
                    return f"Machine {machine_id} completed: {result}"
            else:
                return f"MCP server not available for machine {machine_id}"

        except Exception as e:
            return f"Failed to queue command for {machine_id}: {str(e)}"
