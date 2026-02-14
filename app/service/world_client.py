# -*- coding: utf-8 -*-
"""World Client — HTTP client for the World Server microservice."""

import requests
from typing import Dict, List, Optional, Tuple


class WorldClient:
    """HTTP client for the World Server."""

    def __init__(self, base_url: str = "http://localhost:8005"):
        self.base_url = base_url
        self.timeout = 5

    def _post(self, path: str, data: dict = None) -> dict:
        """POST request, returns parsed JSON."""
        resp = requests.post(f"{self.base_url}{path}", json=data, timeout=self.timeout)
        return resp.json()

    def _get(self, path: str) -> dict:
        """GET request, returns parsed JSON."""
        resp = requests.get(f"{self.base_url}{path}", timeout=self.timeout)
        return resp.json()

    @staticmethod
    def _unwrap(result: dict):
        """Extract data from the unified response envelope."""
        if "data" in result and "success" in result:
            return result["data"]
        return result

    # ==================== Core API ====================

    def register_machine(
        self,
        machine_id: str,
        position: List[float],
        owner: str = "",
        life_value: int = 10,
        machine_type: str = "worker",
        size: float = 1.0,
        facing_direction: Tuple[float, float] = (1.0, 0.0),
        view_size: int = 3,
    ) -> Tuple[bool, str]:
        """Register a machine in the world."""
        result = self._post(
            "/api/v1/world/machines",
            {
                "machine_id": machine_id,
                "position": position,
                "owner": owner,
                "life_value": life_value,
                "machine_type": machine_type,
                "size": size,
                "facing_direction": list(facing_direction),
                "view_size": view_size,
            },
        )
        return result.get("success", False), self._get_error(result)

    def machine_action(self, machine_id: str, action: str, params: dict = None) -> dict:
        """Execute a machine action."""
        result = self._post(
            f"/api/v1/world/machines/{machine_id}/actions",
            {"action": action, "params": params or {}},
        )
        # Unwrap: the actual action result is inside data
        if result.get("success"):
            return {"success": True, "result": self._unwrap(result)}
        return result

    def save_world(self) -> bool:
        """Persist world state."""
        result = self._post("/api/v1/world/state")
        return result.get("success", False)

    def get_machine_view(self, machine_id: str) -> Optional[dict]:
        """Get a machine's field-of-view."""
        result = self._get(f"/api/v1/world/machines/{machine_id}/view")
        if result.get("success"):
            return self._unwrap(result)
        return None

    @staticmethod
    def _get_error(result: dict) -> str:
        """Extract error message from unified response."""
        err = result.get("error")
        if isinstance(err, dict):
            return err.get("message", "")
        return err or ""

    # ==================== Convenience methods ====================

    def move(self, machine_id: str, direction: List[float], distance: float) -> dict:
        """Move a machine."""
        return self.machine_action(machine_id, "move", {"direction": direction, "distance": distance})

    def attack(self, machine_id: str, damage: int = 1) -> dict:
        """Attack."""
        return self.machine_action(machine_id, "attack", {"damage": damage})

    def turn(self, machine_id: str, direction: List[float]) -> dict:
        """Turn."""
        return self.machine_action(machine_id, "turn", {"direction": direction})

    def grab(self, machine_id: str, direction: str) -> dict:
        """Grab a resource."""
        return self.machine_action(machine_id, "grab", {"direction": direction})

    def drop(self, machine_id: str, direction: str) -> dict:
        """Drop a resource."""
        return self.machine_action(machine_id, "drop", {"direction": direction})

    def remove_machine(self, machine_id: str) -> bool:
        """Remove a machine."""
        result = self.machine_action(machine_id, "remove", {})
        return result.get("success", False)

    # ==================== Debug methods ====================

    def get_all_machines(self) -> dict:
        """Get all machines (raw format)."""
        try:
            result = self._get("/api/v1/world/debug/machines")
            return self._unwrap(result) or {}
        except requests.exceptions.Timeout:
            raise Exception(f"World Server request timeout (timeout={self.timeout}s)")
        except requests.exceptions.RequestException as e:
            raise Exception(f"World Server request failed: {e}")

    def get_all_obstacles(self) -> dict:
        """Get all obstacles (raw format)."""
        result = self._get("/api/v1/world/debug/obstacles")
        return self._unwrap(result) or {}

    def reset_world(self) -> dict:
        """Reset the world."""
        result = self._post("/api/v1/world/debug/reset")
        return self._unwrap(result) or {}

    def check_collision(self, position: List[float], size: float = 1.0, exclude_id: str = None) -> dict:
        """Simple collision check by fetching all data."""
        machines = self.get_all_machines()
        obstacles = self.get_all_obstacles()

        for m_id, m in machines.items():
            if m_id == exclude_id:
                continue
            m_pos = m["position"]
            dist = sum((a - b) ** 2 for a, b in zip(position, m_pos)) ** 0.5
            if dist < max(size, m.get("size", 1.0)) * 0.5:
                return {"collision": True}

        for obs in obstacles.values():
            obs_pos = obs["position"]
            dist = sum((a - b) ** 2 for a, b in zip(position, obs_pos)) ** 0.5
            if dist < max(size, obs.get("size", 1.0)) * 0.5:
                return {"collision": True}

        return {"collision": False}

    def health_check(self) -> bool:
        """Health check."""
        try:
            result = self._get("/health")
            return result.get("status") == "ok"
        except Exception:
            return False

    def get_machine(self, machine_id: str) -> Optional[dict]:
        """Get a single machine."""
        machines = self.get_all_machines()
        return machines.get(machine_id)


# Global client instance
world_client = WorldClient()
