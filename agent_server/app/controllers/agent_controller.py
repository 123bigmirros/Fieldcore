# -*- coding: utf-8 -*-
"""
Agent Controller - Agent 管理控制器

提供 HTTP API:
- agentCreate: 创建 human 或 machine
- getAgentInfo: 获取 Agent 信息
- updateAgentInfo: 更新 Agent 信息
- sendCmd: 发送命令
"""

from flask import Blueprint, request, jsonify

from agent_server.app.services.agent_service import agent_service
from agent_server.app.services.task_service import task_service
from agent_server.app.utils.auth_decorator import require_api_key

agent_bp = Blueprint('agent', __name__, url_prefix='/api/agent')


@agent_bp.route('', methods=['POST'])
@require_api_key
def agent_create(user_id):
    """
    创建 Agent (human 或 machine)

    Request:
        {
            "agent_type": "human" | "machine",
            "agent_id": "human_01",
            "owner_id": "human_01",  // machine 必需
            "machine_count": 3,      // human 可选
            "position": [0, 0, 0]    // machine 可选
        }
    """
    data = request.get_json() or {}
    success, result = agent_service.create_agent(
        agent_type=data.get('agent_type'),
        agent_id=data.get('agent_id'),
        owner_id=data.get('owner_id'),
        machine_count=data.get('machine_count', 3),
        position=data.get('position'),
        user_id=user_id
    )

    if success:
        return jsonify({'success': True, **result})
    return jsonify({'success': False, **result}), 400


@agent_bp.route('/<agent_id>', methods=['GET'])
@require_api_key
def get_agent_info(agent_id, user_id):
    """
    获取 Agent 信息

    Response:
        {
            "agent_id": "...",
            "agent_type": "human" | "machine",
            "status": "active",
            ...
        }
    """
    info = agent_service.get_agent_info(agent_id)
    if info:
        return jsonify({'success': True, 'agent': info})
    return jsonify({'success': False, 'error': f'Agent {agent_id} not found'}), 404


@agent_bp.route('/<agent_id>', methods=['PUT'])
@require_api_key
def update_agent_info(agent_id, user_id):
    """
    更新 Agent 信息

    Request:
        {
            "position": [1, 2, 0],  // machine only
            "life_value": 15,        // machine only
            "metadata": {...}        // human only
        }
    """
    data = request.get_json()
    success, error = agent_service.update_agent_info(agent_id, data)
    if success:
        return jsonify({'success': True})
    return jsonify({'success': False, 'error': error}), 400


@agent_bp.route('/<agent_id>/command', methods=['POST'])
@require_api_key
def send_cmd(agent_id, user_id):
    """
    发送命令（异步执行）

    Request:
        {
            "command": "move forward"
        }

    Response:
        {
            "success": true,
            "task_id": "task-uuid"
        }
    """
    data = request.get_json()
    command = data.get('command')

    if not command:
        return jsonify({'success': False, 'error': 'command is required'}), 400

    # 验证 agent 是否存在
    if not agent_service.get_agent_info(agent_id):
        return jsonify({'success': False, 'error': f'Agent {agent_id} not found'}), 404

    # 提交异步任务（TaskService 会自动处理旧任务取消）
    task_id = task_service.submit_command(agent_id, command)
    return jsonify({'success': True, 'task_id': task_id})


@agent_bp.route('/command/task/<task_id>', methods=['GET'])
@require_api_key
def get_task_status(task_id, user_id):
    """
    查询任务状态

    Response:
        {
            "success": true,
            "status": "PENDING" | "SUCCESS" | "FAILURE",
            "result": {...}
        }
    """
    response = task_service.get_task_status(task_id)
    return jsonify(response)


@agent_bp.route('/<agent_id>', methods=['DELETE'])
@require_api_key
def delete_agent(agent_id, user_id):
    """删除 Agent"""
    success, error = agent_service.delete_agent(agent_id)
    if success:
        return jsonify({'success': True})
    return jsonify({'success': False, 'error': error}), 404


@agent_bp.route('', methods=['GET'])
@require_api_key
def list_agents(user_id):
    """获取所有 Agent 列表"""
    from app.logger import logger
    logger.info(f"📥 收到获取所有 Agent 列表请求，user_id={user_id}")
    try:
        agents = agent_service.get_all_agents()
        logger.info(f"✅ 成功返回 {len(agents)} 个 Agent")
        return jsonify({'success': True, 'agents': agents})
    except Exception as e:
        logger.error(f"❌ 获取所有 Agent 列表失败: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

