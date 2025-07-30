# coding: utf-8
# A shortcut to launch OpenManus MCP server, where its introduction also solves other import issues.
import asyncio
import threading
import time
from flask import Flask, jsonify
from flask_cors import CORS
from app.mcp.server import MCPServer, parse_args


def create_http_server(world_manager, mcp_server):
    """创建HTTP服务器"""
    app = Flask(__name__)
    CORS(app)

    # MCP工具调用端点
    @app.route('/mcp/call_tool', methods=['POST'])
    def call_tool():
        """调用MCP工具"""
        from flask import request, jsonify
        import json

        try:
            data = request.get_json()
            tool_name = data.get('tool_name')
            parameters = data.get('parameters', {})

            if not tool_name:
                return jsonify({'error': 'tool_name is required'}), 400

            # 调用MCP服务器的工具
            result = asyncio.run(mcp_server.server.call_tool(tool_name, parameters))

            # 处理返回值序列化
            if hasattr(result, 'content'):
                # 如果是TextContent对象，提取文本内容
                content_str = ""
                for content in result.content:
                    if hasattr(content, 'text'):
                        content_str += content.text
                return jsonify({'result': content_str})
            else:
                return jsonify({'result': str(result)})

        except Exception as e:
            return jsonify({'error': str(e)}), 500

    # 获取工具列表端点
    @app.route('/mcp/list_tools', methods=['GET'])
    def list_tools():
        """获取可用工具列表"""
        try:
            # 返回基本的工具列表
            tools = [
                {
                    'name': 'register_machine',
                    'description': 'Register a new machine in the world',
                    'parameters': {
                        'type': 'object',
                        'properties': {
                            'machine_id': {'type': 'string'},
                            'position': {'type': 'array', 'items': {'type': 'number'}},
                            'life_value': {'type': 'integer'},
                            'machine_type': {'type': 'string'}
                        }
                    }
                },
                {
                    'name': 'movement',
                    'description': 'Move a machine to a new position',
                    'parameters': {
                        'type': 'object',
                        'properties': {
                            'machine_id': {'type': 'string'},
                            'coordinates': {'type': 'array', 'items': {'type': 'number'}},
                            'relative': {'type': 'boolean'}
                        }
                    }
                },
                {
                    'name': 'get_all_machines',
                    'description': 'Get all machines in the world',
                    'parameters': {
                        'type': 'object',
                        'properties': {}
                    }
                },
                {
                    'name': 'get_machine_info',
                    'description': 'Get information about a specific machine',
                    'parameters': {
                        'type': 'object',
                        'properties': {
                            'machine_id': {'type': 'string'}
                        }
                    }
                },
                {
                    'name': 'get_machine_commands',
                    'description': 'Get commands for a specific machine',
                    'parameters': {
                        'type': 'object',
                        'properties': {
                            'machine_id': {'type': 'string'}
                        }
                    }
                },
                {
                    'name': 'remove_machine',
                    'description': 'Remove a machine from the world',
                    'parameters': {
                        'type': 'object',
                        'properties': {
                            'machine_id': {'type': 'string'}
                        }
                    }
                }
            ]
            return jsonify({'tools': tools})
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/mcp/machines', methods=['GET'])
    def get_machines():
        """获取所有机器信息"""
        try:
            machines = world_manager.get_all_machines()
            result = {}
            for machine_id, machine_info in machines.items():
                result[machine_id] = {
                    'machine_id': machine_info.machine_id,
                    'position': list(machine_info.position.coordinates),
                    'life_value': machine_info.life_value,
                    'machine_type': machine_info.machine_type,
                    'status': machine_info.status,
                    'last_action': machine_info.last_action
                }
            return jsonify(result)
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/mcp/machines/<machine_id>', methods=['GET'])
    def get_machine(machine_id):
        """获取特定机器信息"""
        try:
            machine_info = world_manager.get_machine_info(machine_id)
            if machine_info:
                result = {
                    'machine_id': machine_info.machine_id,
                    'position': list(machine_info.position.coordinates),
                    'life_value': machine_info.life_value,
                    'machine_type': machine_info.machine_type,
                    'status': machine_info.status,
                    'last_action': machine_info.last_action
                }
                return jsonify(result)
            else:
                return jsonify({'error': 'Machine not found'}), 404
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/mcp/health', methods=['GET'])
    def health_check():
        """健康检查"""
        try:
            machines = world_manager.get_all_machines()
            return jsonify({
                'status': 'ok',
                'machine_count': len(machines)
            })
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/mcp/reset', methods=['POST'])
    def reset_world():
        """重置世界状态"""
        try:
            machines = world_manager.get_all_machines()
            for machine_id in list(machines.keys()):
                world_manager.remove_machine(machine_id)
            return jsonify({'status': 'ok', 'message': 'World reset successfully'})
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    return app


def run_http_server(app, port=8001):
    """在后台线程中运行HTTP服务器"""
    def run():
        app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

    thread = threading.Thread(target=run, daemon=True)
    thread.start()
    return thread


if __name__ == "__main__":
    args = parse_args()

    # 创建MCP服务器
    server = MCPServer()

    # 获取WorldManager实例
    world_manager = server.world_manager

    # 创建HTTP服务器
    http_app = create_http_server(world_manager, server)

    # 在后台启动HTTP服务器
    print("🚀 启动MCP服务器...")
    print("🌐 启动HTTP接口服务器...")
    http_thread = run_http_server(http_app, port=8003)

    print("✅ MCP服务器启动成功")
    print("✅ HTTP接口服务器启动成功 (端口: 8003)")
    print("📡 MCP服务器地址: http://localhost:8004")
    print("🌐 HTTP接口地址: http://localhost:8003")

    # 运行MCP服务器 - 使用stdio模式
    server.run(transport="stdio")
