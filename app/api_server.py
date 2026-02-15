#!/usr/bin/env python3
"""
API服务器 - 直接访问MCP服务器的WorldManager
"""

import json
import sys
import os
from flask import Flask, jsonify
from flask_cors import CORS

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

app = Flask(__name__)
CORS(app)

import requests

# MCP服务器HTTP接口配置
MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://localhost:8003")

def call_mcp_server(endpoint, data=None):
    """调用MCP服务器HTTP接口"""
    try:
        url = f"{MCP_SERVER_URL}/mcp/{endpoint}"
        if data:
            response = requests.post(url, json=data, timeout=5)
        else:
            response = requests.get(url, timeout=5)

        if response.status_code == 200:
            return response.json()
        else:
            print(f"MCP服务器返回错误: {response.status_code}")
            return None
    except requests.exceptions.ConnectionError:
        print(f"无法连接到MCP服务器: {MCP_SERVER_URL}")
        return None
    except Exception as e:
        print(f"调用MCP服务器失败: {e}")
        return None

@app.route('/api/machines', methods=['GET'])
def get_machines():
    """从MCP服务器获取所有机器信息"""
    try:
        result = call_mcp_server("machines")
        if result is not None:
            return json.dumps(result, ensure_ascii=False)
        else:
            # 如果MCP服务器不可用，返回空数据
            return json.dumps({}, ensure_ascii=False)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/machines/<machine_id>', methods=['GET'])
def get_machine(machine_id):
    """从MCP服务器获取特定机器信息"""
    try:
        result = call_mcp_server(f"machines/{machine_id}")
        if result:
            return json.dumps(result, ensure_ascii=False)
        else:
            return jsonify({'error': 'Machine not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """健康检查端点"""
    try:
        result = call_mcp_server("health")
        if result:
            return jsonify({
                'status': 'ok',
                'mcp_connected': True,
                'machine_count': result.get('machine_count', 0)
            })
        else:
            return jsonify({
                'status': 'warning',
                'mcp_connected': False,
                'message': 'MCP服务器不可用'
            })
    except Exception as e:
        return jsonify({'status': 'error', 'mcp_connected': False, 'error': str(e)}), 500

@app.route('/api/reset', methods=['POST'])
def reset_world():
    """重置世界状态（通过MCP服务器）"""
    try:
        result = call_mcp_server("reset", {})
        if result:
            return jsonify({'status': 'ok', 'message': 'World reset successfully'})
        else:
            return jsonify({'error': 'Failed to reset world'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    print("🚀 启动API服务器...")
    print(f"📡 将连接到MCP服务器: {MCP_SERVER_URL}")
    print("✅ API服务器启动成功")
    print("🔧 API服务器地址: http://localhost:8000")
    app.run(host='0.0.0.0', port=8000, debug=False)
