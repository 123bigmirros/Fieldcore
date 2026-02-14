# -*- coding: utf-8 -*-
"""
Agent Service - Agent Management Service Facade

Provides a unified external interface for Agent (Human/Machine) management.
Internally delegates to HumanManager and MachineManager.
"""

from threading import Lock
from typing import Dict, List, Optional, Tuple

from app.logger import logger

from .human_manager import human_manager
from .machine_manager import machine_manager


class AgentService:
    """
    Agent Management Service - Facade Pattern

    Provides a unified Agent management interface, internally delegating
    to specialized Managers.
    """

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
        self._initialized = True

    # ==================== Unified Creation Interface ====================

    def create_agent(
        self,
        agent_type: str,
        agent_id: str,
        owner_id: str = None,
        machine_count: int = 3,
        position: List[float] = None,
        user_id: str = None
    ) -> Tuple[bool, dict]:
        """
        Unified Agent creation interface

        Args:
            agent_type: Agent type ("human" or "machine")
            agent_id: Agent ID
            owner_id: Owning Human ID (required for machine)
            machine_count: Number of robots (optional for human, default 3)
            position: Position coordinates (optional for machine)
            user_id: User ID (optional, used to establish mapping)

        Returns:
            (success, result_dict)
        """
        if not agent_type or not agent_id:
            return False, {"error": "agent_type and agent_id are required"}

        if agent_type == "human":
            return self._create_human_with_machines(agent_id, machine_count, user_id)

        elif agent_type == "machine":
            if not owner_id:
                return False, {"error": "owner_id is required for machine"}
            return self._create_machine(agent_id, owner_id, position)

        else:
            return False, {"error": f"Invalid agent_type: {agent_type}"}

    def _create_human_with_machines(
        self,
        human_id: str,
        machine_count: int,
        user_id: str = None
    ) -> Tuple[bool, dict]:
        """Create a Human and its subordinate machines"""
        # Create Human
        success, error = human_manager.create(human_id, machine_count)
        if not success:
            return False, {"error": error}

        # Establish user_id mapping
        if user_id:
            self._set_user_human_mapping(user_id, human_id)

        # Create machines
        actual_count = 0
        for i in range(machine_count):
            machine_id = f"{human_id}_robot_{i+1:02d}"
            m_success, m_error = machine_manager.create(machine_id, human_id)
            if m_success:
                human_manager.add_machine(human_id, machine_id)
                actual_count += 1
            else:
                logger.warning(f"Robot {machine_id} creation failed: {m_error}")

        return True, {
            "agent_id": human_id,
            "agent_type": "human",
            "machine_count": actual_count
        }

    def _create_machine(
        self,
        machine_id: str,
        owner_id: str,
        position: List[float] = None
    ) -> Tuple[bool, dict]:
        """Create a single machine"""
        if not human_manager.exists(owner_id):
            return False, {"error": f"Owner {owner_id} not found"}

        success, error = machine_manager.create(machine_id, owner_id, position)
        if not success:
            return False, {"error": error}

        human_manager.add_machine(owner_id, machine_id)

        return True, {
            "agent_id": machine_id,
            "agent_type": "machine",
            "owner_id": owner_id
        }

    def _set_user_human_mapping(self, user_id: str, human_id: str):
        """Establish mapping between user_id and human_id"""
        try:
            from .auth_service import auth_service
            auth_service.set_user_human_mapping(user_id, human_id)
        except Exception as e:
            logger.warning(f"Failed to establish user_id to human_id mapping: {e}")

    # ==================== Query Interface ====================

    def get_agent_info(self, agent_id: str) -> Optional[dict]:
        """Get Agent information"""
        # Check Human first
        info = human_manager.get_info(agent_id)
        if info:
            return info

        # Then check Machine
        return machine_manager.get_info(agent_id)

    def get_all_agents(self) -> Dict[str, dict]:
        """Get all Agent information"""
        from app.logger import logger
        logger.info("Starting to retrieve all Agent information")
        result = {}
        try:
            logger.info("Retrieving all Human information")
            human_result = human_manager.get_all()
            result.update(human_result)
            logger.info(f"Retrieved {len(human_result)} Human(s)")
        except Exception as e:
            logger.error(f"Failed to retrieve Human information: {e}", exc_info=True)

        try:
            logger.info("Retrieving all Machine information")
            machines = machine_manager.get_all()
            result.update(machines)
            logger.info(f"Retrieved {len(machines)} Machine(s)")
        except Exception as e:
            logger.error(f"Failed to retrieve Machine information: {e}", exc_info=True)

        logger.info(f"Total of {len(result)} Agent(s) retrieved")
        return result

    # ==================== Update Interface ====================

    def update_agent_info(self, agent_id: str, updates: dict) -> Tuple[bool, str]:
        """Update Agent information"""
        # Human update
        if human_manager.exists(agent_id):
            # Human currently only supports metadata updates
            return True, ""

        # Machine update
        if machine_manager.exists(agent_id):
            if 'position' in updates:
                success, error = machine_manager.update_position(agent_id, updates['position'])
                if not success:
                    return False, error

            if 'life_value' in updates:
                info = machine_manager.get_info(agent_id)
                if info:
                    current_life = info.get('life_value', 10)
                    change = updates['life_value'] - current_life
                    machine_manager.update_life(agent_id, change)

            return True, ""

        return False, f"Agent {agent_id} not found"

    # ==================== Command Execution ====================

    def send_command(self, agent_id: str, command: str) -> Tuple[bool, str]:
        """Send a command to an Agent"""
        # Human command
        if human_manager.exists(agent_id):
            return human_manager.send_command(agent_id, command)

        # # Machine command
        # if machine_manager.exists(agent_id):
        #     return machine_manager.send_command(agent_id, command)

        return False, f"Agent {agent_id} not found"

    # ==================== Delete Interface ====================

    def delete_agent(self, agent_id: str) -> Tuple[bool, str]:
        """Delete an Agent"""
        # Human deletion
        if human_manager.exists(agent_id):
            # First get the list of associated machines
            machine_ids = human_manager.get_machines(agent_id)

            # Delete all associated machines
            for m_id in machine_ids:
                machine_manager.delete(m_id)

            # Delete Human
            return human_manager.delete(agent_id)

        # Machine deletion
        if machine_manager.exists(agent_id):
            # Remove from the owning Human's list
            info = machine_manager.get_info(agent_id)
            if info:
                owner_id = info.get('owner_id')
                if owner_id:
                    human_manager.remove_machine(owner_id, agent_id)

            return machine_manager.delete(agent_id)

        return False, f"Agent {agent_id} not found"

    # ==================== Legacy Interface Compatibility ====================

    def create_human(self, human_id: str, machine_count: int = 3, user_id: str = None) -> Tuple[bool, str, int]:
        """Create a Human Agent (legacy interface compatibility)"""
        success, result = self._create_human_with_machines(human_id, machine_count, user_id)
        if success:
            return True, human_id, result.get('machine_count', 0)
        return False, result.get('error', 'Unknown error'), 0

    def create_machine(self, machine_id: str, owner_id: str, position: List[float] = None) -> Tuple[bool, str]:
        """Create a Machine Agent (legacy interface compatibility)"""
        success, result = self._create_machine(machine_id, owner_id, position)
        if success:
            return True, ""
        return False, result.get('error', 'Unknown error')


# Global instance
agent_service = AgentService()
