# -*- coding: utf-8 -*-
"""User Data Model"""

from dataclasses import dataclass, field
from typing import Dict, Optional
from datetime import datetime


@dataclass
class User:
    """User Information"""
    user_id: str  # Unique user ID
    api_key: str  # API Key
    created_at: datetime = field(default_factory=datetime.now)
    metadata: Dict = field(default_factory=dict)
    human_id: Optional[str] = None  # Associated Human ID

    def to_dict(self) -> dict:
        return {
            "user_id": self.user_id,
            "api_key": self.api_key,
            "created_at": self.created_at.isoformat(),
            "metadata": self.metadata,
            "human_id": self.human_id
        }

