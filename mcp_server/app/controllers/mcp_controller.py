# -*- coding: utf-8 -*-
"""
MCP Controller — tool listing and invocation via HTTP.

Endpoints:
  GET  /tools                    — list available tools
  POST /tools/<tool_name>/invoke — invoke a tool
"""

import sys
import os
import asyncio

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from flask import Blueprint, request

from shared.response import success_response, error_response
from shared import error_codes as EC
from shared.validation import ToolInvokeRequest

from mcp_server.app.services.mcp_service import mcp_service

mcp_bp = Blueprint("mcp", __name__, url_prefix="/api/v1/mcp")


@mcp_bp.route("/tools", methods=["GET"])
def list_tools():
    """List all available tools."""
    tools = mcp_service.list_tools()
    return success_response({"tools": tools})


@mcp_bp.route("/tools/<tool_name>/invoke", methods=["POST"])
def call_tool(tool_name):
    """Invoke a tool by name."""
    data = request.get_json() or {}

    try:
        req = ToolInvokeRequest(**data)
    except Exception as e:
        return error_response(EC.VALIDATION_ERROR, str(e))

    try:
        result = asyncio.run(mcp_service.call_tool(tool_name, req.parameters))
        return success_response({"result": result})
    except ValueError as e:
        return error_response(EC.TOOL_NOT_FOUND, str(e), 404)
    except Exception as e:
        return error_response(EC.TOOL_EXECUTION_FAILED, str(e), 500)
