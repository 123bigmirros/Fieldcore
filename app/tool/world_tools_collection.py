"""
统一的世界状态管理工具集合 - 包含机器人和障碍物管理的所有工具
"""

import json
from typing import Any, Optional

from app.tool.base import BaseTool, ToolResult
from app.agent.world_manager import Position, world_manager
from app.logger import logger


class RegisterMachineWorldTool(BaseTool):
    """注册机器人到世界中"""

    name: str = "register_machine"
    description: str = "Register a new machine in the world"
    parameters: dict = {
        "type": "object",
        "properties": {
            "machine_id": {"type": "string", "description": "Unique identifier for the machine"},
            "position": {"type": "array", "items": {"type": "number"}, "description": "Position coordinates [x, y, z]"},
            "life_value": {"type": "integer", "description": "Initial life value", "default": 10},
            "machine_type": {"type": "string", "description": "Type of machine", "default": "generic"},
            "size": {"type": "number", "description": "Machine size for collision detection", "default": 1.0},
            "facing_direction": {"type": "array", "items": {"type": "number"}, "description": "Facing direction [x, y]", "default": [1.0, 0.0]},
            "owner": {"type": "string", "description": "Owner of the machine", "default": ""},
            "caller_id": {"type": "string", "description": "Caller ID", "default": ""}
        },
        "required": ["machine_id", "position"]
    }

    async def execute(self, machine_id: str, position: list, life_value: int = 10,
                     machine_type: str = "generic", size: float = 1.0,
                     facing_direction: list = None, owner: str = "",
                     caller_id: str = "", **kwargs) -> ToolResult:
        try:
            pos = Position(*position)
            facing = tuple(facing_direction) if facing_direction else (1.0, 0.0)
            # 使用owner参数，如果没有提供则使用caller_id
            actual_owner = owner if owner else caller_id
            world_manager.register_machine(
                machine_id=machine_id,
                position=pos,
                life_value=life_value,
                machine_type=machine_type,
                size=size,
                facing_direction=facing,
                owner=actual_owner
            )
            return ToolResult(output=f"Machine {machine_id} registered successfully at position {pos} with size {size}")
        except Exception as e:
            return ToolResult(error=f"Error registering machine {machine_id}: {str(e)}")


class RegisterMachineControlTool(BaseTool):
    """注册机器人控制"""

    name: str = "register_machine_control"
    description: str = "Register a machine for control by creating Machine Agent in MCP server"
    parameters: dict = {
        "type": "object",
        "properties": {
            "machine_id": {"type": "string", "description": "Machine identifier"},
            "callback_url": {"type": "string", "description": "Callback URL", "default": ""},
            "caller_id": {"type": "string", "description": "Caller ID", "default": ""}
        },
        "required": ["machine_id"]
    }

    # 声明 mcp_server 字段，使其成为 Pydantic 模型的一部分
    mcp_server: Optional[Any] = None

    def __init__(self, mcp_server=None, **kwargs):
        super().__init__(mcp_server=mcp_server, **kwargs)

    async def execute(self, machine_id: str, callback_url: str = "",
                     caller_id: str = "", **kwargs) -> ToolResult:
        try:
            if not self.mcp_server:
                return ToolResult(error="MCP server not available")

            # 检查机器人是否存在于世界中
            machine_info = world_manager.get_machine_info(machine_id)
            if not machine_info:
                return ToolResult(error=f"Error: Machine {machine_id} not found in world registry")

            # 确保有调用者ID
            if not caller_id:
                return ToolResult(error="Error: caller_id is required for machine registration")

            # 初始化human的机器人集合（如果不存在）
            if caller_id not in self.mcp_server.machine_agents:
                self.mcp_server.machine_agents[caller_id] = {}

            # 如果Machine Agent不存在，创建它
            if machine_id not in self.mcp_server.machine_agents[caller_id]:
                machine_agent = await self.mcp_server._create_machine_agent(machine_id)
                self.mcp_server.machine_agents[caller_id][machine_id] = machine_agent
                return ToolResult(output=f"Machine {machine_id} control registered successfully for {caller_id} (Agent created)")
            else:
                return ToolResult(output=f"Machine {machine_id} control already registered for {caller_id}")

        except Exception as e:
            error_msg = f"Error registering machine control: {str(e)}"
            return ToolResult(error=error_msg)


class HumanGetMachineInfoTool(BaseTool):
    """获取机器人信息（Human专用）"""

    name: str = "human_get_machine_info"
    description: str = "Get information about a specific machine"
    parameters: dict = {
        "type": "object",
        "properties": {
            "machine_id": {"type": "string", "description": "Machine identifier"}
        },
        "required": ["machine_id"]
    }

    async def execute(self, machine_id: str, **kwargs) -> ToolResult:
        try:
            info = world_manager.get_machine_info(machine_id)
            if info:
                result = {
                    "machine_id": info.machine_id,
                    "position": list(info.position.coordinates),
                    "life_value": info.life_value,
                    "machine_type": info.machine_type,
                    "owner": info.owner,
                    "status": info.status,
                    "last_action": info.last_action,
                    "size": info.size,
                    "facing_direction": list(info.facing_direction)
                }
                return ToolResult(output=json.dumps(result))
            else:
                return ToolResult(error=f"Error: Machine {machine_id} not found")
        except Exception as e:
            return ToolResult(error=f"Error getting machine info: {str(e)}")


class HumanGetAllMachinesTool(BaseTool):
    """获取所有机器人信息（Human专用）"""

    name: str = "human_get_all_machines"
    description: str = "Get information about all machines in the world"
    parameters: dict = {
        "type": "object",
        "properties": {},
        "required": []
    }

    async def execute(self, **kwargs) -> ToolResult:
        try:
            machines = world_manager.get_all_machines()
            result = {}
            for machine_id, info in machines.items():
                result[machine_id] = {
                    "machine_id": info.machine_id,
                    "position": list(info.position.coordinates),
                    "life_value": info.life_value,
                    "machine_type": info.machine_type,
                    "owner": info.owner,
                    "status": info.status,
                    "last_action": info.last_action,
                    "size": info.size,
                    "facing_direction": list(info.facing_direction)
                }
            return ToolResult(output=json.dumps(result))
        except Exception as e:
            return ToolResult(error=f"Error getting all machines: {str(e)}")


class UpdateMachinePositionWorldTool(BaseTool):
    """更新机器人位置"""

    name: str = "update_machine_position"
    description: str = "Update a machine's position with collision detection"
    parameters: dict = {
        "type": "object",
        "properties": {
            "machine_id": {"type": "string", "description": "Machine identifier"},
            "new_position": {"type": "array", "items": {"type": "number"}, "description": "New position coordinates [x, y, z]"}
        },
        "required": ["machine_id", "new_position"]
    }

    async def execute(self, machine_id: str, new_position: list, **kwargs) -> ToolResult:
        try:
            pos = Position(*new_position)
            success, collision_details = world_manager.update_machine_position_with_details(machine_id, pos)
            if success:
                return ToolResult(output=f"Machine {machine_id} position updated to {pos}")
            else:
                if collision_details:
                    details = "; ".join(collision_details)
                    return ToolResult(error=f"Error: Movement blocked for machine {machine_id}. 碰撞检测: {details}")
                else:
                    return ToolResult(error=f"Error: Failed to update position for machine {machine_id}")
        except Exception as e:
            return ToolResult(error=f"Error updating machine position: {str(e)}")


class UpdateMachineLifeWorldTool(BaseTool):
    """更新机器人生命值"""

    name: str = "update_machine_life"
    description: str = "Update a machine's life value"
    parameters: dict = {
        "type": "object",
        "properties": {
            "machine_id": {"type": "string", "description": "Machine identifier"},
            "life_change": {"type": "integer", "description": "Change in life value (positive or negative)"}
        },
        "required": ["machine_id", "life_change"]
    }

    async def execute(self, machine_id: str, life_change: int, **kwargs) -> ToolResult:
        try:
            success = world_manager.update_machine_life(machine_id, life_change)
            if success:
                info = world_manager.get_machine_info(machine_id)
                return ToolResult(output=f"Machine {machine_id} life updated. Current life: {info.life_value if info else 'unknown'}")
            else:
                return ToolResult(error=f"Error: Failed to update life for machine {machine_id}")
        except Exception as e:
            return ToolResult(error=f"Error updating machine life: {str(e)}")


class UpdateMachineActionWorldTool(BaseTool):
    """更新机器人动作"""

    name: str = "update_machine_action"
    description: str = "Update a machine's last action"
    parameters: dict = {
        "type": "object",
        "properties": {
            "machine_id": {"type": "string", "description": "Machine identifier"},
            "action": {"type": "string", "description": "Action description to record"}
        },
        "required": ["machine_id", "action"]
    }

    async def execute(self, machine_id: str, action: str, **kwargs) -> ToolResult:
        try:
            success = world_manager.update_machine_action(machine_id, action)
            if success:
                return ToolResult(output=f"Machine {machine_id} action updated: {action}")
            else:
                return ToolResult(error=f"Error: Failed to update action for machine {machine_id}")
        except Exception as e:
            return ToolResult(error=f"Error updating machine action: {str(e)}")


class RemoveMachineWorldTool(BaseTool):
    """从世界中移除机器人"""

    name: str = "remove_machine"
    description: str = "Remove a machine from the world"
    parameters: dict = {
        "type": "object",
        "properties": {
            "machine_id": {"type": "string", "description": "Machine identifier to remove"}
        },
        "required": ["machine_id"]
    }

    async def execute(self, machine_id: str, **kwargs) -> ToolResult:
        try:
            success = world_manager.remove_machine(machine_id)
            if success:
                return ToolResult(output=f"Machine {machine_id} removed from world")
            else:
                return ToolResult(error=f"Error: Machine {machine_id} not found")
        except Exception as e:
            return ToolResult(error=f"Error removing machine: {str(e)}")


class GetNearbyMachinesWorldTool(BaseTool):
    """获取附近的机器人"""

    name: str = "get_nearby_machines_world"
    description: str = "Get machines within a certain radius of the specified machine"
    parameters: dict = {
        "type": "object",
        "properties": {
            "machine_id": {"type": "string", "description": "Machine identifier to search around"},
            "radius": {"type": "number", "description": "Search radius", "default": 10.0}
        },
        "required": ["machine_id"]
    }

    async def execute(self, machine_id: str, radius: float = 10.0, **kwargs) -> ToolResult:
        try:
            nearby = world_manager.get_nearby_machines(machine_id, radius)
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
            return ToolResult(output=json.dumps(result))
        except Exception as e:
            return ToolResult(error=f"Error getting nearby machines: {str(e)}")


class CheckCollisionTool(BaseTool):
    """检查碰撞"""

    name: str = "check_collision"
    description: str = "Check if a position would collide with obstacles or machines"
    agent_type: Optional[str] = None
    parameters: dict = {
        "type": "object",
        "properties": {
            "position": {"type": "array", "items": {"type": "number"}, "minItems": 3, "maxItems": 3, "description": "Position to check [x, y, z]"},
            "size": {"type": "number", "description": "Size of the object", "default": 1.0},
            "exclude_machine_id": {"type": "string", "description": "Machine ID to exclude from check", "default": None}
        },
        "required": ["position"]
    }

    async def execute(self, position: list, size: float = 1.0,
                     exclude_machine_id: Optional[str] = None, **kwargs) -> ToolResult:
        try:
            pos = Position(*position)
            collision = world_manager.check_collision(pos, size, exclude_machine_id)
            collision_details = world_manager.find_collision_details(pos, size, exclude_machine_id)

            result = {
                "collision": collision,
                "details": collision_details
            }
            return ToolResult(output=json.dumps(result))
        except Exception as e:
            return ToolResult(error=f"Error checking collision: {str(e)}")


class AddObstacleTool(BaseTool):
    """添加障碍物"""

    name: str = "add_obstacle"
    description: str = "Add a new obstacle to the world"
    parameters: dict = {
        "type": "object",
        "properties": {
            "obstacle_id": {"type": "string", "description": "Unique identifier for the obstacle"},
            "position": {"type": "array", "items": {"type": "number"}, "description": "Position coordinates [x, y, z]"},
            "size": {"type": "number", "description": "Obstacle size", "default": 1.0},
            "obstacle_type": {"type": "string", "description": "Type of obstacle", "default": "static"}
        },
        "required": ["obstacle_id", "position"]
    }

    async def execute(self, obstacle_id: str, position: list, size: float = 1.0,
                     obstacle_type: str = "static", **kwargs) -> ToolResult:
        try:
            pos = Position(*position)
            success = world_manager.add_obstacle(
                obstacle_id=obstacle_id,
                position=pos,
                size=size,
                obstacle_type=obstacle_type
            )
            if success:
                return ToolResult(output=f"Obstacle {obstacle_id} added successfully at position {pos} with size {size}")
            else:
                return ToolResult(error=f"Error: Failed to add obstacle {obstacle_id} (collision or already exists)")
        except Exception as e:
            return ToolResult(error=f"Error adding obstacle: {str(e)}")


class RemoveObstacleTool(BaseTool):
    """移除障碍物"""

    name: str = "remove_obstacle"
    description: str = "Remove an obstacle from the world"
    parameters: dict = {
        "type": "object",
        "properties": {
            "obstacle_id": {"type": "string", "description": "Obstacle identifier to remove"}
        },
        "required": ["obstacle_id"]
    }

    async def execute(self, obstacle_id: str, **kwargs) -> ToolResult:
        try:
            success = world_manager.remove_obstacle(obstacle_id)
            if success:
                return ToolResult(output=f"Obstacle {obstacle_id} removed successfully")
            else:
                return ToolResult(error=f"Error: Obstacle {obstacle_id} not found")
        except Exception as e:
            return ToolResult(error=f"Error removing obstacle: {str(e)}")


class GetObstacleInfoTool(BaseTool):
    """获取障碍物信息"""

    name: str = "get_obstacle_info"
    description: str = "Get information about a specific obstacle"
    parameters: dict = {
        "type": "object",
        "properties": {
            "obstacle_id": {"type": "string", "description": "Obstacle identifier"}
        },
        "required": ["obstacle_id"]
    }

    async def execute(self, obstacle_id: str, **kwargs) -> ToolResult:
        try:
            obstacle = world_manager.get_obstacle(obstacle_id)
            if obstacle:
                result = {
                    "obstacle_id": obstacle.obstacle_id,
                    "position": list(obstacle.position.coordinates),
                    "size": obstacle.size,
                    "obstacle_type": obstacle.obstacle_type
                }
                return ToolResult(output=json.dumps(result))
            else:
                return ToolResult(error=f"Error: Obstacle {obstacle_id} not found")
        except Exception as e:
            return ToolResult(error=f"Error getting obstacle info: {str(e)}")


class GetAllObstaclesTool(BaseTool):
    """获取所有障碍物信息"""

    name: str = "get_all_obstacles"
    description: str = "Get information about all obstacles in the world"
    parameters: dict = {
        "type": "object",
        "properties": {},
        "required": []
    }

    async def execute(self, **kwargs) -> ToolResult:
        try:
            obstacles = world_manager.get_all_obstacles()
            result = {}
            for obstacle_id, obstacle in obstacles.items():
                result[obstacle_id] = {
                    "obstacle_id": obstacle.obstacle_id,
                    "position": list(obstacle.position.coordinates),
                    "size": obstacle.size,
                    "obstacle_type": obstacle.obstacle_type
                }
            return ToolResult(output=json.dumps(result))
        except Exception as e:
            return ToolResult(error=f"Error getting all obstacles: {str(e)}")


class ClearAllObstaclesTool(BaseTool):
    """清除所有障碍物"""

    name: str = "clear_all_obstacles"
    description: str = "Remove all obstacles from the world"
    parameters: dict = {
        "type": "object",
        "properties": {},
        "required": []
    }

    async def execute(self, **kwargs) -> ToolResult:
        try:
            world_manager.clear_all_obstacles()
            return ToolResult(output="All obstacles removed successfully")
        except Exception as e:
            return ToolResult(error=f"Error clearing obstacles: {str(e)}")
