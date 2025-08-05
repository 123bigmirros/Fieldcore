"""
Global world manager for tracking machine positions and world state.
"""

import asyncio
import json
import os
import tempfile
from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass
from threading import Lock
import time


@dataclass
class Position:
    """Represents a position in multi-dimensional space."""
    coordinates: Tuple[float, ...]

    def __init__(self, *coords: float):
        self.coordinates = tuple(coords)

    def distance_to(self, other: "Position") -> float:
        """Calculate Euclidean distance to another position."""
        if len(self.coordinates) != len(other.coordinates):
            raise ValueError("Positions must have same dimensions")

        return sum((a - b) ** 2 for a, b in zip(self.coordinates, other.coordinates)) ** 0.5

    def square_distance_to(self, other: "Position") -> float:
        """Calculate Chebyshev distance (square visibility) to another position."""
        if len(self.coordinates) != len(other.coordinates):
            raise ValueError("Positions must have same dimensions")

        return max(abs(a - b) for a, b in zip(self.coordinates, other.coordinates))

    def __str__(self) -> str:
        return f"({', '.join(map(str, self.coordinates))})"

    def is_within_bounds(self, min_pos: "Position", max_pos: "Position") -> bool:
        """Check if this position is within the given bounds."""
        if len(self.coordinates) != len(min_pos.coordinates) or len(self.coordinates) != len(max_pos.coordinates):
            raise ValueError("All positions must have same dimensions")

        return all(min_coord <= coord <= max_coord
                  for coord, min_coord, max_coord in
                  zip(self.coordinates, min_pos.coordinates, max_pos.coordinates))


@dataclass
class Obstacle:
    """Represents an obstacle in the world."""
    obstacle_id: str
    position: Position
    size: float = 1.0  # obstacle size (radius for circular obstacles)
    obstacle_type: str = "static"  # static, dynamic, etc.

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            'obstacle_id': self.obstacle_id,
            'position': list(self.position.coordinates),
            'size': self.size,
            'obstacle_type': self.obstacle_type
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Obstacle":
        """Create from dictionary."""
        return cls(
            obstacle_id=data['obstacle_id'],
            position=Position(*data['position']),
            size=data['size'],
            obstacle_type=data['obstacle_type']
        )


@dataclass
class MachineInfo:
    """Information about a machine in the world."""
    machine_id: str
    position: Position
    life_value: int
    machine_type: str
    status: str = "active"
    last_action: Optional[str] = None
    size: float = 1.0  # machine size (radius for collision detection)
    facing_direction: Tuple[float, float] = (1.0, 0.0)  # facing direction (x, y)

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            'machine_id': self.machine_id,
            'position': list(self.position.coordinates),
            'life_value': self.life_value,
            'machine_type': self.machine_type,
            'status': self.status,
            'last_action': self.last_action,
            'size': self.size,
            'facing_direction': list(self.facing_direction)
        }

    @classmethod
    def from_dict(cls, data: dict) -> "MachineInfo":
        """Create from dictionary."""
        return cls(
            machine_id=data['machine_id'],
            position=Position(*data['position']),
            life_value=data['life_value'],
            machine_type=data['machine_type'],
            status=data.get('status', 'active'),
            last_action=data.get('last_action'),
            size=data.get('size', 1.0),
            facing_direction=tuple(data.get('facing_direction', [1.0, 0.0]))
        )


class WorldManager:
    """Simple file-based world manager for cross-process sharing."""

    _instance: Optional["WorldManager"] = None
    _lock = Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, 'initialized'):
            self.world_dimensions: int = 3  # Default to 3D world
            self.world_bounds: Tuple[float, float] = (-100.0, 100.0)  # Min, Max for each dimension

            # Use temporary files for cross-process sharing
            self.shared_file = os.path.join(tempfile.gettempdir(), "openmanus_world_state.json")
            self.obstacles_file = os.path.join(tempfile.gettempdir(), "openmanus_obstacles.json")

            # Initialize with empty world if files don't exist
            if not os.path.exists(self.shared_file):
                self._save_world_state({})
            if not os.path.exists(self.obstacles_file):
                self._save_obstacles_state({})

            self.initialized = True

    def _load_world_state(self) -> Dict[str, dict]:
        """Load world state from shared file."""
        try:
            with open(self.shared_file, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def _save_world_state(self, machines: Dict[str, dict]):
        """Save world state to shared file."""
        with open(self.shared_file, 'w') as f:
            json.dump(machines, f, indent=2)

    def _load_obstacles_state(self) -> Dict[str, dict]:
        """Load obstacles state from shared file."""
        try:
            with open(self.obstacles_file, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def _save_obstacles_state(self, obstacles: Dict[str, dict]):
        """Save obstacles state to shared file."""
        with open(self.obstacles_file, 'w') as f:
            json.dump(obstacles, f, indent=2)

    def register_machine(self, machine_id: str, position: Position,
                        life_value: int = 10, machine_type: str = "generic", size: float = 1.0,
                        facing_direction: Tuple[float, float] = (1.0, 0.0)) -> None:
        """Register a new machine in the world."""
        machine_info = MachineInfo(
            machine_id=machine_id,
            position=position,
            life_value=life_value,
            machine_type=machine_type,
            size=size,
            facing_direction=facing_direction
        )

        # Load current state
        machines = self._load_world_state()
        machines[machine_id] = machine_info.to_dict()

        # Save updated state
        self._save_world_state(machines)

    def check_collision(self, position: Position, size: float = 1.0, exclude_machine_id: str = None) -> bool:
        """
        Check if a position would collide with any obstacles or other machines.

        Args:
            position: Position to check
            size: Size of the object (default: 1.0)
            exclude_machine_id: Machine ID to exclude from collision check (for movement)

        Returns:
            True if collision detected, False otherwise
        """

        # Check collision with static obstacles
        obstacles = self._load_obstacles_state()
        for obstacle_data in obstacles.values():
            obstacle = Obstacle.from_dict(obstacle_data)
            distance = position.distance_to(obstacle.position)
            # 允许接触但不重叠，distance == 0 表示完全重叠
            if distance < max(size, obstacle.size) * 0.5:
                return True

        # Check collision with other machines
        machines = self._load_world_state()
        for machine_id, machine_data in machines.items():
            if machine_id == exclude_machine_id:
                continue  # Skip the machine that is moving

            machine_info = MachineInfo.from_dict(machine_data)
            if machine_info.status != "active":
                continue  # Skip inactive machines

            distance = position.distance_to(machine_info.position)
            # 允许相邻放置，只有重叠时才算碰撞 (距离 < 0.5 * 较大的尺寸)
            if distance < max(size, machine_info.size) * 0.5:
                return True

        return False

    def find_collision_details(self, position: Position, size: float = 1.0, exclude_machine_id: str = None) -> List[str]:
        """
        Find details about what would collide with the given position.

        Args:
            position: Position to check
            size: Size of the object (default: 1.0)
            exclude_machine_id: Machine ID to exclude from collision check

        Returns:
            List of collision descriptions
        """

        collisions = []

        # Check collision with static obstacles
        obstacles = self._load_obstacles_state()
        for obstacle_data in obstacles.values():
            obstacle = Obstacle.from_dict(obstacle_data)
            distance = position.distance_to(obstacle.position)
            # 使用与check_collision相同的逻辑
            if distance < max(size, obstacle.size) * 0.5:
                collisions.append(f"障碍物 {obstacle.obstacle_id} 在位置 {obstacle.position}")

        # Check collision with other machines
        machines = self._load_world_state()
        for machine_id, machine_data in machines.items():
            if machine_id == exclude_machine_id:
                continue

            machine_info = MachineInfo.from_dict(machine_data)
            if machine_info.status != "active":
                continue

            distance = position.distance_to(machine_info.position)
            # 使用与check_collision相同的逻辑
            if distance < max(size, machine_info.size) * 0.5:
                collisions.append(f"机器人 {machine_id} 在位置 {machine_info.position}")

        return collisions

    def update_machine_position(self, machine_id: str, new_position: Position) -> bool:
        """Update a machine's position with collision detection. Returns True if successful."""
        machines = self._load_world_state()

        if machine_id not in machines:
            return False

        # Check bounds
        for coord in new_position.coordinates:
            if not (self.world_bounds[0] <= coord <= self.world_bounds[1]):
                return False

        # Get machine info for size
        machine_info = MachineInfo.from_dict(machines[machine_id])

        # Check for collisions (exclude the machine that is moving)
        if self.check_collision(new_position, machine_info.size, exclude_machine_id=machine_id):
            return False

        # Update position
        machines[machine_id]['position'] = list(new_position.coordinates)
        self._save_world_state(machines)
        return True

    def update_machine_position_with_details(self, machine_id: str, new_position: Position) -> Tuple[bool, List[str]]:
        """
        Update machine position with detailed collision information.

        Returns:
            Tuple of (success, collision_details)
        """
        machines = self._load_world_state()

        if machine_id not in machines:
            return False, ["机器人不存在"]

        # Check bounds
        for coord in new_position.coordinates:
            if not (self.world_bounds[0] <= coord <= self.world_bounds[1]):
                return False, [f"位置超出世界边界 {self.world_bounds}"]

        # Get machine info for size
        machine_info = MachineInfo.from_dict(machines[machine_id])

        # Check for collisions with details
        collision_details = self.find_collision_details(new_position, machine_info.size, exclude_machine_id=machine_id)
        if collision_details:
            return False, collision_details

        # Update position
        machines[machine_id]['position'] = list(new_position.coordinates)
        self._save_world_state(machines)
        return True, []

    def get_machine_info(self, machine_id: str) -> Optional[MachineInfo]:
        """Get information about a specific machine."""
        machines = self._load_world_state()
        data = machines.get(machine_id)
        if data:
            return MachineInfo.from_dict(data)
        return None

    def get_nearby_machines(self, machine_id: str, radius: float = 10.0, use_square_distance: bool = False) -> List[MachineInfo]:
        """Get all machines within a certain radius of the specified machine."""
        machines = self._load_world_state()

        if machine_id not in machines:
            return []

        center_position = Position(*machines[machine_id]['position'])
        nearby = []

        for other_id, other_data in machines.items():
            if other_id != machine_id:
                other_position = Position(*other_data['position'])
                if use_square_distance:
                    distance = center_position.square_distance_to(other_position)
                else:
                    distance = center_position.distance_to(other_position)
                if distance <= radius:
                    nearby.append(MachineInfo.from_dict(other_data))

        return nearby

    def get_all_machines(self) -> Dict[str, MachineInfo]:
        """Get all registered machines."""
        machines = self._load_world_state()
        result = {}
        for machine_id, data in machines.items():
            result[machine_id] = MachineInfo.from_dict(data)
        return result

    def remove_machine(self, machine_id: str) -> bool:
        """Remove a machine from the world."""
        machines = self._load_world_state()
        if machine_id in machines:
            del machines[machine_id]
            self._save_world_state(machines)
            return True
        return False

    def update_machine_life(self, machine_id: str, life_change: int) -> bool:
        """Update a machine's life value."""
        machines = self._load_world_state()

        if machine_id not in machines:
            return False

        # Update life value
        machines[machine_id]['life_value'] += life_change

        # Remove machine if life drops to 0 or below
        if machines[machine_id]['life_value'] <= 0:
            machines[machine_id]['status'] = "destroyed"

        self._save_world_state(machines)
        return True

    def update_machine_action(self, machine_id: str, action: str) -> bool:
        """Update a machine's last action."""
        machines = self._load_world_state()

        if machine_id not in machines:
            return False

        # Update last action
        machines[machine_id]['last_action'] = action
        self._save_world_state(machines)
        return True

    # Obstacle management methods
    def add_obstacle(self, obstacle_id: str, position: Position, size: float = 1.0, obstacle_type: str = "static") -> bool:
        """Add a new obstacle to the world."""
        obstacles = self._load_obstacles_state()

        if obstacle_id in obstacles:
            return False  # Obstacle already exists

        # Check if the obstacle position collides with existing machines or obstacles
        if self.check_collision(position, size):
            return False

        obstacle = Obstacle(
            obstacle_id=obstacle_id,
            position=position,
            size=size,
            obstacle_type=obstacle_type
        )

        obstacles[obstacle_id] = obstacle.to_dict()
        self._save_obstacles_state(obstacles)
        return True

    def remove_obstacle(self, obstacle_id: str) -> bool:
        """Remove an obstacle from the world."""
        obstacles = self._load_obstacles_state()
        if obstacle_id in obstacles:
            del obstacles[obstacle_id]
            self._save_obstacles_state(obstacles)
            return True
        return False

    def get_obstacle(self, obstacle_id: str) -> Optional[Obstacle]:
        """Get information about a specific obstacle."""
        obstacles = self._load_obstacles_state()
        data = obstacles.get(obstacle_id)
        if data:
            return Obstacle.from_dict(data)
        return None

    def get_all_obstacles(self) -> Dict[str, Obstacle]:
        """Get all obstacles in the world."""
        obstacles = self._load_obstacles_state()
        result = {}
        for obstacle_id, data in obstacles.items():
            result[obstacle_id] = Obstacle.from_dict(data)
        return result

    def clear_all_obstacles(self) -> None:
        """Remove all obstacles from the world."""
        self._save_obstacles_state({})

    def get_obstacles_in_area(self, center: Position, radius: float, use_square_distance: bool = False) -> List[Obstacle]:
        """Get all obstacles within a certain radius of the center position."""
        obstacles = self._load_obstacles_state()
        result = []

        for obstacle_data in obstacles.values():
            obstacle = Obstacle.from_dict(obstacle_data)
            if use_square_distance:
                distance = center.square_distance_to(obstacle.position)
            else:
                distance = center.distance_to(obstacle.position)
            if distance <= radius:
                result.append(obstacle)

        return result


# Global instance
world_manager = WorldManager()
