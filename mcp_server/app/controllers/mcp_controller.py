# -*- coding: utf-8 -*-
"""
MCP Controller - MCP 工具调用控制器

提供 HTTP API:
- list_tools: 获取工具列表
- call_tool: 调用工具
"""

import asyncio
from flask import Blueprint, request, jsonify

from mcp_server.app.services.mcp_service import mcp_service

mcp_bp = Blueprint('mcp', __name__, url_prefix='/api/mcp')


@mcp_bp.route('/list_tools', methods=['GET'])
def list_tools():
    """
    获取工具列表

    Response:
        {
            "tools": [
                {
                    "name": "...",
                    "description": "...",
                    "parameters": {...}
                },
                ...
            ]
        }
    """
    tools = mcp_service.list_tools()
    return jsonify({"tools": tools})


@mcp_bp.route('/call_tool', methods=['POST'])
def call_tool():
    """
    调用工具

    Request:
        {
            "tool_name": "machine_step_movement",
            "parameters": {"machine_id": "robot_01", "direction": [1,0,0], "distance": 1}
        }

    Response:
        {"success": true, "result": "..."}
    """
    data = request.get_json()
    tool_name = data.get('tool_name')
    parameters = data.get('parameters', {})

    if not tool_name:
        return jsonify({'success': False, 'error': 'tool_name is required'}), 400

    try:
        result = asyncio.run(mcp_service.call_tool(tool_name, parameters))
        return jsonify({'success': True, 'result': result})
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 404
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
