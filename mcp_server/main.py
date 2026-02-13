#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MCP Server - MCP 工具服务

提供工具列表查询和工具调用 API
"""

import sys
import os
import logging

# 添加路径
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)
sys.path.insert(0, os.path.dirname(current_dir))  # 项目根目录

from flask import Flask
from flask_cors import CORS

from mcp_server.app.config import config
from mcp_server.app.controllers.mcp_controller import mcp_bp


def create_app() -> Flask:
    """创建 Flask 应用"""
    flask_app = Flask(__name__)
    CORS(flask_app)
    flask_app.register_blueprint(mcp_bp)

    @flask_app.route('/health', methods=['GET'])
    def health_check():
        return {'status': 'ok', 'service': 'mcp_server'}

    return flask_app


def main():
    """主入口"""
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)

    flask_app = create_app()

    print("=" * 50)
    print("🔧 MCP Server - 工具服务")
    print("=" * 50)
    print(f"📡 地址: http://{config.HOST}:{config.PORT}")
    print(f"🌍 World Server: {config.WORLD_SERVER_URL}")
    print("\n📋 API:")
    print("  GET  /api/mcp/list_tools  - 获取工具列表")
    print("  POST /api/mcp/call_tool   - 调用工具")
    print("  GET  /health              - 健康检查")
    print("=" * 50)
    print("\n⚠️  请先启动 World Server:")
    print("   cd world_server && python main.py\n")
    print("✅ 服务已启动\n")

    flask_app.run(host=config.HOST, port=config.PORT, debug=False)


if __name__ == '__main__':
    main()
