import logging
import sys


logging.basicConfig(level=logging.INFO, handlers=[logging.StreamHandler(sys.stderr)])

import argparse
import asyncio
import atexit
import json
import uuid
from inspect import Parameter, Signature
from typing import Any, Dict, List, Optional

import redis
from rq import Queue, Worker

from mcp.server.fastmcp import FastMCP

from app.logger import logger
from app.tool.base import BaseTool
from app.tool.human_tools import ControlMachineTool
from app.tool.machine_tools import CheckEnvironmentTool, StepMovementTool, LaserAttackTool, GetSelfStatusTool
from app.agent.world_manager import WorldManager, Position
from app.agent.machine import MachineAgent


# 全局MCP服务器实例引用，用于RQ任务
_mcp_server_instance = None

def execute_machine_command(machine_id: str, command: str, human_id: str = ""):
    """
    RQ任务函数：执行机器人命令
    """
    import asyncio
    from app.logger import logger

    try:
        logger.info(f"🔄 RQ Worker executing command for machine {machine_id} (owner: {human_id}): {command}")

        if _mcp_server_instance is None:
            raise RuntimeError("MCP Server instance not available")

        # 在二维结构中查找机器人
        machine_agent = None
        if human_id and human_id in _mcp_server_instance.machine_agents:
            if machine_id in _mcp_server_instance.machine_agents[human_id]:
                machine_agent = _mcp_server_instance.machine_agents[human_id][machine_id]

        # 如果没找到，尝试在所有human中查找（向后兼容）
        if not machine_agent:
            for hid, machines in _mcp_server_instance.machine_agents.items():
                if machine_id in machines:
                    machine_agent = machines[machine_id]
                    logger.info(f"Found machine {machine_id} in human {hid}'s collection")
                    break

        if not machine_agent:
            raise ValueError(f"Machine {machine_id} not found in registry")

        # 在新事件循环中执行异步任务
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            result = loop.run_until_complete(machine_agent.run(command))
            logger.info(f"✅ RQ Worker completed command: {result}")
            return result
        finally:
            loop.close()

    except Exception as e:
        logger.error(f"❌ RQ Worker command failed: {e}")
        raise


class MCPServer:
    """MCP Server implementation with tool registration and management."""

    def __init__(self, name: str = "openmanus"):
        self.server = FastMCP(name)
        self.tools: Dict[str, BaseTool] = {}

        # Initialize WorldManager - THIS IS THE KEY PART
        self.world_manager = WorldManager()
        logger.info("MCPServer: WorldManager initialized")

        # Initialize Redis connection and RQ queue
        # 注意：RQ需要decode_responses=False来避免编码问题
        self.redis_conn = redis.Redis(host='localhost', port=6379, db=0, decode_responses=False)
        self.task_queue = Queue('machine_commands', connection=self.redis_conn)
        logger.info("MCPServer: Redis and RQ queue initialized")

        # Initialize Machine Agent registry - 二维结构：human_id -> {machine_id -> MachineAgent}
        self.machine_agents: Dict[str, Dict[str, MachineAgent]] = {}  # human_id -> {machine_id -> MachineAgent实例}
        logger.info("MCPServer: Machine Agent registry initialized with hierarchical structure")

        # Initialize human tools (只有Human Agent可以使用)
        self.human_tools = {
            "control_machine": ControlMachineTool(mcp_server=self)
        }

        # Initialize machine tools (只有Machine Agent可以使用)
        # 传递世界管理器实例给工具
        self.machine_tools = {
            "check_environment": CheckEnvironmentTool(),
            "step_movement": StepMovementTool(),
            "laser_attack": LaserAttackTool(),
            "get_self_status": GetSelfStatusTool()
        }

        # 设置工具的世界管理器引用
        for tool in self.machine_tools.values():
            if hasattr(tool, 'set_world_manager'):
                tool.set_world_manager(self.world_manager)

        # 将工具添加到主工具字典中，但标记其类型
        for name, tool in self.human_tools.items():
            self.tools[name] = tool
            tool.agent_type = "human"  # 标记为Human工具

        for name, tool in self.machine_tools.items():
            self.tools[name] = tool
            tool.agent_type = "machine"  # 标记为Machine工具

        # World state management tools are registered directly in register_all_tools()

        # 设置全局实例引用用于RQ任务
        global _mcp_server_instance
        _mcp_server_instance = self

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

            # 对于RQ Worker中运行的Machine Agent，使用HTTP API连接到主服务器
            # 这样可以确保使用主服务器的world_manager实例
            await machine_agent.initialize(
                connection_type="http_api",
                server_url="http://localhost:8003"
            )
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

    def enqueue_command(self, machine_id: str, command: str, offline: bool = True, human_id: str = ""):
        """
        添加命令到RQ队列

        Args:
            machine_id: 机器人ID
            command: 命令内容
            offline: 是否离线执行（True=立即返回job_id，False=等待完成返回结果）
            human_id: 机器人所有者ID

        Returns:
            如果offline=True，返回job_id
            如果offline=False，返回执行结果
        """
        try:
            # 检查机器人是否存在
            machine_info = self.world_manager.get_machine_info(machine_id)
            if not machine_info:
                raise ValueError(f"Machine {machine_id} not found in world registry")

            # 使用RQ排队任务（传递human_id）
            job = self.task_queue.enqueue(
                execute_machine_command,
                machine_id,
                command,
                human_id,  # 传递human_id参数
                job_timeout='5m'
            )

            logger.info(f"📥 Command {job.id} enqueued for machine {machine_id} (owner: {human_id}): {command}")

            if not offline:
                # 在线模式：等待任务完成
                logger.info(f"⏳ Waiting for command {job.id} to complete...")

                # 使用轮询方式等待任务完成 - 兼容不同RQ版本
                import time
                timeout = 300  # 5分钟超时
                start_time = time.time()

                while job.get_status() not in ['finished', 'failed', 'canceled']:
                    if time.time() - start_time > timeout:
                        logger.error(f"❌ Command {job.id} timed out after {timeout} seconds")
                        raise TimeoutError(f"Job {job.id} timed out after {timeout} seconds")
                    time.sleep(0.1)  # 每100ms检查一次

                if job.get_status() == 'failed':
                    logger.error(f"❌ Command {job.id} failed: {job.exc_info}")
                    raise Exception(f"Job failed: {job.exc_info}")
                elif job.get_status() == 'canceled':
                    logger.error(f"❌ Command {job.id} was canceled")
                    raise Exception(f"Job was canceled")

                result = job.result
                logger.info(f"✅ Command {job.id} completed with result: {result}")
                return result
            else:
                # 离线模式：不等待，返回job_id
                return job.id

        except Exception as e:
            logger.error(f"❌ Failed to enqueue command for {machine_id}: {e}")
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

        # Close Redis connection
        if self.redis_conn:
            self.redis_conn.close()
            logger.info("Redis connection closed")

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
        async def register_machine_control(machine_id: str, callback_url: str = "", caller_id: str = "") -> str:
            """Register a machine for control by creating Machine Agent in MCP server."""
            try:
                # 检查机器人是否存在于世界中
                machine_info = self.world_manager.get_machine_info(machine_id)
                if not machine_info:
                    return f"Error: Machine {machine_id} not found in world registry"

                # 确保有调用者ID
                if not caller_id:
                    return f"Error: caller_id is required for machine registration"

                # 初始化human的机器人集合（如果不存在）
                if caller_id not in self.machine_agents:
                    self.machine_agents[caller_id] = {}

                # 如果Machine Agent不存在，创建它
                if machine_id not in self.machine_agents[caller_id]:
                    machine_agent = await self._create_machine_agent(machine_id)
                    self.machine_agents[caller_id][machine_id] = machine_agent
                    logger.info(f"✅ Machine Agent {machine_id} created and registered for {caller_id}")
                    return f"Machine {machine_id} control registered successfully for {caller_id} (Agent created)"
                else:
                    logger.info(f"✅ Machine Agent {machine_id} already exists for {caller_id}")
                    return f"Machine {machine_id} control already registered for {caller_id}"

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

        # 删除send_command_to_machine工具 - 不再使用命令队列

        # 删除get_machine_commands工具 - 不再使用命令队列

        # 删除update_command_status工具 - 不再使用命令队列

        # 删除wait_for_command_completion工具 - 不再使用命令队列

        # 删除get_command_status工具 - 不再使用命令队列

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


