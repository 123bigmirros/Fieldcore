# -*- coding: utf-8 -*-
"""
Machine Tools - 机器人工具

通过 HTTP 调用 world_server 微服务
"""

import json
from typing import List

from app.service.world_client import world_client
from app.tool.base import BaseTool, ToolResult


class CheckEnvironmentTool(BaseTool):
    """环境检测工具"""

    name: str = "machine_check_environment"
    description: str = "检查周围环境，获取视野内的信息"
    parameters: dict = {
        "type": "object",
        "properties": {
            "machine_id": {
                "type": "string",
                "description": "机器人ID",
                },
        },
        "required": ["machine_id"],
    }

    async def execute(self, machine_id: str, **kwargs) -> ToolResult:
        """获取机器人视野"""
        try:
            view = world_client.get_machine_view(machine_id)
            if not view:
                return ToolResult(error=f"机器人 {machine_id} 不存在")
            return ToolResult(output=json.dumps(view, indent=2, ensure_ascii=False))
        except Exception as e:
            return ToolResult(error=f"环境检测失败: {str(e)}")


class StepMovementTool(BaseTool):
    """移动工具"""

    name: str = "machine_step_movement"
    description: str = "移动机器人。方向: 东[1,0,0], 北[0,1,0], 西[-1,0,0], 南[0,-1,0]"
    parameters: dict = {
        "type": "object",
        "properties": {
            "machine_id": {"type": "string", "description": "机器人ID"},
            "direction": {"type": "array", "items": {"type": "number"}, "description": "方向向量"},
            "distance": {"type": "number", "description": "移动距离"},
        },
        "required": ["machine_id", "direction", "distance"],
    }

    async def execute(self, machine_id: str, direction: List[float], distance: float, **kwargs) -> ToolResult:
        """执行移动"""
        try:
            result = world_client.move(machine_id, direction, distance)
            if result.get('success'):
                return ToolResult(output=json.dumps(result['result'], ensure_ascii=False))
            return ToolResult(error=result.get('error', 'Move failed'))
        except Exception as e:
            return ToolResult(error=f"移动失败: {str(e)}")


class LaserAttackTool(BaseTool):
    """激光攻击工具"""

    name: str = "machine_laser_attack"
    description: str = "沿当前朝向发射激光攻击"
    parameters: dict = {
        "type": "object",
        "properties": {
            "machine_id": {"type": "string", "description": "机器人ID"},
            "damage": {"type": "number", "description": "伤害值", "default": 1},
        },
        "required": ["machine_id"],
    }

    async def execute(self, machine_id: str, damage: int = 1, **kwargs) -> ToolResult:
        """执行攻击"""
        try:
            result = world_client.attack(machine_id, damage)
            if result.get('success'):
                return ToolResult(output=json.dumps(result['result'], indent=2, ensure_ascii=False))
            return ToolResult(error=result.get('error', 'Attack failed'))
        except Exception as e:
            return ToolResult(error=f"攻击失败: {str(e)}")


class GetSelfStatusTool(BaseTool):
    """获取自身状态"""

    name: str = "machine_get_self_status"
    description: str = "获取机器人自身状态"
    parameters: dict = {
        "type": "object",
        "properties": {
            "machine_id": {"type": "string", "description": "机器人ID"},
        },
        "required": ["machine_id"],
    }

    async def execute(self, machine_id: str, **kwargs) -> ToolResult:
        """获取状态"""
        try:
            machine = world_client.get_machine(machine_id)
            if not machine:
                return ToolResult(error=f"机器人 {machine_id} 不存在")
            return ToolResult(output=json.dumps(machine, indent=2, ensure_ascii=False))
        except Exception as e:
            return ToolResult(error=f"获取状态失败: {str(e)}")
