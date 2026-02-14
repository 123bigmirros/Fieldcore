# -*- coding: utf-8 -*-
"""Machine Tools — robot tools that call the World Server via HTTP."""

import json
from typing import List

from app.service.world_client import world_client
from app.tool.base import BaseTool, ToolResult


class CheckEnvironmentTool(BaseTool):
    """Environment check tool."""

    name: str = "machine_check_environment"
    description: str = "Check surroundings and get field-of-view information"
    parameters: dict = {
        "type": "object",
        "properties": {
            "machine_id": {
                "type": "string",
                "description": "Machine ID",
            },
        },
        "required": ["machine_id"],
    }

    async def execute(self, machine_id: str, **kwargs) -> ToolResult:
        """Get machine field-of-view."""
        try:
            view = world_client.get_machine_view(machine_id)
            if not view:
                return ToolResult(error=f"Machine {machine_id} not found")
            return ToolResult(output=json.dumps(view, indent=2, ensure_ascii=False))
        except Exception as e:
            return ToolResult(error=f"Environment check failed: {str(e)}")


class StepMovementTool(BaseTool):
    """Movement tool."""

    name: str = "machine_step_movement"
    description: str = "Move a machine. Directions: East[1,0,0], North[0,1,0], West[-1,0,0], South[0,-1,0]"
    parameters: dict = {
        "type": "object",
        "properties": {
            "machine_id": {"type": "string", "description": "Machine ID"},
            "direction": {"type": "array", "items": {"type": "number"}, "description": "Direction vector"},
            "distance": {"type": "number", "description": "Movement distance"},
        },
        "required": ["machine_id", "direction", "distance"],
    }

    async def execute(self, machine_id: str, direction: List[float], distance: float, **kwargs) -> ToolResult:
        """Execute movement."""
        try:
            result = world_client.move(machine_id, direction, distance)
            if result.get("success"):
                return ToolResult(output=json.dumps(result["result"], ensure_ascii=False))
            return ToolResult(error=result.get("error", "Move failed"))
        except Exception as e:
            return ToolResult(error=f"Movement failed: {str(e)}")


class LaserAttackTool(BaseTool):
    """Laser attack tool."""

    name: str = "machine_laser_attack"
    description: str = "Fire a laser attack along the current facing direction"
    parameters: dict = {
        "type": "object",
        "properties": {
            "machine_id": {"type": "string", "description": "Machine ID"},
            "damage": {"type": "number", "description": "Damage value", "default": 1},
        },
        "required": ["machine_id"],
    }

    async def execute(self, machine_id: str, damage: int = 1, **kwargs) -> ToolResult:
        """Execute attack."""
        try:
            result = world_client.attack(machine_id, damage)
            if result.get("success"):
                return ToolResult(output=json.dumps(result["result"], indent=2, ensure_ascii=False))
            return ToolResult(error=result.get("error", "Attack failed"))
        except Exception as e:
            return ToolResult(error=f"Attack failed: {str(e)}")


class GetSelfStatusTool(BaseTool):
    """Get self status tool."""

    name: str = "machine_get_self_status"
    description: str = "Get the machine's own status"
    parameters: dict = {
        "type": "object",
        "properties": {
            "machine_id": {"type": "string", "description": "Machine ID"},
        },
        "required": ["machine_id"],
    }

    async def execute(self, machine_id: str, **kwargs) -> ToolResult:
        """Get status."""
        try:
            machine = world_client.get_machine(machine_id)
            if not machine:
                return ToolResult(error=f"Machine {machine_id} not found")
            return ToolResult(output=json.dumps(machine, indent=2, ensure_ascii=False))
        except Exception as e:
            return ToolResult(error=f"Failed to get status: {str(e)}")


class GrabResourceTool(BaseTool):
    """Grab resource tool."""

    name: str = "machine_grab_resource"
    description: str = "Grab a resource from an adjacent cell. Direction: top(N), bottom(S), left(W), right(E)"
    parameters: dict = {
        "type": "object",
        "properties": {
            "machine_id": {"type": "string", "description": "Machine ID"},
            "direction": {"type": "string", "enum": ["top", "bottom", "left", "right"], "description": "Grab direction"},
        },
        "required": ["machine_id", "direction"],
    }

    async def execute(self, machine_id: str, direction: str, **kwargs) -> ToolResult:
        """Execute grab."""
        try:
            result = world_client.grab(machine_id, direction)
            if result.get("success"):
                return ToolResult(output=json.dumps(result.get("result", result), ensure_ascii=False))
            return ToolResult(error=result.get("error", "Grab failed"))
        except Exception as e:
            return ToolResult(error=f"Grab failed: {str(e)}")


class DropResourceTool(BaseTool):
    """Drop resource tool."""

    name: str = "machine_drop_resource"
    description: str = "Drop a carried resource to an adjacent cell. Direction: top(N), bottom(S), left(W), right(E)"
    parameters: dict = {
        "type": "object",
        "properties": {
            "machine_id": {"type": "string", "description": "Machine ID"},
            "direction": {"type": "string", "enum": ["top", "bottom", "left", "right"], "description": "Drop direction"},
        },
        "required": ["machine_id", "direction"],
    }

    async def execute(self, machine_id: str, direction: str, **kwargs) -> ToolResult:
        """Execute drop."""
        try:
            result = world_client.drop(machine_id, direction)
            if result.get("success"):
                return ToolResult(output=json.dumps(result.get("result", result), ensure_ascii=False))
            return ToolResult(error=result.get("error", "Drop failed"))
        except Exception as e:
            return ToolResult(error=f"Drop failed: {str(e)}")
