"""
Tools specific to Machine agents for environment interaction and movement.
"""

import json
from typing import Any, Dict, List, Optional

from app.agent.world_manager import Position, world_manager
from app.tool.base import BaseTool, ToolResult


class CheckEnvironmentTool(BaseTool):
    """Tool for checking the surrounding environment and nearby machines."""

    name: str = "check_environment"
    description: str = "Check the surrounding environment to get information about nearby machines and their positions."
    parameters: dict = {
        "type": "object",
        "properties": {
            "machine_id": {
                "type": "string",
                "description": "The ID of the machine checking the environment",
            },
            "radius": {
                "type": "number",
                "description": "The radius to check for nearby machines (default: 10.0)",
                "default": 10.0,
            },
        },
        "required": ["machine_id"],
    }

    async def execute(self, machine_id: str, radius: float = 10.0, **kwargs) -> ToolResult:
        """Execute environment check."""
        try:
            # Get machine info
            machine_info = world_manager.get_machine_info(machine_id)
            if not machine_info:
                return ToolResult(
                    error=f"Machine {machine_id} not found in world registry"
                )

            # Get nearby machines
            nearby_machines = world_manager.get_nearby_machines(machine_id, radius)

            # Build environment report
            environment_data = {
                "machine_id": machine_id,
                "current_position": str(machine_info.position),
                "life_value": machine_info.life_value,
                "status": machine_info.status,
                "nearby_machines": [
                    {
                        "id": m.machine_id,
                        "position": str(m.position),
                        "distance": machine_info.position.distance_to(m.position),
                        "life_value": m.life_value,
                        "type": m.machine_type,
                        "status": m.status,
                        "last_action": m.last_action,
                    }
                    for m in nearby_machines
                ],
                "scan_radius": radius,
            }

            return ToolResult(
                output=json.dumps(environment_data, indent=2, ensure_ascii=False)
            )

        except Exception as e:
            return ToolResult(error=f"Environment check failed: {str(e)}")


class MovementTool(BaseTool):
    """Tool for controlling machine movement in multi-dimensional space."""

    name: str = "movement"
    description: str = "Move the machine to a new position in multi-dimensional space. Each move is limited to 1 unit (enforced externally)."
    parameters: dict = {
        "type": "object",
        "properties": {
            "machine_id": {
                "type": "string",
                "description": "The ID of the machine to move",
            },
            "coordinates": {
                "type": "array",
                "description": "Array of coordinates for the new position (e.g., [x, y, z])",
                "items": {"type": "number"},
            },
            "relative": {
                "type": "boolean",
                "description": "Whether the coordinates are relative to current position (default: false)",
                "default": False,
            },
        },
        "required": ["machine_id", "coordinates"],
    }

    async def execute(self, machine_id: str, coordinates: List[float],
                     relative: bool = False, **kwargs) -> ToolResult:
        """Execute movement, no distance check, just move."""
        try:
            machine_info = world_manager.get_machine_info(machine_id)
            if not machine_info:
                return ToolResult(error=f"Machine {machine_id} not found in world registry")
            if machine_info.status != "active":
                return ToolResult(error=f"Machine {machine_id} is not active (status: {machine_info.status})")

            if relative:
                new_coords = tuple(current + delta for current, delta in zip(machine_info.position.coordinates, coordinates))
            else:
                new_coords = tuple(coordinates)

            new_position = Position(*new_coords)
            success = world_manager.update_machine_position(machine_id, new_position)
            if not success:
                return ToolResult(error=f"Movement failed. Position {new_position} may be out of bounds")
            world_manager.update_machine_action(machine_id, f"moved_to_{new_position}")
            return ToolResult(output=f"Machine {machine_id} moved to {new_position}")
        except Exception as e:
            return ToolResult(error=f"Movement failed: {str(e)}")


class MachineActionTool(BaseTool):
    """Tool for performing machine-specific actions."""

    name: str = "machine_action"
    description: str = "Perform a machine-specific action. Default implementation prints the action."
    parameters: dict = {
        "type": "object",
        "properties": {
            "machine_id": {
                "type": "string",
                "description": "The ID of the machine performing the action",
            },
            "action_type": {
                "type": "string",
                "description": "The type of action to perform",
            },
            "parameters": {
                "type": "object",
                "description": "Additional parameters for the action",
                "default": {},
            },
        },
        "required": ["machine_id", "action_type"],
    }

    async def execute(self, machine_id: str, action_type: str,
                     parameters: Optional[Dict[str, Any]] = None, **kwargs) -> ToolResult:
        """Execute machine action."""
        try:
            # Get machine info
            machine_info = world_manager.get_machine_info(machine_id)
            if not machine_info:
                return ToolResult(
                    error=f"Machine {machine_id} not found in world registry"
                )

            # Check if machine is active
            if machine_info.status != "active":
                return ToolResult(
                    error=f"Machine {machine_id} is not active (status: {machine_info.status})"
                )

            parameters = parameters or {}

            # Default action implementation - can be overridden in subclasses
            action_result = await self._perform_action(machine_id, action_type, parameters)

            # Update last action
            action_description = f"{action_type}_{json.dumps(parameters)}"
            world_manager.update_machine_action(machine_id, action_description)

            return ToolResult(output=action_result)

        except Exception as e:
            return ToolResult(error=f"Action failed: {str(e)}")

    async def _perform_action(self, machine_id: str, action_type: str,
                            parameters: Dict[str, Any]) -> str:
        """Default action implementation - prints the action."""
        machine_info = world_manager.get_machine_info(machine_id)

        action_log = {
            "machine_id": machine_id,
            "machine_type": machine_info.machine_type,
            "position": str(machine_info.position),
            "action_type": action_type,
            "parameters": parameters,
            "timestamp": "now",  # In real implementation, use actual timestamp
        }

        print(f"[MACHINE ACTION] {json.dumps(action_log, ensure_ascii=False)}")

        return f"Machine {machine_id} performed action '{action_type}' with parameters {parameters}"
