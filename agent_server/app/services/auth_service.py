# -*- coding: utf-8 -*-
"""
Authentication Service - Manages user registration and API Key verification
"""

import secrets
import uuid
from typing import Dict, Optional, Tuple
from threading import Lock
from datetime import datetime

from agent_server.app.models.user import User
import sys
import os
# Add project root directory
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from app.logger import logger


class AuthService:
    """Authentication Service - Singleton"""

    _instance: Optional["AuthService"] = None
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

        # Store user data: api_key -> User
        self._users_by_key: Dict[str, User] = {}
        # user_id -> User mapping
        self._users_by_id: Dict[str, User] = {}
        # user_id -> human_id mapping
        self._user_human_mapping: Dict[str, str] = {}
        self._data_lock = Lock()

        self.initialized = True

    def register(self, metadata: Dict = None) -> Tuple[bool, Dict]:
        """
        Register a new user

        Args:
            metadata: User metadata

        Returns:
            (success, result_dict)
            result_dict format:
            - success=True: {"user_id": str, "api_key": str, ...}
            - success=False: {"error": str}
        """
        try:
            # Generate unique user ID
            user_id = f"user_{uuid.uuid4().hex[:12]}"

            # Generate API Key (similar to OpenAI format: sk-...)
            api_key = f"sk-{secrets.token_urlsafe(32)}"

            # Create user
            user = User(
                user_id=user_id,
                api_key=api_key,
                metadata=metadata or {}
            )

            with self._data_lock:
                self._users_by_key[api_key] = user
                self._users_by_id[user_id] = user

            logger.info(f"User registered successfully: user_id={user_id}")

            return True, {
                "user_id": user_id,
                "api_key": api_key,
                "created_at": user.created_at.isoformat(),
                "metadata": user.metadata
            }

        except Exception as e:
            logger.error(f"Failed to register user: {e}")
            return False, {"error": str(e)}

    def verify_api_key(self, api_key: str) -> Tuple[bool, Optional[str]]:
        """
        Verify an API Key

        Args:
            api_key: API Key

        Returns:
            (is_valid, user_id) - Returns user_id if valid, otherwise None
        """
        if not api_key:
            return False, None

        with self._data_lock:
            user = self._users_by_key.get(api_key)
            if user:
                return True, user.user_id

        return False, None

    def get_user_by_id(self, user_id: str) -> Optional[User]:
        """Get user information by user_id"""
        with self._data_lock:
            return self._users_by_id.get(user_id)

    def get_user_by_api_key(self, api_key: str) -> Optional[User]:
        """Get user information by api_key"""
        with self._data_lock:
            return self._users_by_key.get(api_key)

    def set_user_human_mapping(self, user_id: str, human_id: str) -> bool:
        """
        Establish mapping between user_id and human_id

        Args:
            user_id: User ID
            human_id: Human Agent ID

        Returns:
            Whether the mapping was set successfully
        """
        with self._data_lock:
            if user_id not in self._users_by_id:
                return False

            self._user_human_mapping[user_id] = human_id
            self._users_by_id[user_id].human_id = human_id
            logger.info(f"Mapping established: user_id={user_id} -> human_id={human_id}")
            return True

    def get_human_id_by_user_id(self, user_id: str) -> Optional[str]:
        """Get the associated human_id by user_id"""
        with self._data_lock:
            return self._user_human_mapping.get(user_id)

    def get_user_id_by_human_id(self, human_id: str) -> Optional[str]:
        """Get the associated user_id by human_id"""
        with self._data_lock:
            for uid, hid in self._user_human_mapping.items():
                if hid == human_id:
                    return uid
            return None


# Global instance
auth_service = AuthService()

