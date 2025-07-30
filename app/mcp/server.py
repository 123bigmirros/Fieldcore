import logging
import sys


logging.basicConfig(level=logging.INFO, handlers=[logging.StreamHandler(sys.stderr)])

import argparse
import asyncio
import atexit
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from inspect import Parameter, Signature
from typing import Any, Dict, List, Optional

from mcp.server.fastmcp import FastMCP

from app.logger import logger
from app.tool.base import BaseTool
from app.tool.human_tools import ControlMachineTool, GetMachineStatusTool, PlanTaskTool
from app.tool.machine_tools import CheckEnvironmentTool, MovementTool, MachineActionTool
from app.agent.world_manager import WorldManager, Position


class CommandStatus(Enum):
    """命令执行状态"""
    PENDING = "pending"  # 等待执行
    EXECUTING = "executing"  # 正在执行
    COMPLETED = "completed"  # 执行完成
    FAILED = "failed"  # 执行失败


@dataclass
class MachineCommand:
    """机器指令数据结构"""
    command_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    machine_id: str = ""
    command_type: str = ""  # move_to, perform_action, etc.
    parameters: Dict[str, Any] = field(default_factory=dict)
    status: CommandStatus = CommandStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    result: Optional[str] = None
    error: Optional[str] = None


class MCPServer:
    """MCP Server implementation with tool registration and management."""

    def __init__(self, name: str = "openmanus"):
        self.server = FastMCP(name)
        self.tools: Dict[str, BaseTool] = {}

        # Initialize WorldManager - THIS IS THE KEY PART
        self.world_manager = WorldManager()
        logger.info("MCPServer: WorldManager initialized")

        # Initialize message queue for machine commands
        self.command_queue: Dict[str, List[MachineCommand]] = {}  # machine_id -> commands
        self.command_history: Dict[str, MachineCommand] = {}  # command_id -> command
        logger.info("MCPServer: Command queue initialized")

        # Initialize human tools (只有Human Agent可以使用)
        self.human_tools = {
            "control_machine": ControlMachineTool(),
            "get_machine_status": GetMachineStatusTool(),
            "plan_task": PlanTaskTool()
        }

        # Initialize machine tools (只有Machine Agent可以使用)
        self.machine_tools = {
            "check_environment": CheckEnvironmentTool(),
            "movement": MovementTool(),
            "machine_action": MachineActionTool()
        }

        # 将工具添加到主工具字典中，但标记其类型
        for name, tool in self.human_tools.items():
            self.tools[name] = tool
            tool.agent_type = "human"  # 标记为Human工具

        for name, tool in self.machine_tools.items():
            self.tools[name] = tool
            tool.agent_type = "machine"  # 标记为Machine工具

        # World state management tools are registered directly in register_all_tools()

    def register_tool(self, tool: BaseTool, method_name: Optional[str] = None) -> None:
        """Register a tool with parameter validation and documentation."""
        tool_name = method_name or tool.name
        tool_param = tool.to_param()
        tool_function = tool_param["function"]

        # Define the async function to be registered
        async def tool_method(**kwargs):
            logger.info(f"Executing {tool_name}: {kwargs}")
            result = await tool.execute(**kwargs)

            logger.info(f"Result of {tool_name}: {result}")

            # Handle different types of results (match original logic)
            if hasattr(result, "model_dump"):
                return json.dumps(result.model_dump())
            elif isinstance(result, dict):
                return json.dumps(result)
            return result

        # Set method metadata
        tool_method.__name__ = tool_name
        tool_method.__doc__ = self._build_docstring(tool_function)
        tool_method.__signature__ = self._build_signature(tool_function)

        # Store parameter schema (important for tools that access it programmatically)
        param_props = tool_function.get("parameters", {}).get("properties", {})
        required_params = tool_function.get("parameters", {}).get("required", [])
        tool_method._parameter_schema = {
            param_name: {
                "description": param_details.get("description", ""),
                "type": param_details.get("type", "any"),
                "required": param_name in required_params,
            }
            for param_name, param_details in param_props.items()
        }

        # Register with server
        self.server.tool()(tool_method)
        logger.info(f"Registered tool: {tool_name}")

    def _build_docstring(self, tool_function: dict) -> str:
        """Build a formatted docstring from tool function metadata."""
        description = tool_function.get("description", "")
        param_props = tool_function.get("parameters", {}).get("properties", {})
        required_params = tool_function.get("parameters", {}).get("required", [])

        # Build docstring (match original format)
        docstring = description
        if param_props:
            docstring += "\n\nParameters:\n"
            for param_name, param_details in param_props.items():
                required_str = (
                    "(required)" if param_name in required_params else "(optional)"
                )
                param_type = param_details.get("type", "any")
                param_desc = param_details.get("description", "")
                docstring += (
                    f"    {param_name} ({param_type}) {required_str}: {param_desc}\n"
                )

        return docstring

    def _build_signature(self, tool_function: dict) -> Signature:
        """Build a function signature from tool function metadata."""
        param_props = tool_function.get("parameters", {}).get("properties", {})
        required_params = tool_function.get("parameters", {}).get("required", [])

        parameters = []

        # Follow original type mapping
        for param_name, param_details in param_props.items():
            param_type = param_details.get("type", "")
            default = Parameter.empty if param_name in required_params else None

            # Map JSON Schema types to Python types (same as original)
            annotation = Any
            if param_type == "string":
                annotation = str
            elif param_type == "integer":
                annotation = int
            elif param_type == "number":
                annotation = float
            elif param_type == "boolean":
                annotation = bool
            elif param_type == "object":
                annotation = dict
            elif param_type == "array":
                annotation = list

            # Create parameter with same structure as original
            param = Parameter(
                name=param_name,
                kind=Parameter.KEYWORD_ONLY,
                default=default,
                annotation=annotation,
            )
            parameters.append(param)

        return Signature(parameters=parameters)

    async def cleanup(self) -> None:
        """Clean up server resources."""
        logger.info("Cleaning up resources")
        # Clean up control machine tool registry
        if "control_machine" in self.tools and hasattr(self.tools["control_machine"], "machine_registry"):
            self.tools["control_machine"].machine_registry.clear()

    def register_all_tools(self) -> None:
        """Register all tools with the server."""
        # Register BaseTool instances
        for tool in self.tools.values():
            self.register_tool(tool)

        # Register world state management tools directly
        self._register_world_tools()

    def _register_world_tools(self) -> None:
        """Register world state management tools that use the server's WorldManager."""

        # Register machine tool
        @self.server.tool()
        async def register_machine(machine_id: str, position: list, life_value: int = 10, machine_type: str = "generic") -> str:
            """Register a new machine in the world."""
            try:
                pos = Position(*position)
                self.world_manager.register_machine(
                    machine_id=machine_id,
                    position=pos,
                    life_value=life_value,
                    machine_type=machine_type
                )
                return f"Machine {machine_id} registered successfully at position {pos}"
            except Exception as e:
                return f"Error registering machine {machine_id}: {str(e)}"

        # Get machine info tool
        @self.server.tool()
        async def get_machine_info(machine_id: str) -> str:
            """Get information about a specific machine."""
            try:
                info = self.world_manager.get_machine_info(machine_id)
                if info:
                    return json.dumps({
                        "machine_id": info.machine_id,
                        "position": list(info.position.coordinates),
                        "life_value": info.life_value,
                        "machine_type": info.machine_type,
                        "status": info.status,
                        "last_action": info.last_action
                    })
                else:
                    return f"Error: Machine {machine_id} not found"
            except Exception as e:
                return f"Error getting machine info: {str(e)}"

        # Get all machines tool
        @self.server.tool()
        async def get_all_machines() -> str:
            """Get information about all machines in the world."""
            try:
                machines = self.world_manager.get_all_machines()
                result = {}
                for machine_id, info in machines.items():
                    result[machine_id] = {
                        "machine_id": info.machine_id,
                        "position": list(info.position.coordinates),
                        "life_value": info.life_value,
                        "machine_type": info.machine_type,
                        "status": info.status,
                        "last_action": info.last_action
                    }
                return json.dumps(result)
            except Exception as e:
                return f"Error getting all machines: {str(e)}"

        # Update machine position tool
        @self.server.tool()
        async def update_machine_position(machine_id: str, new_position: list) -> str:
            """Update a machine's position."""
            try:
                pos = Position(*new_position)
                success = self.world_manager.update_machine_position(machine_id, pos)
                if success:
                    return f"Machine {machine_id} position updated to {pos}"
                else:
                    return f"Error: Failed to update position for machine {machine_id}"
            except Exception as e:
                return f"Error updating machine position: {str(e)}"

        # Update machine life tool
        @self.server.tool()
        async def update_machine_life(machine_id: str, life_change: int) -> str:
            """Update a machine's life value."""
            try:
                success = self.world_manager.update_machine_life(machine_id, life_change)
                if success:
                    info = self.world_manager.get_machine_info(machine_id)
                    return f"Machine {machine_id} life updated. Current life: {info.life_value if info else 'unknown'}"
                else:
                    return f"Error: Failed to update life for machine {machine_id}"
            except Exception as e:
                return f"Error updating machine life: {str(e)}"

        # Update machine action tool
        @self.server.tool()
        async def update_machine_action(machine_id: str, action: str) -> str:
            """Update a machine's last action."""
            try:
                success = self.world_manager.update_machine_action(machine_id, action)
                if success:
                    return f"Machine {machine_id} action updated: {action}"
                else:
                    return f"Error: Failed to update action for machine {machine_id}"
            except Exception as e:
                return f"Error updating machine action: {str(e)}"

        # Remove machine tool
        @self.server.tool()
        async def remove_machine(machine_id: str) -> str:
            """Remove a machine from the world."""
            try:
                success = self.world_manager.remove_machine(machine_id)
                if success:
                    return f"Machine {machine_id} removed from world"
                else:
                    return f"Error: Machine {machine_id} not found"
            except Exception as e:
                return f"Error removing machine: {str(e)}"

        # Get nearby machines tool
        @self.server.tool()
        async def get_nearby_machines_world(machine_id: str, radius: float = 10.0) -> str:
            """Get machines within a certain radius of the specified machine."""
            try:
                nearby = self.world_manager.get_nearby_machines(machine_id, radius)
                result = []
                for info in nearby:
                    result.append({
                        "machine_id": info.machine_id,
                        "position": list(info.position.coordinates),
                        "life_value": info.life_value,
                        "machine_type": info.machine_type,
                        "status": info.status,
                        "last_action": info.last_action
                    })
                return json.dumps(result)
            except Exception as e:
                return f"Error getting nearby machines: {str(e)}"

        # Command queue management tools
        @self.server.tool()
        async def send_command_to_machine(machine_id: str, command_type: str, parameters: dict = None) -> str:
            """Send a command to a specific machine. Returns command_id for tracking."""
            try:
                if parameters is None:
                    parameters = {}

                command = MachineCommand(
                    machine_id=machine_id,
                    command_type=command_type,
                    parameters=parameters
                )

                # Add to queue
                if machine_id not in self.command_queue:
                    self.command_queue[machine_id] = []
                self.command_queue[machine_id].append(command)

                # Add to history
                self.command_history[command.command_id] = command

                logger.info(f"Command {command.command_id} sent to machine {machine_id}: {command_type}")
                return json.dumps({
                    "command_id": command.command_id,
                    "status": "sent",
                    "message": f"Command sent to machine {machine_id}"
                })
            except Exception as e:
                return f"Error sending command: {str(e)}"

        @self.server.tool()
        async def get_machine_commands(machine_id: str) -> str:
            """Get pending commands for a specific machine."""
            try:
                if machine_id not in self.command_queue:
                    return json.dumps([])

                commands = []
                for cmd in self.command_queue[machine_id]:
                    # 返回所有未完成的命令（pending, executing）
                    if cmd.status in [CommandStatus.PENDING, CommandStatus.EXECUTING]:
                        commands.append({
                            "command_id": cmd.command_id,
                            "command_type": cmd.command_type,
                            "parameters": cmd.parameters,
                            "status": cmd.status.value,
                            "created_at": cmd.created_at.isoformat()
                        })

                return json.dumps(commands)
            except Exception as e:
                return f"Error getting commands: {str(e)}"

        @self.server.tool()
        async def update_command_status(command_id: str, status: str, result: str = None, error: str = None) -> str:
            """Update the status of a command."""
            try:
                if command_id not in self.command_history:
                    return f"Error: Command {command_id} not found"

                command = self.command_history[command_id]
                command.status = CommandStatus(status)
                command.updated_at = datetime.now()

                if result:
                    command.result = result
                if error:
                    command.error = error

                logger.info(f"Command {command_id} status updated to {status}")
                return f"Command {command_id} status updated to {status}"
            except Exception as e:
                return f"Error updating command status: {str(e)}"

        @self.server.tool()
        async def wait_for_command_completion(command_id: str, timeout: int = 30) -> str:
            """Wait for a command to complete. Returns the final status and result."""
            try:
                if command_id not in self.command_history:
                    return f"Error: Command {command_id} not found"

                # Wait for completion with timeout
                for _ in range(timeout):
                    command = self.command_history[command_id]
                    if command.status in [CommandStatus.COMPLETED, CommandStatus.FAILED]:
                        return json.dumps({
                            "command_id": command_id,
                            "status": command.status.value,
                            "result": command.result,
                            "error": command.error,
                            "completed_at": command.updated_at.isoformat()
                        })
                    await asyncio.sleep(1)

                # Timeout
                return json.dumps({
                    "command_id": command_id,
                    "status": "timeout",
                    "error": f"Command did not complete within {timeout} seconds"
                })
            except Exception as e:
                return f"Error waiting for command: {str(e)}"

        @self.server.tool()
        async def get_command_status(command_id: str) -> str:
            """Get the current status of a command."""
            try:
                if command_id not in self.command_history:
                    return f"Error: Command {command_id} not found"

                command = self.command_history[command_id]
                return json.dumps({
                    "command_id": command_id,
                    "machine_id": command.machine_id,
                    "command_type": command.command_type,
                    "status": command.status.value,
                    "result": command.result,
                    "error": command.error,
                    "created_at": command.created_at.isoformat(),
                    "updated_at": command.updated_at.isoformat()
                })
            except Exception as e:
                return f"Error getting command status: {str(e)}"

        logger.info("MCPServer: All world state management tools registered")
        logger.info("MCPServer: Command queue tools registered")

    def run(self, transport: str = "stdio", host: str = None, port: int = None) -> None:
        """Run the MCP server."""
        # Register all tools
        self.register_all_tools()

        # Register cleanup function (match original behavior)
        atexit.register(lambda: asyncio.run(self.cleanup()))

        # Start server (with same logging as original)
        logger.info(f"Starting OpenManus server ({transport} mode)")

        if transport == "http" and host and port:
            self.server.run(transport=transport, host=host, port=port)
        else:
            self.server.run(transport=transport)


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="OpenManus MCP Server")
    parser.add_argument(
        "--transport",
        choices=["stdio", "http"],
        default="stdio",
        help="Communication method: stdio or http (default: stdio)",
    )
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Host for HTTP transport (default: 0.0.0.0)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8004,
        help="Port for HTTP transport (default: 8004)",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    # Create and run server (maintaining original flow)
    server = MCPServer()
    server.run(transport=args.transport)


