"""
Human Agent — intelligent commander that decomposes tasks and coordinates machines.
"""

import os
import uuid

import requests
from typing import Any, Dict, List, Optional, Tuple

from pydantic import Field, PrivateAttr

from app.agent.mcp import MCPAgent
from app.logger import logger
from app.service.map_manager import map_manager
from app.prompt.human import (
    SYSTEM_PROMPT,
    NEXT_STEP_PROMPT,
)

WORLD_SERVER_URL = os.getenv("WORLD_SERVER_URL", "http://localhost:8005")
MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://localhost:8003")


class HumanAgent(MCPAgent):
    """
    Intelligent Human Agent — creates and manages Machine Agents directly.
    """

    name: str = "human_commander"
    description: str = "Intelligent commander that coordinates machines to complete tasks"

    # 使用prompt文件中的提示词
    system_prompt: str = SYSTEM_PROMPT
    next_step_prompt: str = NEXT_STEP_PROMPT

    # Agent类型
    agent_type: str = "human"

    # Enable parallel tool execution for concurrent machine commands
    parallel_tool_calls: bool = True

    # Human特有属性
    human_id: str = Field(default_factory=lambda: f"commander_{uuid.uuid4().hex[:8]}")
    global_map: Dict[str, Any] = Field(default_factory=dict)

    _map_manager: Any = PrivateAttr(default_factory=lambda: map_manager)



    def __init__(self,
                 human_id: Optional[str] = None,
                 machine_count: int = 3,
                 **kwargs):
        """
        Initialize the Human Agent.

        Args:
            human_id: Commander ID, optional
            machine_count: Number of machines to create
        """
        super().__init__(**kwargs)

        if human_id:
            self.human_id = human_id

        # Store machine_count for initialize
        self.machine_count = machine_count

        # Format system_prompt with actual human_id and machine info
        machine_ids = ", ".join(
            f"{self.human_id}_robot_{i:02d}" for i in range(1, machine_count + 1)
        )
        self.system_prompt = SYSTEM_PROMPT.format(
            human_id=self.human_id,
            machine_count=machine_count,
            machine_ids=machine_ids,
        )

        logger.info(f"Human Commander {self.human_id} created")
        self.refresh_global_map()

    async def initialize(self, **kwargs) -> None:
        """
        Initialize — connect to MCP server.
        """
        # HTTP API connection
        if not kwargs or kwargs.get("connection_type") == "http_api":
            kwargs = {
                "connection_type": "http_api",
                "server_url": MCP_SERVER_URL,
            }

        # Initialize MCP connection
        await super().initialize(**kwargs)

        # Dynamically add tool info to system message
        await self._update_system_message_with_tool_details()

        logger.info(f"Human Commander {self.human_id} initialized")

    async def _update_system_message_with_tool_details(self) -> None:
        """Dynamically update system message with tool details."""
        if not self.mcp_clients or not self.mcp_clients.tool_map:
            return
        # Generate tool list, only show Human Agent tools
        tools_list = []
        for tool_name, tool_info in self.mcp_clients.tool_map.items():
            # Only show tools prefixed with human_
            if tool_name.startswith('human_') or tool_name.startswith('mcp_python_human_'):
                if hasattr(tool_info, 'description'):
                    description = tool_info.description
                    tools_list.append(f"- {tool_name}: {description}")
        tools_text = "\n".join(tools_list)
        # Append tool details to the existing system prompt instead of replacing it
        if self.memory.messages and self.memory.messages[0].role == "system":
            from app.schema import Message
            tool_names = list(self.mcp_clients.tool_map.keys())
            tools_info = ", ".join(tool_names)
            original_content = self.memory.messages[0].content
            tool_section = f"\n\n🔧 当前可用工具:\n{tools_text}\n\nAvailable MCP tools: {tools_info}"
            self.memory.messages[0] = Message.system_message(original_content + tool_section)

    async def create_machine_at_position(self, machine_id: str, position: list) -> bool:
        """Create a single machine at the specified position."""
        try:
            # 通过 HTTP API 注册机器人到 World Server
            resp = requests.post(
                f"{WORLD_SERVER_URL}/api/v1/world/machines",
                json={
                    "machine_id": machine_id,
                    "position": position,
                    "life_value": 10,
                    "machine_type": "worker",
                    "size": 1.0,
                    "facing_direction": [1.0, 0.0],
                    "owner": self.human_id,
                    "view_size": 3
                },
                timeout=5
            )
            result = resp.json()

            # Check the response envelope
            data = result.get("data", result)
            if result.get("success") or data.get("machine_id"):
                logger.info(f"  Created machine: {machine_id} at position {position}")
                self._map_manager.register_machine(machine_id, self._extract_xy(position))
                self.refresh_global_map()
                return True
            else:
                logger.error(f"Failed to create machine {machine_id}: {result.get('error', 'Unknown error')}")
                return False

        except Exception as e:
            logger.error(f"Failed to create machine {machine_id}: {e}")
            return False




    async def call_tool(self, tool_name: str, **kwargs) -> Any:
        """Call a tool, automatically adding caller_id."""
        kwargs["caller_id"] = self.human_id
        return await super().call_tool(tool_name, **kwargs)



    async def run(self, request: Optional[str] = None) -> str:
        """Process a natural language instruction."""
        try:
            logger.info(f"Human Commander {self.human_id} received task: {request}")
            self.refresh_global_map()

            # Inject machine context into the user request so the LLM knows
            # which machine_ids to use when calling tools.
            if request:
                machine_ids = [
                    f"{self.human_id}_robot_{i:02d}"
                    for i in range(1, self.machine_count + 1)
                ]
                ids_str = ", ".join(machine_ids)
                request = (
                    f"{request}\n\n"
                    f"[Context] 你的机器人ID列表: {ids_str}。"
                    f"请直接使用 human_send_short_command 工具向这些机器人发送指令，"
                    f"machine_id 使用上述完整ID。"
                )

            # 使用父类的智能执行
            result = await super().run(request)

            logger.info(f"Human Commander {self.human_id} task completed")
            self.refresh_global_map()
            return result

        except Exception as e:
            logger.error(f"Human Commander {self.human_id} execution error: {e}")
            return f"Human Commander {self.human_id} encountered an error: {str(e)}"

    async def cleanup(self, *args, **kwargs):
        """Clean up resources — no-op to avoid auto-deleting machines."""
        pass

    def refresh_global_map(self) -> None:
        """Refresh the global map snapshot for the Human Agent."""
        self.global_map = self._map_manager.get_global_map_snapshot()

    @staticmethod
    def _extract_xy(position: List[float]) -> Tuple[float, float]:
        """Extract 2D coordinates from a position vector."""
        if not position:
            return 0.0, 0.0
        x_coord = float(position[0])
        y_coord = float(position[1]) if len(position) > 1 else 0.0
        return x_coord, y_coord
