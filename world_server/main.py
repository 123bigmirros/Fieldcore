#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
World Server - 世界管理微服务

核心 API:
- machine_register: 注册机器人
- machine_action: 处理移动、攻击等操作
- save_world: 持久化世界状态
- machine_view: 获取机器人视野
"""

import logging
from flask import Flask
from flask_cors import CORS

from app.config import config
from app.controllers.world_controller import world_bp


def create_app() -> Flask:
    """创建 Flask 应用"""
    app = Flask(__name__)
    CORS(app)

    # 注册世界控制器
    app.register_blueprint(world_bp)

    @app.route('/health', methods=['GET'])
    def health_check():
        return {'status': 'ok', 'service': 'world_server'}

    return app


def main():
    """主入口"""
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)

    app = create_app()

    print("=" * 50)
    print("🌍 World Server - 世界管理微服务")
    print("=" * 50)
    print(f"📡 地址: http://{config.HOST}:{config.PORT}")
    print("\n📋 核心 API:")
    print("  POST /api/world/machine_register  - 注册机器人")
    print("  POST /api/world/machine_action    - 执行动作")
    print("  POST /api/world/save_world        - 保存世界")
    print("  GET  /api/world/machine_view/<id> - 获取视野")
    print("\n🌐 前端数据 API:")
    print("  GET  /api/world/machines          - 获取所有机器人（前端格式）")
    print("  GET  /api/world/obstacles         - 获取所有障碍物（前端格式）")
    print("\n🔧 调试 API:")
    print("  GET  /api/world/debug/machines    - 获取所有机器人（原始格式）")
    print("  GET  /api/world/debug/obstacles   - 获取所有障碍物（原始格式）")
    print("  POST /api/world/debug/reset       - 重置世界")
    print("=" * 50)
    print("✅ 服务已启动\n")

    app.run(host=config.HOST, port=config.PORT, debug=config.DEBUG)


if __name__ == '__main__':
    main()
