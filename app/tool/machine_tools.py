"""
Tools specific to Machine agents for environment interaction and movement.
"""

import json
import time
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
                    "description": "The radius to check for nearby machines (default: 3.0)",
                    "default": 3.0,
                },
        },
        "required": ["machine_id"],
    }

    async def execute(self, machine_id: str, radius: float = 3.0, **kwargs) -> ToolResult:
        """Execute environment check."""
        try:
            # Get machine info
            machine_info = world_manager.get_machine_info(machine_id)
            if not machine_info:
                return ToolResult(
                    error=f"Machine {machine_id} not found in world registry"
                )

            # Get nearby machines using square distance
            nearby_machines = world_manager.get_nearby_machines(machine_id, radius, use_square_distance=True)

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
                        "distance": machine_info.position.square_distance_to(m.position),
                        "life_value": m.life_value,
                        "type": m.machine_type,
                        "status": m.status,
                        "last_action": m.last_action or "none",  # 避免 None 值
                    }
                    for m in nearby_machines if m and m.position  # 过滤掉 None 对象
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
                     relative: bool = False, step_by_step: bool = False, **kwargs) -> ToolResult:
        """Execute movement with optional step-by-step collision checking."""
        try:
            machine_info = world_manager.get_machine_info(machine_id)
            if not machine_info:
                return ToolResult(error=f"Machine {machine_id} not found in world registry")
            if machine_info.status != "active":
                return ToolResult(error=f"Machine {machine_id} is not active (status: {machine_info.status})")

            if relative:
                target_coords = tuple(current + delta for current, delta in zip(machine_info.position.coordinates, coordinates))
            else:
                target_coords = tuple(coordinates)

            target_position = Position(*target_coords)

            if step_by_step:
                # 逐步移动模式
                return await self._step_by_step_movement(machine_id, machine_info.position, target_position)
            else:
                # 直接移动模式（原有逻辑）
                success = world_manager.update_machine_position(machine_id, target_position)
                if not success:
                    return ToolResult(error=f"Movement failed. Position {target_position} may be blocked")
                world_manager.update_machine_action(machine_id, f"moved_to_{target_position}")
                return ToolResult(output=f"Machine {machine_id} moved to {target_position}")
        except Exception as e:
            return ToolResult(error=f"Movement failed: {str(e)}")

    async def _step_by_step_movement(self, machine_id: str, start_pos: Position, target_pos: Position) -> ToolResult:
        """逐步移动，每单位检查碰撞"""
        current_pos = start_pos
        steps_taken = 0

        # 计算移动方向和总步数
        dx = target_pos.coordinates[0] - start_pos.coordinates[0]
        dy = target_pos.coordinates[1] - start_pos.coordinates[1]
        dz = (target_pos.coordinates[2] if len(target_pos.coordinates) > 2 else 0.0) - (start_pos.coordinates[2] if len(start_pos.coordinates) > 2 else 0.0)

                # 计算总移动距离，设置小步长确保前端能看到每一步
        total_distance = (dx**2 + dy**2 + dz**2) ** 0.5
        if total_distance == 0:
            return ToolResult(output=f"Machine {machine_id} already at target position")

        # 设置每步移动0.1单位，确保足够多的中间步骤
        step_size = 0.1
        total_steps = max(1, int(total_distance / step_size))

        # 计算每步的增量
        step_x = dx / total_steps if total_steps > 0 else 0
        step_y = dy / total_steps if total_steps > 0 else 0
        step_z = dz / total_steps if total_steps > 0 else 0

                # 逐步移动（支持中断）
        import asyncio
        for step in range(1, int(total_steps) + 1):
            # 检查是否被取消，延长等待时间确保前端能看到每一步
            try:
                await asyncio.sleep(0.6)  # 600ms每步，前端300ms刷新能看到2次更新
            except asyncio.CancelledError:
                world_manager.update_machine_action(machine_id, f"cancelled_at_{current_pos}")
                return ToolResult(output=f"Machine {machine_id} movement cancelled at {current_pos} after {steps_taken} steps")

            next_x = start_pos.coordinates[0] + step_x * step
            next_y = start_pos.coordinates[1] + step_y * step
            next_z = (start_pos.coordinates[2] if len(start_pos.coordinates) > 2 else 0.0) + step_z * step
            next_pos = Position(next_x, next_y, next_z)

            # 检查下一步是否会碰撞
            if world_manager.check_collision(next_pos, exclude_machine_id=machine_id):
                # 遇到障碍物，停止移动
                collision_details = world_manager.find_collision_details(next_pos, exclude_machine_id=machine_id)
                details_str = "; ".join(collision_details)
                world_manager.update_machine_action(machine_id, f"stopped_at_{current_pos}_due_to_collision")
                return ToolResult(output=f"Machine {machine_id} moved {steps_taken} steps to {current_pos}, stopped due to collision: {details_str}")

            # 移动到下一位置
            success = world_manager.update_machine_position(machine_id, next_pos)
            if not success:
                world_manager.update_machine_action(machine_id, f"stopped_at_{current_pos}_update_failed")
                return ToolResult(error=f"Movement failed at step {step}. Position update failed for {next_pos}")

            current_pos = next_pos
            steps_taken = step

        # 成功完成移动
        world_manager.update_machine_action(machine_id, f"moved_to_{current_pos}")
        return ToolResult(output=f"Machine {machine_id} successfully moved to {current_pos} in {steps_taken} steps")


class StepMovementTool(BaseTool):
    """Tool for step-by-step movement with collision checking."""

    name: str = "step_movement"
    description: str = "Move machine step-by-step towards target, stopping at obstacles."
    parameters: dict = {
        "type": "object",
        "properties": {
            "machine_id": {
                "type": "string",
                "description": "The ID of the machine to move",
            },
            "direction": {
                "type": "array",
                "items": {"type": "number"},
                "description": "Direction vector [x, y, z] to move (e.g., [1, 0, 0] for east)",
            },
            "distance": {
                "type": "number",
                "description": "Number of units to move in the direction",
            },
        },
        "required": ["machine_id", "direction", "distance"],
    }

    async def execute(self, machine_id: str, direction: List[float], distance: float, **kwargs) -> ToolResult:
        """Execute step-by-step movement in a specific direction."""
        try:
            machine_info = world_manager.get_machine_info(machine_id)
            if not machine_info:
                return ToolResult(error=f"Machine {machine_id} not found in world registry")
            if machine_info.status != "active":
                return ToolResult(error=f"Machine {machine_id} is not active (status: {machine_info.status})")

            # 标准化方向向量
            direction_length = sum(d**2 for d in direction) ** 0.5
            if direction_length == 0:
                return ToolResult(error="Direction vector cannot be zero")

            normalized_direction = [d / direction_length for d in direction]

            # 计算目标位置
            current_pos = machine_info.position
            target_x = current_pos.coordinates[0] + normalized_direction[0] * distance
            target_y = current_pos.coordinates[1] + normalized_direction[1] * distance
            target_z = (current_pos.coordinates[2] if len(current_pos.coordinates) > 2 else 0.0) + (normalized_direction[2] if len(normalized_direction) > 2 else 0) * distance

            target_position = Position(target_x, target_y, target_z)

            # 使用逐步移动
            movement_tool = MovementTool(name="movement", description="Movement tool")
            return await movement_tool._step_by_step_movement(machine_id, current_pos, target_position)

        except Exception as e:
            return ToolResult(error=f"Step movement failed: {str(e)}")


class MachineActionTool(BaseTool):
    """Base class for machine combat and action tools."""

    name: str = "machine_action"
    description: str = "Base class for machine actions including attacks and special abilities."

    async def execute(self, machine_id: str, **kwargs) -> ToolResult:
        """Execute machine action with pre/post checks."""
        try:
            # Pre-action validation
            validation_result = await self._validate_action(machine_id)
            if validation_result.error:
                return validation_result

            # Execute the specific action
            action_result = await self._perform_action(machine_id, **kwargs)

            # Post-action processing
            await self._post_action_processing(machine_id, action_result)

            return action_result

        except Exception as e:
            return ToolResult(error=f"Action failed: {str(e)}")

    async def _validate_action(self, machine_id: str) -> ToolResult:
        """Validate machine can perform action."""
        machine_info = world_manager.get_machine_info(machine_id)
        if not machine_info:
            return ToolResult(error=f"Machine {machine_id} not found in world registry")

        if machine_info.status != "active":
            return ToolResult(error=f"Machine {machine_id} is not active (status: {machine_info.status})")

        return ToolResult(output="validation_passed")

    async def _perform_action(self, machine_id: str, **kwargs) -> ToolResult:
        """Override this method in subclasses to implement specific actions."""
        raise NotImplementedError("Subclasses must implement _perform_action")

    async def _post_action_processing(self, machine_id: str, action_result: ToolResult) -> None:
        """Handle common post-action tasks like updating last_action."""
        if action_result.output and not action_result.error:
            # Extract action description from result for last_action update
            action_desc = getattr(self, '_last_action_description', f"{self.name}_executed")
            world_manager.update_machine_action(machine_id, action_desc)

    async def _handle_machine_destruction(self, machine_id: str) -> bool:
        """Handle machine destruction when life reaches 0. Returns True if machine was destroyed."""
        machine_info = world_manager.get_machine_info(machine_id)
        if machine_info and machine_info.life_value <= 0:
            # Mark machine as destroyed
            world_manager.update_machine_action(machine_id, "destroyed")
            # Remove from world immediately - frontend will handle visual effects
            world_manager.remove_machine(machine_id)
            return True
        return False


class LaserAttackTool(MachineActionTool):
    """Tool for performing laser attacks on other machines."""

    name: str = "laser_attack"
    description: str = "Perform a laser attack in the machine's facing direction. Laser can damage other machines and is blocked by obstacles."
    parameters: dict = {
        "type": "object",
        "properties": {
            "machine_id": {
                "type": "string",
                "description": "The ID of the machine performing the laser attack",
            },
            "range": {
                "type": "number",
                "description": "Maximum range of the laser attack (default: 5.0)",
                "default": 5.0,
            },
            "damage": {
                "type": "number",
                "description": "Damage points to inflict (default: 1)",
                "default": 1,
            },
        },
        "required": ["machine_id"],
    }

    async def _perform_action(self, machine_id: str, laser_range: float = 5.0, damage: int = 1, **kwargs) -> ToolResult:
        """Execute laser attack logic."""
        try:
            # Get attacker machine info (already validated by parent)
            attacker = world_manager.get_machine_info(machine_id)

            # Calculate laser path
            laser_path = self._calculate_laser_path(attacker, laser_range)

            # Find first collision (obstacle or machine)
            hit_result = self._find_laser_collision(attacker, laser_path)

            # Build attack result
            attack_data = {
                "attacker_id": machine_id,
                "attacker_position": str(attacker.position),
                "facing_direction": list(attacker.facing_direction),
                "laser_range": laser_range,
                "laser_path": [[p.coordinates[0], p.coordinates[1]] for p in laser_path],
                "hit_result": hit_result,
                "damage_dealt": damage if hit_result.get("hit_machine") else 0,
                "target_destroyed": False
            }

            # Apply damage if a machine was hit
            if hit_result.get("hit_machine"):
                target_id = hit_result["hit_machine"]
                success = world_manager.update_machine_life(target_id, -damage)
                if success:
                    target_info = world_manager.get_machine_info(target_id)
                    attack_data["target_remaining_life"] = target_info.life_value if target_info else 0

                    # Handle machine destruction in backend
                    destroyed = await self._handle_machine_destruction(target_id)
                    attack_data["target_destroyed"] = destroyed

            # Set action description for parent class (add timestamp for uniqueness)
            timestamp = int(time.time() * 1000)  # 毫秒时间戳
            self._last_action_description = f"laser_attack_range_{laser_range}_damage_{damage}_time_{timestamp}"

            return ToolResult(output=json.dumps(attack_data, indent=2, ensure_ascii=False))

        except Exception as e:
            return ToolResult(error=f"Laser attack failed: {str(e)}")

    def _calculate_laser_path(self, attacker, laser_range: float) -> List[Position]:
        """Calculate the path of the laser beam."""
        path = []

        # Start from attacker position
        start_x, start_y = attacker.position.coordinates[0], attacker.position.coordinates[1]
        dx, dy = attacker.facing_direction

        # Calculate path points with fine granularity
        step_size = 0.1
        steps = int(laser_range / step_size)

        for i in range(steps + 1):
            distance = i * step_size
            x = start_x + dx * distance
            y = start_y + dy * distance
            path.append(Position(x, y, 0.0))

        return path

    def _find_laser_collision(self, attacker, laser_path: List[Position]) -> dict:
        """Find the first collision along the laser path."""
        result = {"hit_type": "none", "hit_position": None}

        for point in laser_path[1:]:  # Skip starting position
            # Check for obstacle collision
            obstacles = world_manager.get_obstacles_in_area(point, 0.5, use_square_distance=True)
            if obstacles:
                result = {
                    "hit_type": "obstacle",
                    "hit_position": [point.coordinates[0], point.coordinates[1]],
                    "hit_obstacle": obstacles[0].obstacle_id
                }
                break

            # Check for machine collision - get all machines and check distance
            all_machines = world_manager.get_all_machines()
            for machine_id, machine in all_machines.items():
                if machine_id == attacker.machine_id:  # Skip self
                    continue

                machine_pos = machine.position
                # Check if laser point is close to this machine
                if (abs(point.coordinates[0] - machine_pos.coordinates[0]) < 0.5 and
                    abs(point.coordinates[1] - machine_pos.coordinates[1]) < 0.5):
                    result = {
                        "hit_type": "machine",
                        "hit_position": [point.coordinates[0], point.coordinates[1]],
                        "hit_machine": machine.machine_id
                    }
                    break

            if result["hit_type"] != "none":
                break

        return result


# Example: Template for future attack tools
class MeleeAttackTool(MachineActionTool):
    """Template for close-range melee attacks. This is just an example."""

    name: str = "melee_attack"
    description: str = "Perform a melee attack on adjacent machines. Template for future attack implementations."
    parameters: dict = {
        "type": "object",
        "properties": {
            "machine_id": {
                "type": "string",
                "description": "The ID of the machine performing the melee attack",
            },
            "damage": {
                "type": "number",
                "description": "Damage points to inflict (default: 2)",
                "default": 2,
            },
        },
        "required": ["machine_id"],
    }

    async def _perform_action(self, machine_id: str, damage: int = 2, **kwargs) -> ToolResult:
        """Example implementation of melee attack."""
        try:
            # Get attacker machine info (already validated by parent)
            attacker = world_manager.get_machine_info(machine_id)

            # Find adjacent machines (within 1.5 units)
            nearby_machines = world_manager.get_nearby_machines(machine_id, 1.5, use_square_distance=True)

            targets_hit = []

            # Attack all adjacent machines
            for target in nearby_machines:
                if target.machine_id != machine_id and target.status == "active":
                    # Apply damage
                    success = world_manager.update_machine_life(target.machine_id, -damage)
                    if success:
                        target_info = world_manager.get_machine_info(target.machine_id)
                        target_data = {
                            "target_id": target.machine_id,
                            "damage_dealt": damage,
                            "remaining_life": target_info.life_value if target_info else 0,
                            "destroyed": False
                        }

                        # Handle machine destruction
                        destroyed = await self._handle_machine_destruction(target.machine_id)
                        target_data["destroyed"] = destroyed

                        targets_hit.append(target_data)

            # Build attack result
            attack_data = {
                "attacker_id": machine_id,
                "attacker_position": str(attacker.position),
                "attack_type": "melee",
                "targets_hit": targets_hit,
                "total_targets": len(targets_hit)
            }

            # Set action description for parent class
            self._last_action_description = f"melee_attack_damage_{damage}_targets_{len(targets_hit)}"

            return ToolResult(output=json.dumps(attack_data, indent=2, ensure_ascii=False))

        except Exception as e:
            return ToolResult(error=f"Melee attack failed: {str(e)}")

# Note: To use MeleeAttackTool, add it to machine_tools in mcp/server.py
# and handle the "melee_attack" command type in machine agent
