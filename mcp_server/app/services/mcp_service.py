# -*- coding: utf-8 -*-
"""
MCP Service — tool management service.

Wraps FastMCP, provides tool registration and invocation.
Tools are distinguished by naming convention: human_* and machine_*.
"""

import json
import sys
import os
from typing import Any, Dict, List, Optional
from inspect import Parameter, Signature

# 添加项目根目录
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from mcp.server.fastmcp import FastMCP
from app.tool.base import BaseTool
from app.tool.machine_tools import (
    CheckEnvironmentTool, StepMovementTool,
    LaserAttackTool, GetSelfStatusTool,
    GrabResourceTool, DropResourceTool
)
from app.tool.human_tools import (
    ListMachinesTool, GetWorldViewTool,
    SendShortCommandTool, SendLongCommandTool,
)


class MCPService:
    """MCP tool management service."""

    _instance: Optional["MCPService"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, 'initialized'):
            return

        self._server = FastMCP("openmanus")
        self._tools: Dict[str, BaseTool] = {}

        # Register tools
        self._register_default_tools()
        self.initialized = True

    def _register_default_tools(self):
        """Register default tools."""
        # Human tools
        human_tools = [
            ListMachinesTool(),
            GetWorldViewTool(),
            SendShortCommandTool(),
            SendLongCommandTool(),
        ]
        for tool in human_tools:
            self.register_tool(tool)

        # Machine tools
        machine_tools = [
            CheckEnvironmentTool(),
            StepMovementTool(),
            LaserAttackTool(),
            GetSelfStatusTool(),
            GrabResourceTool(),
            DropResourceTool(),
        ]
        for tool in machine_tools:
            self.register_tool(tool)

    def register_tool(self, tool: BaseTool) -> None:
        """Register a tool."""
        self._tools[tool.name] = tool

        async def tool_method(t=tool, **kwargs):
            result = await t.execute(**kwargs)
            if hasattr(result, "model_dump"):
                return json.dumps(result.model_dump())
            elif isinstance(result, dict):
                return json.dumps(result)
            return str(result)

        tool_param = tool.to_param()
        tool_func = tool_param["function"]

        tool_method.__name__ = tool.name
        tool_method.__doc__ = tool_func.get("description", "")
        tool_method.__signature__ = self._build_signature(tool_func)

        self._server.tool()(tool_method)

    def _build_signature(self, tool_func: dict) -> Signature:
        """Build function signature from tool schema."""
        props = tool_func.get("parameters", {}).get("properties", {})
        required = tool_func.get("parameters", {}).get("required", [])

        type_map = {
            "string": str, "integer": int, "number": float,
            "boolean": bool, "object": dict, "array": list
        }

        params = []
        for name, details in props.items():
            params.append(Parameter(
                name=name,
                kind=Parameter.KEYWORD_ONLY,
                default=Parameter.empty if name in required else None,
                annotation=type_map.get(details.get("type", ""), Any),
            ))
        return Signature(parameters=params)

    def list_tools(self) -> List[dict]:
        """Get the list of available tools."""
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.parameters
            }
            for tool in self._tools.values()
        ]

    async def call_tool(self, tool_name: str, parameters: dict) -> Any:
        """Invoke a tool by name."""
        if tool_name not in self._tools:
            raise ValueError(f"Tool '{tool_name}' not found")

        tool = self._tools[tool_name]
        result = await tool.execute(**parameters)

        if hasattr(result, "output") and result.output:
            return result.output
        if hasattr(result, "error") and result.error:
            raise Exception(result.error)
        return str(result)

    def get_fastmcp_server(self) -> FastMCP:
        """Get the underlying FastMCP server instance."""
        return self._server


# 全局实例
mcp_service = MCPService()
