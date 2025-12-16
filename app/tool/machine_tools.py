"""
Tools specific to Machine agents for environment interaction and movement.
"""

import json
import time
from typing import Any, Dict, List, Optional, Tuple

from app.agent.world_manager import Position, world_manager
from app.logger import logger
from app.service.map_manager import MapObservation, map_manager
from app.tool.base import BaseTool, ToolResult


class CheckEnvironmentTool(BaseTool):
    """Tool for checking the surrounding environment and nearby machines."""

    name: str = "machine_check_environment"
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



class StepMovementTool(BaseTool):
    """Tool for step-by-step movement with collision checking and direction setting."""

    name: str = "machine_step_movement"
    description: str = "Move machine step-by-step towards target, stopping at obstacles. Supports four cardinal directions: East [1,0,0], North [0,1,0], West [-1,0,0], South [0,-1,0]. Set distance=0 to only change direction without moving."
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
                "description": "Direction vector [x, y, z]. Cardinal directions: East [1,0,0], North [0,1,0], West [-1,0,0], South [0,-1,0]",
            },
            "distance": {
                "type": "number",
                "description": "Number of units to move in the direction. Use 0 to only change facing direction without moving.",
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

            # 更新机器人朝向（只使用x,y分量）
            facing_direction = (normalized_direction[0], normalized_direction[1])
            world_manager.update_machine_direction(machine_id, facing_direction)

            # 如果距离为0，只更新方向不移动
            if distance == 0:
                return ToolResult(output=f"Machine {machine_id} direction updated to {facing_direction}")

            # 计算目标位置（确保整数坐标）
            current_pos = machine_info.position
            target_x = round(current_pos.coordinates[0] + normalized_direction[0] * distance)
            target_y = round(current_pos.coordinates[1] + normalized_direction[1] * distance)
            target_z = round((current_pos.coordinates[2] if len(current_pos.coordinates) > 2 else 0.0) + (normalized_direction[2] if len(normalized_direction) > 2 else 0) * distance)

            target_position = Position(float(target_x), float(target_y), float(target_z))

            # 使用逐步移动
            result = await self._step_by_step_movement(machine_id, current_pos, target_position)

            # 在移动结果中添加方向更新信息
            if hasattr(result, 'output') and result.output:
                result.output += f" Direction updated to {facing_direction}."

            return result

        except Exception as e:
            return ToolResult(error=f"Step movement failed: {str(e)}")

    async def _step_by_step_movement(self, machine_id: str, start_pos: Position, target_pos: Position) -> ToolResult:
        """逐步移动，每单位检查碰撞"""
        current_pos = start_pos
        steps_taken = 0

        # 计算移动方向和总步数
        dx = target_pos.coordinates[0] - start_pos.coordinates[0]
        dy = target_pos.coordinates[1] - start_pos.coordinates[1]
        dz = (target_pos.coordinates[2] if len(target_pos.coordinates) > 2 else 0.0) - (start_pos.coordinates[2] if len(start_pos.coordinates) > 2 else 0.0)

                # 计算总移动距离，使用1单位作为最小移动步长
        total_distance = (dx**2 + dy**2 + dz**2) ** 0.5
        if total_distance == 0:
            return ToolResult(output=f"Machine {machine_id} already at target position")

        # 每步移动1单位，确保移动单位为整数
        step_size = 1.0
        total_steps = max(1, int(total_distance / step_size))

        # 计算每步的增量（保证每步移动1单位）
        step_x = dx / total_steps if total_steps > 0 else 0
        step_y = dy / total_steps if total_steps > 0 else 0
        step_z = dz / total_steps if total_steps > 0 else 0

        # 逐步移动（支持中断）
        import asyncio
        for step in range(1, int(total_steps) + 1):
            # 通过睡眠控制移动速度，让前端能够看到移动过程
            try:
                await asyncio.sleep(0.8)  # 800ms每步，前端300ms刷新能看到移动过程
            except asyncio.CancelledError:
                world_manager.update_machine_action(machine_id, f"cancelled_at_{current_pos}")
                return ToolResult(output=f"Machine {machine_id} movement cancelled at {current_pos} after {steps_taken} steps")

            next_x = start_pos.coordinates[0] + step_x * step
            next_y = start_pos.coordinates[1] + step_y * step
            next_z = (start_pos.coordinates[2] if len(start_pos.coordinates) > 2 else 0.0) + step_z * step
            next_pos = Position(next_x, next_y, next_z)  # Position类会自动四舍五入到整数

            # 检查下一步是否会碰撞
            if world_manager.check_collision(next_pos, exclude_machine_id=machine_id):
                # 遇到障碍物，停止移动
                collision_details = world_manager.find_collision_details(next_pos, exclude_machine_id=machine_id)
                details_str = "; ".join(collision_details)
                world_manager.update_machine_action(machine_id, f"stopped_at_{current_pos}_due_to_collision")
                return ToolResult(output=f"Machine {machine_id} moved {steps_taken} units to {current_pos}, stopped due to collision: {details_str}")

            # 移动到下一位置
            success = world_manager.update_machine_position(machine_id, next_pos)
            if not success:
                world_manager.update_machine_action(machine_id, f"stopped_at_{current_pos}_update_failed")
                return ToolResult(error=f"Movement failed at step {step}. Position update failed for {next_pos}")

            current_pos = next_pos
            steps_taken = step

        # 成功完成移动
        world_manager.update_machine_action(machine_id, f"moved_to_{current_pos}")
        self._record_map_observation(machine_id)
        return ToolResult(output=f"Machine {machine_id} successfully moved to {current_pos} in {steps_taken} units")

    def _record_map_observation(self, machine_id: str) -> None:
        """Fetch latest view for the machine and push to map manager."""
        try:
            view_payload = world_manager.get_machine_view(machine_id)
            if not view_payload:
                return
            center = view_payload.get("center", [0, 0])
            observation = MapObservation(
                machine_id=machine_id,
                position=(int(center[0]), int(center[1])),
                view=view_payload.get("cells", []),
            )
            map_manager.submit_observation(observation)
        except Exception as exc:  # pylint: disable=broad-except
            logger.error("Failed to record map observation for %s: %s", machine_id, exc)


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

    name: str = "machine_laser_attack"
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
                "description": "Maximum range of the laser attack (default: unlimited - goes to world boundary)",
                "default": 999.0,
            },
            "damage": {
                "type": "number",
                "description": "Damage points to inflict (default: 1)",
                "default": 1,
            },
        },
        "required": ["machine_id"],
    }

    async def _perform_action(self, machine_id: str, laser_range: float = 999.0, damage: int = 1, **kwargs) -> ToolResult:
        """Execute laser attack logic."""
        try:
            # Get attacker machine info (already validated by parent)
            attacker = world_manager.get_machine_info(machine_id)

            # Calculate laser path using grid-based algorithm (ignore range limit, go to world boundary)
            full_laser_path = self._calculate_laser_path(attacker, laser_range)

            # Find first collision (obstacle or machine)
            hit_result = self._find_laser_collision(attacker, full_laser_path)

            # 根据碰撞结果截断激光路径
            if hit_result["hit_type"] != "none" and "path_index" in hit_result:
                # 截断到碰撞点（包含碰撞点）
                actual_laser_path = full_laser_path[:hit_result["path_index"] + 1]
            else:
                # 没有碰撞，使用完整路径
                actual_laser_path = full_laser_path

            # Build attack result with grid information
            attack_data = {
                "attacker_id": machine_id,
                "attacker_position": [round(attacker.position.coordinates[0]), round(attacker.position.coordinates[1])],
                "facing_direction": list(attacker.facing_direction),
                "laser_range": laser_range,
                "laser_path_grids": [{"x": round(p.coordinates[0]), "y": round(p.coordinates[1])} for p in actual_laser_path],
                "laser_start_pos": [round(attacker.position.coordinates[0]), round(attacker.position.coordinates[1])],
                "laser_end_pos": [round(actual_laser_path[-1].coordinates[0]), round(actual_laser_path[-1].coordinates[1])] if actual_laser_path else [round(attacker.position.coordinates[0]), round(attacker.position.coordinates[1])],
                "hit_result": hit_result,
                "damage_dealt": damage if hit_result.get("hit_machine") else 0,
                "target_destroyed": False,
                "actual_range": len(actual_laser_path) - 1  # 不计算起始网格
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

            # Set action description with attack result data for frontend (add timestamp for uniqueness)
            timestamp = int(time.time() * 1000)  # 毫秒时间戳
            self._last_action_description = f"laser_attack_range_{laser_range}_damage_{damage}_time_{timestamp}_result_{json.dumps(attack_data)}"

            return ToolResult(output=json.dumps(attack_data, indent=2, ensure_ascii=False))

        except Exception as e:
            return ToolResult(error=f"Laser attack failed: {str(e)}")

    def _calculate_laser_path(self, attacker, laser_range: float) -> List[Position]:
        """Calculate the laser path to world boundary using grid-based Bresenham algorithm."""
        # 将起始坐标对齐到网格中心
        start_x = round(attacker.position.coordinates[0])
        start_y = round(attacker.position.coordinates[1])
        dx, dy = attacker.facing_direction

        # 计算到世界边界的最大射程（而不是固定5格）
        world_bounds = world_manager.world_bounds  # (-100, 100)
        min_bound, max_bound = world_bounds

        # 计算在当前方向上能到达的最远网格
        if dx > 0:  # 向右
            max_x = max_bound
        elif dx < 0:  # 向左
            max_x = min_bound
        else:  # 不移动
            max_x = start_x

        if dy > 0:  # 向上
            max_y = max_bound
        elif dy < 0:  # 向下
            max_y = min_bound
        else:  # 不移动
            max_y = start_y

        # 计算到边界的距离
        if dx != 0:
            steps_x = abs((max_x - start_x) / dx)
        else:
            steps_x = float('inf')

        if dy != 0:
            steps_y = abs((max_y - start_y) / dy)
        else:
            steps_y = float('inf')

        # 选择最小步数（先到达的边界）
        max_steps = min(steps_x, steps_y)
        if max_steps == float('inf'):
            max_steps = max(abs(max_bound - start_x), abs(max_bound - start_y))

        # 计算实际终点
        end_x = start_x + round(dx * max_steps)
        end_y = start_y + round(dy * max_steps)

        # 确保终点在世界边界内
        end_x = max(min_bound, min(max_bound, end_x))
        end_y = max(min_bound, min(max_bound, end_y))

        # 使用Bresenham算法计算网格路径
        grids = self._get_line_grids(start_x, start_y, end_x, end_y)

        # 转换为Position对象列表
        path = []
        for grid in grids:
            path.append(Position(grid["x"], grid["y"], 0.0))

        return path

    def _get_line_grids(self, start_x: int, start_y: int, end_x: int, end_y: int) -> List[dict]:
        """使用Bresenham算法计算直线上的网格点"""
        grids = [{"x": start_x, "y": start_y}]

        # Bresenham直线算法
        x, y = start_x, start_y
        delta_x = abs(end_x - start_x)
        delta_y = abs(end_y - start_y)
        step_x = 1 if start_x < end_x else -1
        step_y = 1 if start_y < end_y else -1
        error = delta_x - delta_y

        while x != end_x or y != end_y:
            error2 = 2 * error

            if error2 > -delta_y:
                error -= delta_y
                x += step_x

            if error2 < delta_x:
                error += delta_x
                y += step_y

            grids.append({"x": x, "y": y})

            # 防止无限循环
            if len(grids) > 100:  # 安全限制
                break

        return grids

    def _find_laser_collision(self, attacker, laser_path: List[Position]) -> dict:
        """Find the first collision along the grid-based laser path."""
        result = {"hit_type": "none", "hit_position": None, "collision_grid": None}

        # 创建实体位置的网格映射
        grid_obstacles = {}
        grid_machines = {}

        # 将障碍物映射到网格
        all_obstacles = world_manager.get_all_obstacles()
        for obstacle_id, obstacle in all_obstacles.items():
            obs_x = round(obstacle.position.coordinates[0])
            obs_y = round(obstacle.position.coordinates[1])
            grid_key = f"{obs_x},{obs_y}"
            grid_obstacles[grid_key] = obstacle

        # 将机器人映射到网格（排除发射者）
        all_machines = world_manager.get_all_machines()
        for machine_id, machine in all_machines.items():
            if machine_id == attacker.machine_id:  # 排除自己
                continue
            if machine.status != "active":  # 排除非活跃机器
                continue

            mach_x = round(machine.position.coordinates[0])
            mach_y = round(machine.position.coordinates[1])
            grid_key = f"{mach_x},{mach_y}"
            grid_machines[grid_key] = machine

        # 检查路径上每个网格的碰撞（跳过起始网格）
        for i, point in enumerate(laser_path[1:], 1):
            grid_x = round(point.coordinates[0])
            grid_y = round(point.coordinates[1])
            grid_key = f"{grid_x},{grid_y}"

            # 检查障碍物碰撞
            if grid_key in grid_obstacles:
                obstacle = grid_obstacles[grid_key]
                result = {
                    "hit_type": "obstacle",
                    "hit_position": [grid_x, grid_y],
                    "hit_obstacle": obstacle.obstacle_id,
                    "collision_grid": {"x": grid_x, "y": grid_y},
                    "path_index": i
                }
                break

            # 检查机器人碰撞
            if grid_key in grid_machines:
                machine = grid_machines[grid_key]
                result = {
                    "hit_type": "machine",
                    "hit_position": [grid_x, grid_y],
                    "hit_machine": machine.machine_id,
                    "collision_grid": {"x": grid_x, "y": grid_y},
                    "path_index": i
                }
                break

        return result


# 删除MeleeAttackTool模板类 - 只是示例代码，未实际使用


class GetSelfStatusTool(BaseTool):
    """Tool for machine to get its own status information."""

    name: str = "machine_get_self_status"
    description: str = "Get the machine's own current status including position, facing_direction (cardinal direction the machine is facing), life_value, etc. Use this to check current facing direction before moving."
    parameters: dict = {
        "type": "object",
        "properties": {
            "machine_id": {
                "type": "string",
                "description": "The ID of the machine to get status for",
            },
        },
        "required": ["machine_id"],
    }

    async def execute(self, machine_id: str, **kwargs) -> ToolResult:
        """Get machine's own status information."""
        try:
            machine_info = world_manager.get_machine_info(machine_id)
            if not machine_info:
                return ToolResult(error=f"Machine {machine_id} not found in world registry")

            status_data = {
                "machine_id": machine_info.machine_id,
                "position": list(machine_info.position.coordinates),
                "facing_direction": list(machine_info.facing_direction),
                "life_value": machine_info.life_value,
                "machine_type": machine_info.machine_type,
                "status": machine_info.status,
                "last_action": machine_info.last_action,
                "size": machine_info.size
            }

            return ToolResult(output=json.dumps(status_data, indent=2, ensure_ascii=False))

        except Exception as e:
            return ToolResult(error=f"Failed to get self status: {str(e)}")
