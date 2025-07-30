"""
Global world manager for tracking machine positions and world state.
"""

import asyncio
import json
import os
import tempfile
from typing import Dict, List, Optional, Tuple
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

    def __str__(self) -> str:
        return f"({', '.join(map(str, self.coordinates))})"


@dataclass
class MachineInfo:
    """Information about a machine in the world."""
    machine_id: str
    position: Position
    life_value: int
    machine_type: str
    status: str = "active"
    last_action: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            'machine_id': self.machine_id,
            'position': list(self.position.coordinates),
            'life_value': self.life_value,
            'machine_type': self.machine_type,
            'status': self.status,
            'last_action': self.last_action
        }

    @classmethod
    def from_dict(cls, data: dict) -> "MachineInfo":
        """Create from dictionary."""
        return cls(
            machine_id=data['machine_id'],
            position=Position(*data['position']),
            life_value=data['life_value'],
            machine_type=data['machine_type'],
            status=data['status'],
            last_action=data['last_action']
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

            # Use a temporary file for cross-process sharing
            self.shared_file = os.path.join(tempfile.gettempdir(), "openmanus_world_state.json")

            # Initialize with empty world if file doesn't exist
            if not os.path.exists(self.shared_file):
                self._save_world_state({})

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

    def register_machine(self, machine_id: str, position: Position,
                        life_value: int = 10, machine_type: str = "generic") -> None:
        """Register a new machine in the world."""
        machine_info = MachineInfo(
            machine_id=machine_id,
            position=position,
            life_value=life_value,
            machine_type=machine_type
        )

        # Load current state
        machines = self._load_world_state()
        machines[machine_id] = machine_info.to_dict()

        # Save updated state
        self._save_world_state(machines)

    def update_machine_position(self, machine_id: str, new_position: Position) -> bool:
        """Update a machine's position. Returns True if successful."""
        machines = self._load_world_state()

        if machine_id not in machines:
            return False

        # Check bounds
        for coord in new_position.coordinates:
            if not (self.world_bounds[0] <= coord <= self.world_bounds[1]):
                return False

        # Update position
        machines[machine_id]['position'] = list(new_position.coordinates)
        self._save_world_state(machines)
        return True

    def get_machine_info(self, machine_id: str) -> Optional[MachineInfo]:
        """Get information about a specific machine."""
        machines = self._load_world_state()
        data = machines.get(machine_id)
        if data:
            return MachineInfo.from_dict(data)
        return None

    def get_nearby_machines(self, machine_id: str, radius: float = 10.0) -> List[MachineInfo]:
        """Get all machines within a certain radius of the specified machine."""
        machines = self._load_world_state()

        if machine_id not in machines:
            return []

        center_position = Position(*machines[machine_id]['position'])
        nearby = []

        for other_id, other_data in machines.items():
            if other_id != machine_id:
                other_position = Position(*other_data['position'])
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


# Global instance
world_manager = WorldManager()
