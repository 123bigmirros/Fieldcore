# -*- coding: utf-8 -*-
"""
Human Manager - Human Agent Management

Responsible for creating, querying, deleting, and executing commands for Human Agents.
"""

import sys
import os

# Add project root directory
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from threading import Lock
from typing import Dict, List, Optional, Tuple

from app.agent.human import HumanAgent
from app.logger import logger

import asyncio

from ..config import config
from ..models.agent import HumanInfo


class HumanManager:
    """Human Agent Manager - Singleton"""

    _instance = None
    _lock = Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, '_initialized'):
            return

        self._humans: Dict[str, HumanAgent] = {}
        self._human_machines: Dict[str, List[str]] = {}  # human_id -> [machine_id, ...]
        self._data_lock = Lock()
        self._initialized = True

    def create(self, human_id: str, machine_count: int = 3) -> Tuple[bool, str]:
        """
        Create a Human Agent

        Args:
            human_id: Human ID
            machine_count: Number of robots

        Returns:
            (success, error_message)
        """
        with self._data_lock:
            if human_id in self._humans:
                return False, f"Human {human_id} already exists"

            try:
                human = HumanAgent(
                    human_id=human_id,
                    machine_count=machine_count
                )

                asyncio.run(human.initialize(
                    connection_type="http_api",
                    server_url=config.MCP_SERVER_URL
                ))

                self._humans[human_id] = human
                self._human_machines[human_id] = []

                logger.info(f"Human {human_id} created successfully")
                return True, ""

            except Exception as e:
                logger.error(f"Failed to create Human: {e}")
                return False, str(e)

    def get(self, human_id: str) -> Optional[HumanAgent]:
        """Get a Human Agent instance"""
        with self._data_lock:
            return self._humans.get(human_id)

    def get_info(self, human_id: str) -> Optional[dict]:
        """Get Human information"""
        with self._data_lock:
            if human_id not in self._humans:
                return None

            return HumanInfo(
                agent_id=human_id,
                agent_type="human",
                machine_ids=self._human_machines.get(human_id, [])
            ).to_dict()

    def get_all(self) -> Dict[str, dict]:
        """Get all Human information"""
        with self._data_lock:
            result = {}
            # Build info directly to avoid deadlock from calling get_info()
            for human_id in self._humans:
                result[human_id] = HumanInfo(
                    agent_id=human_id,
                    agent_type="human",
                    machine_ids=self._human_machines.get(human_id, [])
                ).to_dict()
            return result

    def exists(self, human_id: str) -> bool:
        """Check if a Human exists"""
        with self._data_lock:
            return human_id in self._humans

    def delete(self, human_id: str) -> Tuple[bool, str]:
        """Delete a Human Agent"""
        with self._data_lock:
            if human_id not in self._humans:
                return False, f"Human {human_id} not found"

            try:
                human = self._humans[human_id]
                asyncio.run(human.cleanup())

                del self._humans[human_id]

                # Return the list of associated machines for external handling
                machine_ids = self._human_machines.pop(human_id, [])

                logger.info(f"Human {human_id} deleted")
                return True, ""

            except Exception as e:
                logger.error(f"Failed to delete Human: {e}")
                return False, str(e)

    def send_command(self, human_id: str, command: str) -> Tuple[bool, str]:
        """Send a command to a Human"""
        with self._data_lock:
            if human_id not in self._humans:
                return False, f"Human {human_id} not found"

            try:
                human = self._humans[human_id]
                result = asyncio.run(human.run(command))
                return True, result
            except Exception as e:
                return False, str(e)

    def add_machine(self, human_id: str, machine_id: str):
        """Add a machine to the Human's management list"""
        with self._data_lock:
            if human_id in self._human_machines:
                if machine_id not in self._human_machines[human_id]:
                    self._human_machines[human_id].append(machine_id)

    def remove_machine(self, human_id: str, machine_id: str):
        """Remove a machine from the Human's management list"""
        with self._data_lock:
            if human_id in self._human_machines:
                if machine_id in self._human_machines[human_id]:
                    self._human_machines[human_id].remove(machine_id)

    def get_machines(self, human_id: str) -> List[str]:
        """Get the list of machines managed by a Human"""
        with self._data_lock:
            return self._human_machines.get(human_id, []).copy()


# Global instance
human_manager = HumanManager()
