# coding: utf-8
# A shortcut to launch OpenManus MCP server, where its introduction also solves other import issues.
import asyncio
import threading
import time
from flask import Flask, jsonify
from flask_cors import CORS
from app.mcp.server import MCPServer, parse_args


def create_http_server(mcp_server):
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
            if isinstance(result, list):
                # 如果是TextContent对象列表，提取文本内容
                content_str = ""
                for content in result:
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
            # 通过MCP服务器获取工具列表
            tools_list = asyncio.run(mcp_server.server.list_tools())

            # 转换工具格式为HTTP API格式
            tools = []
            for tool in tools_list:
                tool_dict = {
                    'name': tool.name,
                    'description': tool.description,
                    'parameters': tool.inputSchema
                }
                tools.append(tool_dict)

            return jsonify({'tools': tools})
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/mcp/machines', methods=['GET'])
    def get_machines():
        """获取所有机器信息"""
        try:
            # 通过MCP服务器获取所有机器信息
            result = asyncio.run(mcp_server.server.call_tool('get_all_machines', {}))

            # 处理返回值
            if isinstance(result, list):
                content_str = ""
                for content in result:
                    if hasattr(content, 'text'):
                        content_str += content.text
                return jsonify(content_str)
            else:
                return jsonify({'error': 'Failed to get machines'}), 500
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/mcp/machines/<machine_id>', methods=['GET'])
    def get_machine(machine_id):
        """获取特定机器信息"""
        try:
            # 通过MCP服务器获取特定机器信息
            result = asyncio.run(mcp_server.server.call_tool('get_machine_info', {'machine_id': machine_id}))

            # 处理返回值
            if isinstance(result, list):
                content_str = ""
                for content in result:
                    if hasattr(content, 'text'):
                        content_str += content.text
                return jsonify(content_str)
            else:
                return jsonify({'error': 'Machine not found'}), 404
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/mcp/health', methods=['GET'])
    def health_check():
        """健康检查"""
        try:
            # 通过MCP服务器获取机器数量
            result = asyncio.run(mcp_server.server.call_tool('get_all_machines', {}))

            if isinstance(result, list):
                content_str = ""
                for content in result:
                    if hasattr(content, 'text'):
                        content_str += content.text

                # 解析JSON获取机器数量
                import json
                machines_data = json.loads(content_str)
                machine_count = len(machines_data)

                return jsonify({
                    'status': 'ok',
                    'machine_count': machine_count
                })
            else:
                return jsonify({'error': 'Failed to get health status'}), 500
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/mcp/reset', methods=['POST'])
    def reset_world():
        """重置世界状态"""
        try:
            # 通过MCP服务器获取所有机器，然后逐个移除
            result = asyncio.run(mcp_server.server.call_tool('get_all_machines', {}))

            if isinstance(result, list):
                content_str = ""
                for content in result:
                    if hasattr(content, 'text'):
                        content_str += content.text

                # 解析JSON获取机器列表
                import json
                machines_data = json.loads(content_str)

                # 逐个移除机器
                for machine_id in machines_data.keys():
                    asyncio.run(mcp_server.server.call_tool('remove_machine', {'machine_id': machine_id}))

                # 清除所有障碍物
                asyncio.run(mcp_server.server.call_tool('clear_all_obstacles', {}))

                return jsonify({'status': 'ok', 'message': 'World reset successfully'})
            else:
                return jsonify({'error': 'Failed to reset world'}), 500
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    # 障碍物管理端点
    @app.route('/mcp/obstacles', methods=['GET'])
    def get_obstacles():
        """获取所有障碍物信息"""
        try:
            result = asyncio.run(mcp_server.server.call_tool('get_all_obstacles', {}))

            if isinstance(result, list):
                content_str = ""
                for content in result:
                    if hasattr(content, 'text'):
                        content_str += content.text
                return jsonify(content_str)
            else:
                return jsonify({'error': 'Failed to get obstacles'}), 500
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/mcp/obstacles', methods=['POST'])
    def add_obstacle():
        """添加障碍物"""
        try:
            data = request.get_json()
            obstacle_id = data.get('obstacle_id')
            position = data.get('position', [0, 0, 0])
            size = data.get('size', 1.0)
            obstacle_type = data.get('obstacle_type', 'static')

            if not obstacle_id:
                return jsonify({'error': 'obstacle_id is required'}), 400

            result = asyncio.run(mcp_server.server.call_tool('add_obstacle', {
                'obstacle_id': obstacle_id,
                'position': position,
                'size': size,
                'obstacle_type': obstacle_type
            }))

            if isinstance(result, list):
                content_str = ""
                for content in result:
                    if hasattr(content, 'text'):
                        content_str += content.text
                return jsonify({'result': content_str})
            else:
                return jsonify({'result': str(result)})

        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/mcp/obstacles/<obstacle_id>', methods=['DELETE'])
    def remove_obstacle(obstacle_id):
        """移除障碍物"""
        try:
            result = asyncio.run(mcp_server.server.call_tool('remove_obstacle', {'obstacle_id': obstacle_id}))

            if isinstance(result, list):
                content_str = ""
                for content in result:
                    if hasattr(content, 'text'):
                        content_str += content.text
                return jsonify({'result': content_str})
            else:
                return jsonify({'result': str(result)})
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/mcp/collision/check', methods=['POST'])
    def check_collision():
        """检查碰撞"""
        try:
            data = request.get_json()
            position = data.get('position', [0, 0, 0])
            size = data.get('size', 1.0)
            exclude_machine_id = data.get('exclude_machine_id')

            params = {
                'position': position,
                'size': size
            }
            if exclude_machine_id:
                params['exclude_machine_id'] = exclude_machine_id

            result = asyncio.run(mcp_server.server.call_tool('check_collision', params))

            if isinstance(result, list):
                content_str = ""
                for content in result:
                    if hasattr(content, 'text'):
                        content_str += content.text
                return jsonify(content_str)
            else:
                return jsonify({'result': str(result)})
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

    # 创建HTTP服务器
    http_app = create_http_server(server)

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
