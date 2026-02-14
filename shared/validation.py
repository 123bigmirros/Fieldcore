# -*- coding: utf-8 -*-
"""Pydantic request validation models."""

from typing import List, Optional, Tuple

from pydantic import BaseModel, Field, field_validator


class MachineRegisterRequest(BaseModel):
    """POST /api/v1/world/machines"""

    machine_id: str
    position: List[float] = Field(default=[0, 0, 0])
    owner: str = ""
    life_value: int = 10
    machine_type: str = "worker"
    size: float = 1.0
    facing_direction: List[float] = Field(default=[1.0, 0.0])
    view_size: int = 3


class MachineActionRequest(BaseModel):
    """POST /api/v1/world/machines/<machine_id>/actions"""

    action: str
    params: dict = Field(default_factory=dict)


class AgentCreateRequest(BaseModel):
    """POST /api/v1/agents"""

    agent_type: str
    agent_id: str
    owner_id: Optional[str] = None
    machine_count: int = 3
    position: Optional[List[float]] = None

    @field_validator("agent_type")
    @classmethod
    def validate_agent_type(cls, v):
        if v not in ("human", "machine"):
            raise ValueError("agent_type must be 'human' or 'machine'")
        return v


class CommandRequest(BaseModel):
    """POST /api/v1/agents/<agent_id>/commands"""

    command: str


class RegisterRequest(BaseModel):
    """POST /api/v1/auth/register"""

    metadata: Optional[dict] = None


class ToolInvokeRequest(BaseModel):
    """POST /api/v1/mcp/tools/<tool_name>/invoke"""

    parameters: dict = Field(default_factory=dict)


class AgentUpdateRequest(BaseModel):
    """PUT /api/v1/agents/<agent_id>"""

    position: Optional[List[float]] = None
    life_value: Optional[int] = None
    metadata: Optional[dict] = None
