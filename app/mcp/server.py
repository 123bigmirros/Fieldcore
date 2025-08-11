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
from app.tool.machine_tools import CheckEnvironmentTool, StepMovementTool, LaserAttackTool, GetSelfStatusTool
from app.agent.world_manager import WorldManager, Position
from app.agent.machine import MachineAgent


class CommandStatus(Enum):
    """命令执行状态"""
    PENDING = "pending"  # 等待执行
    EXECUTING = "executing"  # 正在执行
    COMPLETED = "completed"  # 执行完成
    FAILED = "failed"  # 执行失败
    CANCELLED = "cancelled"  # 被挤占取消


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

        # Initialize Machine Agent registry
        self.machine_agents: Dict[str, MachineAgent] = {}  # machine_id -> MachineAgent实例
        logger.info("MCPServer: Machine Agent registry initialized")

        # Initialize human tools (只有Human Agent可以使用)
        self.human_tools = {
            "control_machine": ControlMachineTool(mcp_server=self),
            "get_machine_status": GetMachineStatusTool(),
            "plan_task": PlanTaskTool()
        }

        # Initialize machine tools (只有Machine Agent可以使用)
        self.machine_tools = {
            "check_environment": CheckEnvironmentTool(),
            "step_movement": StepMovementTool(),
            "laser_attack": LaserAttackTool(),
            "get_self_status": GetSelfStatusTool()
        }

        # 将工具添加到主工具字典中，但标记其类型
        for name, tool in self.human_tools.items():
            self.tools[name] = tool
            tool.agent_type = "human"  # 标记为Human工具

        for name, tool in self.machine_tools.items():
            self.tools[name] = tool
            tool.agent_type = "machine"  # 标记为Machine工具

        # World state management tools are registered directly in register_all_tools()

    async def _create_machine_agent(self, machine_id: str) -> MachineAgent:
        """创建新的Machine Agent实例"""
        try:
            # 从世界管理器获取机器人信息
            machine_info = self.world_manager.get_machine_info(machine_id)
            if not machine_info:
                raise ValueError(f"Machine {machine_id} not found in world registry")

            # 创建Machine Agent实例
            machine_agent = MachineAgent(
                machine_id=machine_id,
                location=machine_info.position,
                life_value=machine_info.life_value,
                machine_type=machine_info.machine_type,
                size=machine_info.size
            )

            # 设置朝向
            machine_agent.facing_direction = machine_info.facing_direction

            # 设置内部连接模式 - 直接设置属性而不调用initialize
            from app.tool.mcp import MCPClients
            machine_tools = MCPClients()

            # 添加machine专用工具
            for name, tool in self.machine_tools.items():
                machine_tools.tool_map[name] = tool

            # 设置连接和工具，标记为内部模式
            machine_agent.mcp_clients = machine_tools
            machine_agent.available_tools = machine_tools
            machine_agent._internal_server = self  # 保存服务器引用用于内部调用
            machine_agent.initialized = True

            logger.info(f"✅ Created Machine Agent {machine_id} in MCP server")
            return machine_agent

        except Exception as e:
            logger.error(f"❌ Failed to create Machine Agent {machine_id}: {e}")
            raise

    async def call_tool(self, tool_name: str, kwargs: dict) -> Any:
        """内部工具调用方法，供Machine Agent使用"""
        try:
            # 找到对应的工具
            if tool_name.startswith("mcp_python_"):
                # 去掉前缀
                actual_tool_name = tool_name[11:]  # 移除 "mcp_python_"
            else:
                actual_tool_name = tool_name

            # 在已注册的工具中查找
            if actual_tool_name in self.tools:
                tool = self.tools[actual_tool_name]
                result = await tool.execute(**kwargs)
                return result
            else:
                # 查找直接注册的world工具
                world_tools = {
                    "register_machine": "register_machine",
                    "get_machine_info": "get_machine_info",
                    "get_all_machines": "get_all_machines",
                    "update_machine_position": "update_machine_position",
                    "update_machine_life": "update_machine_life",
                    "update_machine_action": "update_machine_action",
                    "remove_machine": "remove_machine",
                    "check_collision": "check_collision"
                }

                if actual_tool_name in world_tools:
                    # 这些工具是直接在服务器中定义的，需要特殊处理
                    return await self._call_world_tool(actual_tool_name, kwargs)
                else:
                    raise ValueError(f"Tool {tool_name} not found")

        except Exception as e:
            logger.error(f"Error calling tool '{tool_name}': {e}")
            raise

    async def _call_world_tool(self, tool_name: str, kwargs: dict) -> Any:
        """调用世界管理工具"""
        try:
            if tool_name == "get_machine_info":
                info = self.world_manager.get_machine_info(kwargs["machine_id"])
                if info:
                    from app.tool.base import ToolResult
                    result_data = {
                        "machine_id": info.machine_id,
                        "position": list(info.position.coordinates),
                        "life_value": info.life_value,
                        "machine_type": info.machine_type,
                        "status": info.status,
                        "last_action": info.last_action,
                        "size": info.size,
                        "facing_direction": list(info.facing_direction)
                    }
                    return ToolResult(output=json.dumps(result_data))
                else:
                    return ToolResult(error=f"Machine {kwargs['machine_id']} not found")

            elif tool_name == "update_machine_position":
                pos = Position(*kwargs["new_position"])
                success, collision_details = self.world_manager.update_machine_position_with_details(kwargs["machine_id"], pos)
                from app.tool.base import ToolResult
                if success:
                    return ToolResult(output=f"Machine {kwargs['machine_id']} position updated to {pos}")
                else:
                    details = "; ".join(collision_details) if collision_details else "Unknown collision"
                    return ToolResult(error=f"Movement blocked: {details}")

            elif tool_name == "update_machine_action":
                success = self.world_manager.update_machine_action(kwargs["machine_id"], kwargs["action"])
                from app.tool.base import ToolResult
                if success:
                    return ToolResult(output=f"Machine {kwargs['machine_id']} action updated: {kwargs['action']}")
                else:
                    return ToolResult(error=f"Failed to update action for machine {kwargs['machine_id']}")

            # 其他工具可以根据需要添加
            else:
                raise ValueError(f"World tool {tool_name} not implemented")

        except Exception as e:
            logger.error(f"Error calling world tool '{tool_name}': {e}")
            raise

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
        async def register_machine(machine_id: str, position: list, life_value: int = 10, machine_type: str = "generic", size: float = 1.0, facing_direction: list = None) -> str:
            """Register a new machine in the world."""
            try:
                pos = Position(*position)
                facing = tuple(facing_direction) if facing_direction else (1.0, 0.0)
                self.world_manager.register_machine(
                    machine_id=machine_id,
                    position=pos,
                    life_value=life_value,
                    machine_type=machine_type,
                    size=size,
                    facing_direction=facing
                )
                return f"Machine {machine_id} registered successfully at position {pos} with size {size}"
            except Exception as e:
                return f"Error registering machine {machine_id}: {str(e)}"

        # Register machine control (create Machine Agent in MCP server)
        @self.server.tool()
        async def register_machine_control(machine_id: str, callback_url: str = "") -> str:
            """Register a machine for control by creating Machine Agent in MCP server."""
            try:
                # 检查机器人是否存在于世界中
                machine_info = self.world_manager.get_machine_info(machine_id)
                if not machine_info:
                    return f"Error: Machine {machine_id} not found in world registry"

                # 如果Machine Agent不存在，创建它
                if machine_id not in self.machine_agents:
                    machine_agent = await self._create_machine_agent(machine_id)
                    self.machine_agents[machine_id] = machine_agent
                    logger.info(f"✅ Machine Agent {machine_id} created and registered")
                    return f"Machine {machine_id} control registered successfully (Agent created)"
                else:
                    logger.info(f"✅ Machine Agent {machine_id} already exists")
                    return f"Machine {machine_id} control already registered"

            except Exception as e:
                error_msg = f"Error registering machine control: {str(e)}"
                logger.error(error_msg)
                return error_msg

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
                        "last_action": info.last_action,
                        "size": info.size,
                        "facing_direction": list(info.facing_direction)
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
                        "last_action": info.last_action,
                        "size": info.size,
                        "facing_direction": list(info.facing_direction)
                    }
                return json.dumps(result)
            except Exception as e:
                return f"Error getting all machines: {str(e)}"

        # Update machine position tool
        @self.server.tool()
        async def update_machine_position(machine_id: str, new_position: list) -> str:
            """Update a machine's position with collision detection."""
            try:
                pos = Position(*new_position)
                success, collision_details = self.world_manager.update_machine_position_with_details(machine_id, pos)
                if success:
                    return f"Machine {machine_id} position updated to {pos}"
                else:
                    if collision_details:
                        details = "; ".join(collision_details)
                        return f"Error: Movement blocked for machine {machine_id}. 碰撞检测: {details}"
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
                        "last_action": info.last_action,
                        "size": info.size,
                        "facing_direction": list(info.facing_direction)
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

        # Obstacle management tools
        @self.server.tool()
        async def add_obstacle(obstacle_id: str, position: list, size: float = 1.0, obstacle_type: str = "static") -> str:
            """Add a new obstacle to the world."""
            try:
                from app.agent.world_manager import Position
                pos = Position(*position)
                success = self.world_manager.add_obstacle(
                    obstacle_id=obstacle_id,
                    position=pos,
                    size=size,
                    obstacle_type=obstacle_type
                )
                if success:
                    return f"Obstacle {obstacle_id} added successfully at position {pos} with size {size}"
                else:
                    return f"Error: Failed to add obstacle {obstacle_id} (collision or already exists)"
            except Exception as e:
                return f"Error adding obstacle: {str(e)}"

        @self.server.tool()
        async def remove_obstacle(obstacle_id: str) -> str:
            """Remove an obstacle from the world."""
            try:
                success = self.world_manager.remove_obstacle(obstacle_id)
                if success:
                    return f"Obstacle {obstacle_id} removed successfully"
                else:
                    return f"Error: Obstacle {obstacle_id} not found"
            except Exception as e:
                return f"Error removing obstacle: {str(e)}"

        @self.server.tool()
        async def get_obstacle_info(obstacle_id: str) -> str:
            """Get information about a specific obstacle."""
            try:
                obstacle = self.world_manager.get_obstacle(obstacle_id)
                if obstacle:
                    return json.dumps({
                        "obstacle_id": obstacle.obstacle_id,
                        "position": list(obstacle.position.coordinates),
                        "size": obstacle.size,
                        "obstacle_type": obstacle.obstacle_type
                    })
                else:
                    return f"Error: Obstacle {obstacle_id} not found"
            except Exception as e:
                return f"Error getting obstacle info: {str(e)}"

        @self.server.tool()
        async def get_all_obstacles() -> str:
            """Get information about all obstacles in the world."""
            try:
                obstacles = self.world_manager.get_all_obstacles()
                result = {}
                for obstacle_id, obstacle in obstacles.items():
                    result[obstacle_id] = {
                        "obstacle_id": obstacle.obstacle_id,
                        "position": list(obstacle.position.coordinates),
                        "size": obstacle.size,
                        "obstacle_type": obstacle.obstacle_type
                    }
                return json.dumps(result)
            except Exception as e:
                return f"Error getting all obstacles: {str(e)}"

        @self.server.tool()
        async def clear_all_obstacles() -> str:
            """Remove all obstacles from the world."""
            try:
                self.world_manager.clear_all_obstacles()
                return "All obstacles removed successfully"
            except Exception as e:
                return f"Error clearing obstacles: {str(e)}"

        @self.server.tool()
        async def check_collision(position: list, size: float = 1.0, exclude_machine_id: str = None) -> str:
            """Check if a position would collide with obstacles or machines."""
            try:
                from app.agent.world_manager import Position
                pos = Position(*position)
                collision = self.world_manager.check_collision(pos, size, exclude_machine_id)
                collision_details = self.world_manager.find_collision_details(pos, size, exclude_machine_id)

                return json.dumps({
                    "collision": collision,
                    "details": collision_details
                })
            except Exception as e:
                return f"Error checking collision: {str(e)}"

        logger.info("MCPServer: All world state management tools registered")
        logger.info("MCPServer: Command queue tools registered")
        logger.info("MCPServer: Obstacle management tools registered")

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


