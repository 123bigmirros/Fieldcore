# -*- coding: utf-8 -*-
"""
认证服务 - 管理用户注册和 API Key 验证
"""

import secrets
import uuid
from typing import Dict, Optional, Tuple
from threading import Lock
from datetime import datetime

from agent_server.app.models.user import User
import sys
import os
# 添加项目根目录
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from app.logger import logger


class AuthService:
    """认证服务 - 单例"""

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

        # 存储用户数据: api_key -> User
        self._users_by_key: Dict[str, User] = {}
        # user_id -> User 的映射
        self._users_by_id: Dict[str, User] = {}
        # user_id -> human_id 的映射
        self._user_human_mapping: Dict[str, str] = {}
        self._data_lock = Lock()

        self.initialized = True

    def register(self, metadata: Dict = None) -> Tuple[bool, Dict]:
        """
        注册新用户

        Args:
            metadata: 用户元数据

        Returns:
            (success, result_dict)
            result_dict 格式:
            - success=True 时: {"user_id": str, "api_key": str, ...}
            - success=False 时: {"error": str}
        """
        try:
            # 生成唯一用户 ID
            user_id = f"user_{uuid.uuid4().hex[:12]}"

            # 生成 API Key (类似 OpenAI 格式: sk-...)
            api_key = f"sk-{secrets.token_urlsafe(32)}"

            # 创建用户
            user = User(
                user_id=user_id,
                api_key=api_key,
                metadata=metadata or {}
            )

            with self._data_lock:
                self._users_by_key[api_key] = user
                self._users_by_id[user_id] = user

            logger.info(f"✅ 用户注册成功: user_id={user_id}")

            return True, {
                "user_id": user_id,
                "api_key": api_key,
                "created_at": user.created_at.isoformat(),
                "metadata": user.metadata
            }

        except Exception as e:
            logger.error(f"注册用户失败: {e}")
            return False, {"error": str(e)}

    def verify_api_key(self, api_key: str) -> Tuple[bool, Optional[str]]:
        """
        验证 API Key

        Args:
            api_key: API Key

        Returns:
            (is_valid, user_id) - 如果有效返回 user_id，否则返回 None
        """
        if not api_key:
            return False, None

        with self._data_lock:
            user = self._users_by_key.get(api_key)
            if user:
                return True, user.user_id

        return False, None

    def get_user_by_id(self, user_id: str) -> Optional[User]:
        """根据 user_id 获取用户信息"""
        with self._data_lock:
            return self._users_by_id.get(user_id)

    def get_user_by_api_key(self, api_key: str) -> Optional[User]:
        """根据 api_key 获取用户信息"""
        with self._data_lock:
            return self._users_by_key.get(api_key)

    def set_user_human_mapping(self, user_id: str, human_id: str) -> bool:
        """
        建立 user_id 和 human_id 的映射关系

        Args:
            user_id: 用户 ID
            human_id: Human Agent ID

        Returns:
            是否设置成功
        """
        with self._data_lock:
            if user_id not in self._users_by_id:
                return False

            self._user_human_mapping[user_id] = human_id
            self._users_by_id[user_id].human_id = human_id
            logger.info(f"✅ 建立映射: user_id={user_id} -> human_id={human_id}")
            return True

    def get_human_id_by_user_id(self, user_id: str) -> Optional[str]:
        """根据 user_id 获取关联的 human_id"""
        with self._data_lock:
            return self._user_human_mapping.get(user_id)

    def get_user_id_by_human_id(self, human_id: str) -> Optional[str]:
        """根据 human_id 获取关联的 user_id"""
        with self._data_lock:
            for uid, hid in self._user_human_mapping.items():
                if hid == human_id:
                    return uid
            return None


# 全局实例
auth_service = AuthService()

