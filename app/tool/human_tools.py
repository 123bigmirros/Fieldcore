"""
Tools specific to Human agents for controlling and coordinating machines.
"""

import asyncio
import json
from typing import Any, Dict, List, Optional

from app.agent.world_manager import world_manager
from app.tool.base import BaseTool, ToolResult


class ControlMachineTool(BaseTool):
    """Tool for controlling machines through text commands."""

    name: str = "control_machine"
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
        },
        "required": ["machine_id", "command"],
    }

    def __init__(self, machine_registry: Optional[Dict[str, Any]] = None):
        super().__init__()
        # Registry of machine agents that can be controlled
        object.__setattr__(self, '_machine_registry', machine_registry or {})

    @property
    def machine_registry(self) -> Dict[str, Any]:
        """Get the machine registry."""
        return getattr(self, '_machine_registry', {})

    def register_machine_agent(self, machine_id: str, machine_agent: Any) -> None:
        """Register a machine agent for control."""
        registry = getattr(self, '_machine_registry', {})
        registry[machine_id] = machine_agent
        object.__setattr__(self, '_machine_registry', registry)

    def unregister_machine_agent(self, machine_id: str) -> None:
        """Unregister a machine agent."""
        registry = getattr(self, '_machine_registry', {})
        if machine_id in registry:
            del registry[machine_id]
            object.__setattr__(self, '_machine_registry', registry)

    async def execute(self, machine_id: str, command: str, **kwargs) -> ToolResult:
        """Execute machine control command."""
        try:
            # Check if machine exists in world
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

            # Check if we have a registered agent for this machine
            registry = getattr(self, '_machine_registry', {})
            if machine_id in registry:
                # Direct agent control
                machine_agent = registry[machine_id]
                result = await self._control_via_agent(machine_agent, command)
            else:
                # Simulated control - interpret common commands
                result = await self._simulate_control(machine_id, command)

            return ToolResult(output=result)

        except Exception as e:
            return ToolResult(error=f"Machine control failed: {str(e)}")

    async def _control_via_agent(self, machine_agent: Any, command: str) -> str:
        """Control machine via its agent."""
        try:
            # Create command prompt for the machine agent
            full_command = f"Execute: {command}"

            # Run the machine agent
            result = await machine_agent.run(full_command)

            return f"Machine executed command successfully: {result}"

        except Exception as e:
            return f"Machine control error: {str(e)}"

    async def _simulate_control(self, machine_id: str, command: str) -> str:
        """Simulate machine control by interpreting common commands."""
        command_lower = command.lower().strip()

        # Parse common movement commands
        if command_lower.startswith("move") or command_lower.startswith("go"):
            return await self._simulate_movement(machine_id, command)

        # Parse action commands
        elif command_lower.startswith("action") or command_lower.startswith("do"):
            return await self._simulate_action(machine_id, command)

        # Parse environment check commands
        elif command_lower.startswith("check") or command_lower.startswith("scan"):
            return await self._simulate_environment_check(machine_id, command)

        # Default simulation
        else:
            world_manager.update_machine_action(machine_id, f"simulated_{command}")
            return f"Machine {machine_id} simulated command: {command}"

    async def _simulate_movement(self, machine_id: str, command: str) -> str:
        """Simulate movement command."""
        # Try to extract coordinates from command text
        import re
        coords_match = re.search(r'(\d+(?:\.\d+)?)[,\s]+(\d+(?:\.\d+)?)[,\s]*(\d+(?:\.\d+)?)?', command)
        if coords_match:
            coordinates = [float(coords_match.group(1)), float(coords_match.group(2))]
            if coords_match.group(3):
                coordinates.append(float(coords_match.group(3)))
        else:
            return f"Could not parse coordinates from command: {command}"

        # Get current position
        machine_info = world_manager.get_machine_info(machine_id)
        if not machine_info:
            return f"Machine {machine_id} not found"

        # Determine if relative movement
        relative = "relative" in command.lower() or "by" in command.lower()

        # Calculate new position
        if relative:
            new_coords = tuple(
                current + delta
                for current, delta in zip(machine_info.position.coordinates, coordinates)
            )
        else:
            new_coords = tuple(coordinates)

        from app.agent.world_manager import Position
        new_position = Position(*new_coords)

        # Update position
        success = world_manager.update_machine_position(machine_id, new_position)
        if success:
            world_manager.update_machine_action(machine_id, f"moved_to_{new_position}")
            return f"Machine {machine_id} moved to {new_position}"
        else:
            return f"Movement failed for machine {machine_id}"

    async def _simulate_action(self, machine_id: str, command: str) -> str:
        """Simulate action command."""
        # Extract action type from command
        action_type = "generic_action"
        if "build" in command.lower():
            action_type = "build"
        elif "collect" in command.lower():
            action_type = "collect"
        elif "scout" in command.lower():
            action_type = "scout"
        elif "repair" in command.lower():
            action_type = "repair"
        elif "work" in command.lower():
            action_type = "work"

        # Update action in world manager
        world_manager.update_machine_action(machine_id, f"simulated_{action_type}")

        # Get machine info for logging
        machine_info = world_manager.get_machine_info(machine_id)
        action_log = {
            "machine_id": machine_id,
            "machine_type": machine_info.machine_type,
            "position": str(machine_info.position),
            "action": action_type,
            "command": command,
        }

        print(f"[HUMAN CONTROLLED ACTION] {json.dumps(action_log, ensure_ascii=False)}")

        return f"Machine {machine_id} performed action: {action_type}"

    async def _simulate_environment_check(self, machine_id: str, command: str) -> str:
        """Simulate environment check command."""
        # Extract radius from command, default to 10.0
        radius = 10.0
        import re
        radius_match = re.search(r'radius[:\s]+(\d+(?:\.\d+)?)', command.lower())
        if radius_match:
            radius = float(radius_match.group(1))

        # Get machine info
        machine_info = world_manager.get_machine_info(machine_id)
        if not machine_info:
            return f"Machine {machine_id} not found"

        # Get nearby machines
        nearby_machines = world_manager.get_nearby_machines(machine_id, radius)

        # Build report
        report = f"Machine {machine_id} environment scan:\n"
        report += f"Position: {machine_info.position}\n"
        report += f"Life: {machine_info.life_value}\n"
        report += f"Status: {machine_info.status}\n"
        report += f"Nearby machines ({len(nearby_machines)}):\n"

        for machine in nearby_machines:
            distance = machine_info.position.distance_to(machine.position)
            report += f"  - {machine.machine_id}: {machine.position} (distance: {distance:.2f})\n"

        world_manager.update_machine_action(machine_id, f"environment_check_radius_{radius}")

        return report


class GetMachineStatusTool(BaseTool):
    """Tool for getting status of controlled machines."""

    name: str = "get_machine_status"
    description: str = "Get status information of controlled machines."
    parameters: dict = {
        "type": "object",
        "properties": {
            "machine_id": {
                "type": "string",
                "description": "The ID of the specific machine to check (optional, if not provided, returns all machines)",
                "default": None,
            },
        },
        "required": [],
    }

    def __init__(self, human_agent: Optional[Any] = None):
        super().__init__()
        object.__setattr__(self, '_human_agent', human_agent)

    async def execute(self, machine_id: Optional[str] = None, **kwargs) -> ToolResult:
        """Execute machine status check."""
        try:
            if machine_id:
                # Get specific machine status
                machine_info = world_manager.get_machine_info(machine_id)
                if machine_info:
                    status_data = {
                        "machine_id": machine_id,
                        "position": str(machine_info.position),
                        "life_value": machine_info.life_value,
                        "machine_type": machine_info.machine_type,
                        "status": machine_info.status,
                        "last_action": machine_info.last_action,
                    }
                    return ToolResult(output=json.dumps(status_data, indent=2, ensure_ascii=False))
                else:
                    return ToolResult(error=f"Machine {machine_id} not found")
            else:
                # Get all machines status
                all_machines = world_manager.get_all_machines()
                status_data = {
                    "total_machines": len(all_machines),
                    "machines": [
                        {
                            "machine_id": m.machine_id,
                            "position": str(m.position),
                            "life_value": m.life_value,
                            "machine_type": m.machine_type,
                            "status": m.status,
                            "last_action": m.last_action,
                        }
                        for m in all_machines.values()
                    ]
                }
                return ToolResult(output=json.dumps(status_data, indent=2, ensure_ascii=False))

        except Exception as e:
            return ToolResult(error=f"Status check failed: {str(e)}")





class PlanTaskTool(BaseTool):
    """Tool for decomposing and planning complex tasks."""

    name: str = "plan_task"
    description: str = "Decompose a complex task into subtasks and assign them to appropriate machines."
    parameters: dict = {
        "type": "object",
        "properties": {
            "task_description": {
                "type": "string",
                "description": "Description of the task to be planned and executed",
            },
        },
        "required": ["task_description"],
    }

    def __init__(self, human_agent: Optional[Any] = None):
        super().__init__()
        object.__setattr__(self, '_human_agent', human_agent)

    async def execute(self, task_description: str, **kwargs) -> ToolResult:
        """Execute task planning."""
        try:
            # Simple task planning without human agent
            # Analyze task and suggest machine assignments
            all_machines = world_manager.get_all_machines()
            active_machines = [m for m in all_machines.values() if m.status == "active"]

            # Basic task decomposition
            subtasks = self._decompose_task(task_description)

            # Simple assignment algorithm
            assignments = self._assign_tasks(subtasks, active_machines)

            plan_data = {
                "task_description": task_description,
                "subtasks": subtasks,
                "assignments": assignments,
                "available_machines": len(active_machines),
                "ready_to_execute": True
            }

            return ToolResult(output=json.dumps(plan_data, indent=2, ensure_ascii=False))

        except Exception as e:
            return ToolResult(error=f"Task planning failed: {str(e)}")

    def _decompose_task(self, task_description: str) -> List[str]:
        """Simple task decomposition."""
        # Basic keyword-based decomposition
        subtasks = []

        if "move" in task_description.lower():
            subtasks.append("movement_task")
        if "build" in task_description.lower():
            subtasks.append("construction_task")
        if "collect" in task_description.lower():
            subtasks.append("collection_task")
        if "scout" in task_description.lower() or "explore" in task_description.lower():
            subtasks.append("exploration_task")
        if "repair" in task_description.lower():
            subtasks.append("maintenance_task")

        # If no specific keywords found, create a generic task
        if not subtasks:
            subtasks.append("generic_task")

        return subtasks

    def _assign_tasks(self, subtasks: List[str], machines: List[Any]) -> List[Dict[str, Any]]:
        """Simple task assignment algorithm."""
        assignments = []

        for i, subtask in enumerate(subtasks):
            if machines:
                # Round-robin assignment
                machine = machines[i % len(machines)]
                assignments.append({
                    "subtask": subtask,
                    "assigned_machine": machine.machine_id,
                    "machine_position": str(machine.position),
                    "machine_type": machine.machine_type,
                    "machine_status": machine.status
                })
            else:
                assignments.append({
                    "subtask": subtask,
                    "assigned_machine": None,
                    "error": "No active machines available"
                })

        return assignments
