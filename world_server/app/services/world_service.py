# -*- coding: utf-8 -*-
"""
World Service - World management service (main service)

Coordinates submodules and provides a unified API
"""

from typing import Dict, List, Optional, Tuple
from threading import Lock

from ..models import Position, MachineInfo
from ..config import config
from ..handlers.action_handler import ActionHandler
from ..utils.world_storage import WorldStorage
from ..utils.frontend_serializer import FrontendSerializer
from .collision_service import CollisionService
from .view_service import ViewService
from .command_queue_service import command_queue_service


def _is_visible(position, my_machines):
    """Chebyshev distance check: is position within any machine's field of view"""
    for m in my_machines:
        mx, my_ = m["position"][0], m["position"][1]
        dx = abs(position[0] - mx)
        dy = abs(position[1] - my_)
        if max(dx, dy) <= m.get("view_size", 3):
            return True
    return False


class WorldService:
    """World management service - singleton"""

    _instance: Optional["WorldService"] = None
    _lock = Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, 'initialized'):
            return

        self.world_bounds = config.WORLD_BOUNDS
        self._machines: Dict[str, dict] = {}
        self._obstacles: Dict[str, dict] = {}
        self._data_lock = Lock()

        # Initialize submodules
        self._storage = WorldStorage()
        self._collision_service = CollisionService(self._machines, self._obstacles)
        self._actions = ActionHandler(self.world_bounds, self._collision_service.check_collision)
        self._view_service = ViewService(self._machines, self._obstacles)
        self._serializer = FrontendSerializer()

        # Load or initialize
        machines, obstacles, loaded = self._storage.load()
        if loaded:
            self._machines = machines
            self._obstacles = obstacles
        else:
            self._obstacles = WorldStorage.create_default_obstacles()

        # Initialize command queue service
        command_queue_service.set_execute_callback(self._execute_action_internal)
        command_queue_service.start_consumer()

        # Create queues for existing machines
        for machine_id in self._machines.keys():
            command_queue_service.create_queue(machine_id)

        self.initialized = True

    # ==================== Core API ====================

    def register_machine(
        self,
        machine_id: str,
        position: List[float],
        owner: str = "",
        life_value: int = config.DEFAULT_LIFE_VALUE,
        machine_type: str = config.DEFAULT_MACHINE_TYPE,
        size: float = config.DEFAULT_SIZE,
        facing_direction: Tuple[float, float] = (1.0, 0.0),
        view_size: int = config.DEFAULT_VIEW_SIZE
    ) -> Tuple[bool, str]:
        """Register a machine"""
        with self._data_lock:
            if machine_id in self._machines:
                return False, "Machine already exists"

            pos = Position(*position)
            if self._collision_service.check_collision(pos, size):
                return False, "Position has collision"

            # Ensure view_size is odd and at least 1
            view_size = max(1, int(view_size))
            if view_size % 2 == 0:
                view_size += 1

            machine = MachineInfo(
                machine_id=machine_id,
                position=pos,
                life_value=life_value,
                machine_type=machine_type,
                owner=owner,
                size=size,
                facing_direction=facing_direction,
                view_size=view_size,
            )
            self._machines[machine_id] = machine.to_dict()

            # Create command queue for the new machine
            command_queue_service.create_queue(machine_id)

            return True, ""

    def _execute_action_internal(self, machine_id: str, action: str, params: dict) -> dict:
        """
        Internal method: execute an action (called by command queue service)

        Note: called from the consumer thread, must be thread-safe
        """
        with self._data_lock:
            if machine_id not in self._machines:
                return {'success': False, 'error': 'Machine not found'}

            machine = self._machines[machine_id]
            if machine.get('status') != 'active':
                return {'success': False, 'error': f"Machine not active: {machine.get('status')}"}

            if action == 'move':
                return self._actions.move(machine, params, machine_id)
            elif action == 'attack':
                return self._actions.attack(machine, params, self._machines, self._obstacles, machine_id)
            elif action == 'turn':
                return self._actions.turn(machine, params)
            elif action == 'grab':
                return self._actions.grab(machine, params, self._obstacles, machine_id)
            elif action == 'drop':
                return self._actions.drop(machine, params, self._obstacles, machine_id)
            elif action == 'remove':
                del self._machines[machine_id]
                command_queue_service.remove_queue(machine_id)
                return {'success': True, 'result': 'Machine removed'}
            else:
                return {'success': False, 'error': f'Unknown action: {action}'}

    def enqueue_command(self, machine_id: str, action: str, params: dict) -> dict:
        """
        Enqueue a command

        Args:
            machine_id: Machine ID
            action: Action type
            params: Action parameters

        Returns:
            Dict with success status
        """
        with self._data_lock:
            if machine_id not in self._machines:
                return {'success': False, 'error': 'Machine not found'}

        success = command_queue_service.enqueue_command(machine_id, action, params)
        if success:
            return {'success': True, 'message': 'Command enqueued'}
        else:
            return {'success': False, 'error': 'Command queue is full'}

    def save_world(self) -> bool:
        """Save world state"""
        with self._data_lock:
            return self._storage.save(self._machines, self._obstacles)

    def get_machine_view(self, machine_id: str) -> Optional[dict]:
        """Get field of view"""
        with self._data_lock:
            return self._view_service.get_machine_view(machine_id)

    # ==================== Debug Methods ====================

    def get_all_machines(self) -> dict:
        """Get all machines (raw format)"""
        with self._data_lock:
            return dict(self._machines)

    def get_all_obstacles(self) -> dict:
        """Get all obstacles (raw format)"""
        with self._data_lock:
            return dict(self._obstacles)

    def reset_world(self) -> dict:
        """Reset world"""
        with self._data_lock:
            count = len(self._machines)
            # Clean up all command queues
            for machine_id in list(self._machines.keys()):
                command_queue_service.remove_queue(machine_id)
            self._machines.clear()
            self._obstacles = WorldStorage.create_default_obstacles()
            return {'machines_removed': count}

    def get_machine(self, machine_id: str) -> Optional[dict]:
        """Get a single machine's info"""
        with self._data_lock:
            return self._machines.get(machine_id)

    # ==================== Frontend Data API ====================

    def get_machines_for_frontend(self) -> List[dict]:
        """Get all machine data (frontend format)"""
        with self._data_lock:
            return self._serializer.serialize_machines(self._machines)

    def get_obstacles_for_frontend(self) -> List[dict]:
        """Get all obstacle data (frontend format)"""
        with self._data_lock:
            return self._serializer.serialize_obstacles(self._obstacles)

    def get_carried_resources_for_frontend(self) -> List[dict]:
        """Get all carried resource data (frontend format)"""
        with self._data_lock:
            return self._serializer.serialize_carried_resources(self._machines)

    def get_view_for_human(self, human_id: str) -> dict:
        """Get world data visible to a player (fog of war filtered)"""
        with self._data_lock:
            # Find all machines owned by this player
            my_machines = []
            my_machine_ids = []
            for mid, mdata in self._machines.items():
                if mdata.get("owner") == human_id:
                    my_machine_ids.append(mid)
                    pos = mdata.get("position", [0, 0, 0])
                    my_machines.append({
                        "position": pos,
                        "view_size": mdata.get("view_size", 3),
                    })

            # Serialize full data
            all_machines = self._serializer.serialize_machines(self._machines)
            all_obstacles = self._serializer.serialize_obstacles(self._obstacles)
            all_carried = self._serializer.serialize_carried_resources(self._machines)

            # Filter: keep only entities within field of view (own machines always visible)
            visible_machines = [
                m for m in all_machines
                if m["machine_id"] in my_machine_ids
                or _is_visible(m["position"], my_machines)
            ]
            visible_obstacles = [
                o for o in all_obstacles
                if _is_visible(o["position"], my_machines)
            ]
            visible_carried = [
                r for r in all_carried
                if _is_visible(r["position"], my_machines)
            ]

            return {
                "machines": visible_machines,
                "obstacles": visible_obstacles,
                "carried_resources": visible_carried,
                "my_machine_ids": my_machine_ids,
            }


# Global instance
world_service = WorldService()
