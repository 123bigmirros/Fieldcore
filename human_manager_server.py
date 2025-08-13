#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Human管理服务器 - 简单封装test_human_machine_lineup_simple.py的逻辑
"""

import asyncio
import json
import sys
import os
import threading

# 确保正确的Python路径 - 与test_human_machine_lineup_simple.py一致
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, jsonify, request
from flask_cors import CORS
from app.logger import logger
import random

# 全局human管理器和事件循环
HUMAN_MANAGERS = {}  # human_id -> HumanAgent
GLOBAL_LOOP = None
LOOP_THREAD = None

async def find_random_valid_position(human_agent, max_attempts=50):
    """在地图范围内找到一个合法的随机位置"""
    # 地图范围：-14 到 14（避开边界墙）
    map_range = 14

    for _ in range(max_attempts):
        # 生成随机坐标
        x = random.randint(-map_range + 1, map_range - 1)
        y = random.randint(-map_range + 1, map_range - 1)
        position = [float(x), float(y), 0.0]

        # 检查位置是否合法（无碰撞）
        try:
            result = await human_agent.call_tool("mcp_python_check_collision",
                                               position=position, size=1.0)

            # 解析检查结果
            if hasattr(result, 'output'):
                import json
                collision_data = json.loads(result.output)
                if not collision_data.get('collision', True):  # 无碰撞
                    return position
        except Exception as e:
            logger.warning(f"位置检查失败 {position}: {e}")
            continue

    logger.error(f"尝试了 {max_attempts} 次都无法找到合法位置")
    return None

def run_async_task(coro):
    """在全局事件循环中运行异步任务"""
    future = asyncio.run_coroutine_threadsafe(coro, GLOBAL_LOOP)
    return future.result()

def start_event_loop():
    """启动全局事件循环"""
    global GLOBAL_LOOP
    GLOBAL_LOOP = asyncio.new_event_loop()
    asyncio.set_event_loop(GLOBAL_LOOP)
    GLOBAL_LOOP.run_forever()

def create_app():
    """创建Flask应用"""
    global LOOP_THREAD

    # 启动专用的事件循环线程
    if LOOP_THREAD is None:
        LOOP_THREAD = threading.Thread(target=start_event_loop, daemon=True)
        LOOP_THREAD.start()
        # 等待事件循环启动
        import time
        time.sleep(0.1)

    app = Flask(__name__)
    CORS(app)

    @app.route('/api/humans', methods=['POST'])
    def create_human():
        """创建human和指定数量的machine"""
        try:
            data = request.get_json()
            human_id = data.get('human_id')
            machine_count = data.get('machine_count', 3)

            if not human_id:
                return jsonify({'error': 'human_id is required'}), 400

            if human_id in HUMAN_MANAGERS:
                return jsonify({'error': f'Human {human_id} already exists'}), 400

            # 使用与test_human_machine_lineup_simple.py完全相同的逻辑
            from app.agent.human import create_human_commander

            async def create_human_with_machines():
                # 创建Human Agent（不自动创建机器人）
                human = await create_human_commander(
                    human_id=human_id,
                    machine_count=0,  # 不让Human Agent自动创建机器人
                    mcp_connection_params={
                        "connection_type": "http_api",
                        "server_url": "http://localhost:8003"
                    }
                )

                # 在随机位置创建机器人
                created_machines = []
                for i in range(machine_count):
                    machine_id = f"{human_id}_robot_{i+1:02d}"

                    # 找到合法的随机位置
                    position = await find_random_valid_position(human)
                    if position:
                        success = await human.create_machine_at_position(machine_id, position)
                        if success:
                            created_machines.append(machine_id)
                            logger.info(f"🤖 为 {human_id} 创建机器人 {machine_id} 在位置 {position}")
                        else:
                            logger.warning(f"⚠️ 机器人 {machine_id} 创建失败")
                    else:
                        logger.warning(f"⚠️ 无法为机器人 {machine_id} 找到合法位置")

                # 注册成功创建的机器人到MCP控制系统
                for machine_id in created_machines:
                    await human.call_tool("mcp_python_register_machine_control", machine_id=machine_id)
                    logger.info(f"✅ 注册机器人 {machine_id} 到MCP控制系统 (owner: {human_id})")

                return human, len(created_machines)

            human, actual_count = run_async_task(create_human_with_machines())
            HUMAN_MANAGERS[human_id] = human

            return jsonify({
                'status': 'success',
                'human_id': human_id,
                'requested_count': machine_count,
                'actual_count': actual_count,
                'message': f'Human {human_id} created with {actual_count}/{machine_count} machines at random positions'
            })

        except Exception as e:
            logger.error(f"创建Human失败: {e}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/humans/<human_id>', methods=['DELETE'])
    def delete_human(human_id):
        """删除指定human及其machines"""
        try:
            if human_id not in HUMAN_MANAGERS:
                return jsonify({'error': f'Human {human_id} not found'}), 404

            human = HUMAN_MANAGERS[human_id]

            # 清理Human Agent（机器人现在由MCP服务器管理，无需清理）
            async def cleanup_human_async():
                # Human Agent的清理逻辑
                await human.cleanup()

            run_async_task(cleanup_human_async())

            # 从管理器中移除
            del HUMAN_MANAGERS[human_id]

            return jsonify({
                'status': 'success',
                'message': f'Human {human_id} and all machines deleted'
            })

        except Exception as e:
            logger.error(f"删除Human失败: {e}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/humans/<human_id>/command', methods=['POST'])
    def send_command_to_human(human_id):
        """向指定human发送命令 - 使用与test_human_machine_lineup_simple.py相同的逻辑"""
        try:
            if human_id not in HUMAN_MANAGERS:
                return jsonify({'error': f'Human {human_id} not found'}), 404

            data = request.get_json()
            command = data.get('command')

            if not command:
                return jsonify({'error': 'command is required'}), 400

            human = HUMAN_MANAGERS[human_id]

            # 直接使用human.run()，就像test_human_machine_lineup_simple.py中那样
            async def execute_command_async():
                result = await human.run(command)
                return result

            result = run_async_task(execute_command_async())

            return jsonify({
                'status': 'success',
                'human_id': human_id,
                'command': command,
                'result': result
            })

        except Exception as e:
            logger.error(f"发送命令失败: {e}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/humans', methods=['GET'])
    def list_humans():
        """获取所有human列表"""
        try:
            humans_info = {}
            for human_id, human in HUMAN_MANAGERS.items():
                humans_info[human_id] = {
                    'human_id': human_id,
                    'current_task': human.current_task,
                    'message': 'Machines are managed by MCP server'
                }

            return jsonify({
                'status': 'success',
                'humans': humans_info
            })

        except Exception as e:
            logger.error(f"获取Human列表失败: {e}")
            return jsonify({'error': str(e)}), 500

    # 机器人控制回调端点已移除 - 现在由MCP服务器直接管理Machine Agent

    @app.route('/health', methods=['GET'])
    def health_check():
        """健康检查"""
        return jsonify({
            'status': 'ok',
            'service': 'human_manager',
            'humans_count': len(HUMAN_MANAGERS)
        })

    return app

if __name__ == "__main__":
    app = create_app()

    print("🚀 启动Human管理服务器...")
    print("📡 Human管理API地址: http://localhost:8004")
    print("🔗 连接到MCP服务器: http://localhost:8003")
    print("\n💡 可用接口:")
    print("  POST   /api/humans                                    - 创建Human")
    print("  DELETE /api/humans/<human_id>                         - 删除Human")
    print("  POST   /api/humans/<human_id>/command                 - 发送命令")
    print("  GET    /api/humans                                    - 获取Human列表")
    print("  POST   /api/humans/<human_id>/machines/<machine_id>/control - 机器人控制回调")
    print("  GET    /health                                        - 健康检查")
    print("\n✅ Human管理服务器启动成功")

    # 启动服务器
    app.run(host='0.0.0.0', port=8004, debug=False)
