#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Agent Server - Agent 管理服务

提供 Agent 的创建、查询、更新和命令执行

用法:
    python main.py          # 启动 Flask API 服务
    python main.py worker   # 启动 Celery Worker
"""

import sys
import os
import logging
import argparse

# 添加路径
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)
sys.path.insert(0, os.path.dirname(current_dir))

from flask import Flask
from flask_cors import CORS

from agent_server.app.config import config
from agent_server.app.controllers.agent_controller import agent_bp
from agent_server.app.controllers.auth_controller import auth_bp


def create_app() -> Flask:
    """创建 Flask 应用"""
    flask_app = Flask(__name__)
    CORS(flask_app)
    flask_app.register_blueprint(auth_bp)
    flask_app.register_blueprint(agent_bp)

    @flask_app.route('/health', methods=['GET'])
    def health_check():
        return {'status': 'ok', 'service': 'agent_server'}

    return flask_app


def run_server():
    """启动 Flask API 服务"""
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)

    flask_app = create_app()

    print("=" * 50)
    print("👤 Agent Server - Agent 管理服务")
    print("=" * 50)
    print(f"📡 地址: http://{config.HOST}:{config.PORT}")
    print(f"🔧 MCP Server: {config.MCP_SERVER_URL}")
    print(f"🌍 World Server: {config.WORLD_SERVER_URL}")
    print("\n📋 API:")
    print("  🔐 认证相关:")
    print("    POST   /api/auth/register    - 注册用户，获取 API Key")
    print("    POST   /api/auth/verify      - 验证 API Key")
    print("  👤 Agent 管理:")
    print("    POST   /api/agent            - 创建 Agent (需要 API Key)")
    print("    GET    /api/agent/<id>       - 获取 Agent 信息 (需要 API Key)")
    print("    PUT    /api/agent/<id>       - 更新 Agent 信息 (需要 API Key)")
    print("    POST   /api/agent/<id>/command - 发送命令 (需要 API Key)")
    print("    DELETE /api/agent/<id>       - 删除 Agent (需要 API Key)")
    print("    GET    /api/agent            - 获取所有 Agent (需要 API Key)")
    print("=" * 50)
    print("\n⚠️  请先启动依赖服务:")
    print("   cd world_server && python main.py")
    print("   python -m mcp_server.main")
    print("   python main.py worker  # 启动 Celery Worker\n")
    print("✅ 服务已启动\n")

    flask_app.run(host=config.HOST, port=config.PORT, debug=False)


def run_worker():
    """启动 Celery Worker"""
    from agent_server.app.services.tasks import celery_app

    print("=" * 50)
    print("🔄 Celery Worker - 异步任务处理")
    print("=" * 50)
    print(f"📡 Broker: {config.CELERY_BROKER_URL}")
    print(f"📦 Backend: {config.CELERY_RESULT_BACKEND}")
    print("✅ Worker 已启动\n")

    celery_app.worker_main(['worker', '--loglevel=info'])


def main():
    """主入口"""
    parser = argparse.ArgumentParser(description='Agent Server')
    parser.add_argument(
        'mode',
        nargs='?',
        default='server',
        choices=['server', 'worker'],
        help='运行模式: server (默认) 或 worker'
    )

    args = parser.parse_args()

    if args.mode == 'worker':
        run_worker()
    else:
        run_server()


if __name__ == '__main__':
    main()

