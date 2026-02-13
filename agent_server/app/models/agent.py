# -*- coding: utf-8 -*-
"""Agent 数据模型"""

from typing import Dict, List, Optional
from dataclasses import dataclass, field


@dataclass
class AgentInfo:
    """Agent 基础信息"""
    agent_id: str
    agent_type: str  # "human" 或 "machine"
    status: str = "active"
    metadata: Dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "agent_id": self.agent_id,
            "agent_type": self.agent_type,
            "status": self.status,
            "metadata": self.metadata
        }


@dataclass
class HumanInfo(AgentInfo):
    """Human Agent 信息"""
    machine_ids: List[str] = field(default_factory=list)

    def __post_init__(self):
        self.agent_type = "human"

    def to_dict(self) -> dict:
        result = super().to_dict()
        result["machine_ids"] = self.machine_ids
        return result


@dataclass
class MachineInfo:
    """Machine Agent 信息"""
    agent_id: str
    owner_id: str  # 所属 Human ID
    position: List[float] = field(default_factory=lambda: [0, 0, 0])
    life_value: int = 10
    status: str = "active"
    metadata: Dict = field(default_factory=dict)

    @property
    def agent_type(self) -> str:
        return "machine"

    def to_dict(self) -> dict:
        return {
            "agent_id": self.agent_id,
            "agent_type": "machine",
            "owner_id": self.owner_id,
            "position": self.position,
            "life_value": self.life_value,
            "status": self.status,
            "metadata": self.metadata
        }
