"""
Tools specific to Human agents for controlling and coordinating machines.
"""

import os

import requests as http_requests
from typing import Optional

from app.tool.base import BaseTool, ToolResult

WORLD_SERVER_URL = os.getenv("WORLD_SERVER_URL", "http://localhost:8005")
AGENT_SERVER_URL = os.getenv("AGENT_SERVER_URL", "http://localhost:8004")


class BaseMachineControlTool(BaseTool):
    """Base class for machine control tools with shared validation and execution."""

    def _get_machine_info_from_world(self, machine_id: str) -> Optional[dict]:
        """Query World Server via HTTP to get machine info."""
        try:
            resp = http_requests.get(
                f"{WORLD_SERVER_URL}/api/v1/world/machines",
                timeout=5,
            )
            if resp.status_code == 200:
                data = resp.json()
                items = data.get("data", {}).get("items", [])
                for machine in items:
                    if machine.get("machine_id") == machine_id:
                        return machine
            return None
        except Exception:
            return None

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

            # Check if machine exists in world through World Server HTTP API
            machine_info = self._get_machine_info_from_world(machine_id)
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
        Send command to Machine Agent via Agent Server internal HTTP API.

        Args:
            machine_id: Machine ID
            command: Command content
            offline: Async execution (True=async, False=sync wait)
            caller_id: Caller ID (human_id)
        """
        try:
            from app.logger import logger
            logger.info(f"Sending command (offline={offline}) for machine {machine_id} via Agent Server")

            resp = http_requests.post(
                f"{AGENT_SERVER_URL}/api/v1/agents/internal/{machine_id}/command",
                json={
                    "command": command,
                    "offline": offline,
                },
                timeout=120 if not offline else 10,
            )

            if resp.status_code == 200:
                data = resp.json()
                result = data.get("data", {})
                if offline:
                    job_id = result.get("job_id", "unknown")
                    return f"Command queued for machine {machine_id}: '{command}' (job_id: {job_id}). The machine will execute this task in the background."
                else:
                    return f"Machine {machine_id} completed command. Result: {result.get('result', str(result))}"
            else:
                error_data = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
                error_msg = error_data.get("error", {}).get("message", resp.text[:200])
                return f"Command failed for {machine_id}: {error_msg}"

        except Exception as e:
            return f"Failed to send command for {machine_id}: {str(e)}"


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
