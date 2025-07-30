"""
World state management tools for MCP server.
"""

import json
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.tool.base import BaseTool


class RegisterMachineTool(BaseTool):
    """Tool to register a new machine in the world."""

    name: str = "register_machine"
    description: str = "Register a new machine in the world"
    parameters: dict = {
        "type": "object",
        "properties": {
            "machine_id": {"type": "string", "description": "Unique identifier for the machine"},
            "position": {"type": "array", "items": {"type": "number"}, "description": "Position coordinates [x, y, z]"},
            "life_value": {"type": "integer", "description": "Initial life value", "default": 10},
            "machine_type": {"type": "string", "description": "Type of machine", "default": "generic"}
        },
        "required": ["machine_id", "position"]
    }

    class RegisterMachineRequest(BaseModel):
        machine_id: str = Field(description="Unique identifier for the machine")
        position: List[float] = Field(description="Position coordinates [x, y, z]")
        life_value: int = Field(default=10, description="Initial life value")
        machine_type: str = Field(default="generic", description="Type of machine")

    async def execute(self, **kwargs) -> str:
        """Execute the register machine tool."""
        from app.agent.world_manager import Position, world_manager

        try:
            request = self.RegisterMachineRequest(**kwargs)
            pos = Position(*request.position)
            world_manager.register_machine(
                machine_id=request.machine_id,
                position=pos,
                life_value=request.life_value,
                machine_type=request.machine_type
            )
            return f"Machine {request.machine_id} registered successfully at position {pos}"
        except Exception as e:
            return f"Error registering machine: {str(e)}"


class GetMachineInfoTool(BaseTool):
    """Tool to get information about a specific machine."""

    name: str = "get_machine_info"
    description: str = "Get information about a specific machine"
    parameters: dict = {
        "type": "object",
        "properties": {
            "machine_id": {"type": "string", "description": "Machine identifier to query"}
        },
        "required": ["machine_id"]
    }

    class GetMachineInfoRequest(BaseModel):
        machine_id: str = Field(description="Machine identifier to query")

    async def execute(self, **kwargs) -> str:
        """Execute the get machine info tool."""
        from app.agent.world_manager import world_manager

        try:
            request = self.GetMachineInfoRequest(**kwargs)
            info = world_manager.get_machine_info(request.machine_id)
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
                return f"Error: Machine {request.machine_id} not found"
        except Exception as e:
            return f"Error getting machine info: {str(e)}"


class GetAllMachinesTool(BaseTool):
    """Tool to get information about all machines in the world."""

    name: str = "get_all_machines"
    description: str = "Get information about all machines in the world"
    parameters: dict = {
        "type": "object",
        "properties": {},
        "required": []
    }

    class GetAllMachinesRequest(BaseModel):
        pass  # No parameters needed

    async def execute(self, **kwargs) -> str:
        """Execute the get all machines tool."""
        from app.agent.world_manager import world_manager

        try:
            machines = world_manager.get_all_machines()
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


class UpdateMachinePositionTool(BaseTool):
    """Tool to update a machine's position."""

    name: str = "update_machine_position"
    description: str = "Update a machine's position"
    parameters: dict = {
        "type": "object",
        "properties": {
            "machine_id": {"type": "string", "description": "Machine identifier"},
            "new_position": {"type": "array", "items": {"type": "number"}, "description": "New position coordinates [x, y, z]"}
        },
        "required": ["machine_id", "new_position"]
    }

    class UpdateMachinePositionRequest(BaseModel):
        machine_id: str = Field(description="Machine identifier")
        new_position: List[float] = Field(description="New position coordinates [x, y, z]")

    async def execute(self, **kwargs) -> str:
        """Execute the update machine position tool."""
        from app.agent.world_manager import Position, world_manager

        try:
            request = self.UpdateMachinePositionRequest(**kwargs)
            pos = Position(*request.new_position)
            success = world_manager.update_machine_position(request.machine_id, pos)
            if success:
                return f"Machine {request.machine_id} position updated to {pos}"
            else:
                return f"Error: Failed to update position for machine {request.machine_id}"
        except Exception as e:
            return f"Error updating machine position: {str(e)}"


class UpdateMachineLifeTool(BaseTool):
    """Tool to update a machine's life value."""

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

    class UpdateMachineLifeRequest(BaseModel):
        machine_id: str = Field(description="Machine identifier")
        life_change: int = Field(description="Change in life value (positive or negative)")

    async def execute(self, **kwargs) -> str:
        """Execute the update machine life tool."""
        from app.agent.world_manager import world_manager

        try:
            request = self.UpdateMachineLifeRequest(**kwargs)
            success = world_manager.update_machine_life(request.machine_id, request.life_change)
            if success:
                info = world_manager.get_machine_info(request.machine_id)
                return f"Machine {request.machine_id} life updated. Current life: {info.life_value if info else 'unknown'}"
            else:
                return f"Error: Failed to update life for machine {request.machine_id}"
        except Exception as e:
            return f"Error updating machine life: {str(e)}"


class UpdateMachineActionTool(BaseTool):
    """Tool to update a machine's last action."""

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

    class UpdateMachineActionRequest(BaseModel):
        machine_id: str = Field(description="Machine identifier")
        action: str = Field(description="Action description to record")

    async def execute(self, **kwargs) -> str:
        """Execute the update machine action tool."""
        from app.agent.world_manager import world_manager

        try:
            request = self.UpdateMachineActionRequest(**kwargs)
            success = world_manager.update_machine_action(request.machine_id, request.action)
            if success:
                return f"Machine {request.machine_id} action updated: {request.action}"
            else:
                return f"Error: Failed to update action for machine {request.machine_id}"
        except Exception as e:
            return f"Error updating machine action: {str(e)}"


class RemoveMachineTool(BaseTool):
    """Tool to remove a machine from the world."""

    name: str = "remove_machine"
    description: str = "Remove a machine from the world"
    parameters: dict = {
        "type": "object",
        "properties": {
            "machine_id": {"type": "string", "description": "Machine identifier to remove"}
        },
        "required": ["machine_id"]
    }

    class RemoveMachineRequest(BaseModel):
        machine_id: str = Field(description="Machine identifier to remove")

    async def execute(self, **kwargs) -> str:
        """Execute the remove machine tool."""
        from app.agent.world_manager import world_manager

        try:
            request = self.RemoveMachineRequest(**kwargs)
            success = world_manager.remove_machine(request.machine_id)
            if success:
                return f"Machine {request.machine_id} removed from world"
            else:
                return f"Error: Machine {request.machine_id} not found"
        except Exception as e:
            return f"Error removing machine: {str(e)}"


class GetNearbyMachinesWorldTool(BaseTool):
    """Tool to get machines within a certain radius of a specified machine."""

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

    class GetNearbyMachinesRequest(BaseModel):
        machine_id: str = Field(description="Machine identifier to search around")
        radius: float = Field(default=10.0, description="Search radius")

    async def execute(self, **kwargs) -> str:
        """Execute the get nearby machines tool."""
        from app.agent.world_manager import world_manager

        try:
            request = self.GetNearbyMachinesRequest(**kwargs)
            nearby = world_manager.get_nearby_machines(request.machine_id, request.radius)
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
