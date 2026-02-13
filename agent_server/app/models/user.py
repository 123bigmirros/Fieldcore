# -*- coding: utf-8 -*-
"""用户数据模型"""

from dataclasses import dataclass, field
from typing import Dict, Optional
from datetime import datetime


@dataclass
class User:
    """用户信息"""
    user_id: str  # 唯一用户 ID
    api_key: str  # API Key
    created_at: datetime = field(default_factory=datetime.now)
    metadata: Dict = field(default_factory=dict)
    human_id: Optional[str] = None  # 关联的 Human ID

    def to_dict(self) -> dict:
        return {
            "user_id": self.user_id,
            "api_key": self.api_key,
            "created_at": self.created_at.isoformat(),
            "metadata": self.metadata,
            "human_id": self.human_id
        }

