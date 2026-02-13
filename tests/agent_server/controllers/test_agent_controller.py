# -*- coding: utf-8 -*-
"""
Agent Controller 测试

测试 Agent Controller 的所有 API 端点
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from flask import Flask

import sys
import os
from pathlib import Path

# 添加项目路径（和 agent_server/main.py 完全一样的方式）
project_root = Path(__file__).parent.parent.parent.parent
agent_server_dir = project_root / 'agent_server'
# 确保 agent_server 可以作为包导入（用于 agent_server.app 路径）
# 注意：项目根目录必须在最前面，这样 agent_server 才能作为包被导入
sys.path.insert(0, str(project_root))
sys.path.insert(1, str(agent_server_dir))

# Mock require_api_key 装饰器
def mock_require_api_key(f):
    """Mock 版本的 require_api_key 装饰器"""
    def wrapper(*args, **kwargs):
        # 自动添加 user_id
        if 'user_id' not in kwargs:
            kwargs['user_id'] = 'test_user_01'
        return f(*args, **kwargs)
    wrapper.__name__ = f.__name__
    wrapper.__wrapped__ = f
    return wrapper


# 延迟导入 agent_bp（在 fixture 中导入，确保路径已设置）
@pytest.fixture(scope='module')
def agent_bp():
    """延迟导入 agent_bp"""
    # 确保 agent_server 包可以被正确导入
    import agent_server
    import agent_server.app
    # 使用 agent_server.app 路径导入（因为 agent_controller.py 内部使用这个路径）
    from agent_server.app.controllers.agent_controller import agent_bp
    return agent_bp


@pytest.fixture
def app(agent_bp):
    """创建测试 Flask 应用"""
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.register_blueprint(agent_bp)
    return app


@pytest.fixture
def client(app):
    """创建测试客户端"""
    return app.test_client()


class TestAgentCreate:
    """测试创建 Agent 接口"""

    @patch('agent_server.app.controllers.agent_controller.agent_service')
    def test_create_human_success(self, mock_agent_service, client):
        """测试成功创建 Human Agent"""
        # Mock agent_service
        mock_agent_service.create_agent.return_value = (
            True,
            {
                'agent_id': 'human_01',
                'agent_type': 'human',
                'machine_count': 3
            }
        )

        # 发送请求
        response = client.post(
            '/api/agent',
            json={
                'agent_type': 'human',
                'agent_id': 'human_01',
                'machine_count': 3
            }
        )

        # 验证响应
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert data['agent_id'] == 'human_01'
        assert data['agent_type'] == 'human'
        assert data['machine_count'] == 3

        # 验证调用
        mock_agent_service.create_agent.assert_called_once()
        call_args = mock_agent_service.create_agent.call_args
        assert call_args[1]['agent_type'] == 'human'
        assert call_args[1]['agent_id'] == 'human_01'
        assert call_args[1]['machine_count'] == 3

    @patch('agent_server.app.controllers.agent_controller.agent_service')
    def test_create_machine_success(self, mock_agent_service, client):
        """测试成功创建 Machine Agent"""
        mock_agent_service.create_agent.return_value = (
            True,
            {
                'agent_id': 'robot_01',
                'agent_type': 'machine',
                'owner_id': 'human_01'
            }
        )

        response = client.post(
            '/api/agent',
            json={
                'agent_type': 'machine',
                'agent_id': 'robot_01',
                'owner_id': 'human_01',
                'position': [0, 0, 0]
            }
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert data['agent_id'] == 'robot_01'
        assert data['agent_type'] == 'machine'

    @patch('agent_server.app.controllers.agent_controller.agent_service')
    def test_create_agent_failure(self, mock_agent_service, client):
        """测试创建 Agent 失败"""
        mock_agent_service.create_agent.return_value = (
            False,
            {'error': 'Invalid agent_type'}
        )

        response = client.post(
            '/api/agent',
            json={
                'agent_type': 'invalid_type',
                'agent_id': 'test_01'
            }
        )

        assert response.status_code == 400
        data = response.get_json()
        assert data['success'] is False
        assert 'error' in data


class TestGetAgentInfo:
    """测试获取 Agent 信息接口"""

    @patch('agent_server.app.controllers.agent_controller.agent_service')
    def test_get_agent_info_success(self, mock_agent_service, client):
        """测试成功获取 Agent 信息"""
        mock_agent_service.get_agent_info.return_value = {
            'agent_id': 'human_01',
            'agent_type': 'human',
            'status': 'active',
            'machine_count': 3
        }

        response = client.get('/api/agent/human_01')

        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert data['agent']['agent_id'] == 'human_01'
        assert data['agent']['agent_type'] == 'human'

    @patch('agent_server.app.controllers.agent_controller.agent_service')
    def test_get_agent_info_not_found(self, mock_agent_service, client):
        """测试 Agent 不存在"""
        mock_agent_service.get_agent_info.return_value = None

        response = client.get('/api/agent/non_existent')

        assert response.status_code == 404
        data = response.get_json()
        assert data['success'] is False
        assert 'not found' in data['error'].lower()


class TestUpdateAgentInfo:
    """测试更新 Agent 信息接口"""

    @patch('agent_server.app.controllers.agent_controller.agent_service')
    def test_update_agent_info_success(self, mock_agent_service, client):
        """测试成功更新 Agent 信息"""
        mock_agent_service.update_agent_info.return_value = (True, "")

        response = client.put(
            '/api/agent/robot_01',
            json={
                'position': [1, 2, 0],
                'life_value': 15
            }
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True

        # 验证调用
        mock_agent_service.update_agent_info.assert_called_once_with(
            'robot_01',
            {'position': [1, 2, 0], 'life_value': 15}
        )

    @patch('agent_server.app.controllers.agent_controller.agent_service')
    def test_update_agent_info_failure(self, mock_agent_service, client):
        """测试更新 Agent 信息失败"""
        mock_agent_service.update_agent_info.return_value = (False, "Agent not found")

        response = client.put(
            '/api/agent/non_existent',
            json={'position': [1, 2, 0]}
        )

        assert response.status_code == 400
        data = response.get_json()
        assert data['success'] is False
        assert 'error' in data


class TestSendCommand:
    """测试发送命令接口"""

    @patch('agent_server.app.controllers.agent_controller.task_service')
    @patch('agent_server.app.controllers.agent_controller.agent_service')
    def test_send_command_success(self, mock_agent_service, mock_task_service, client):
        """测试成功发送命令"""
        # Mock agent 存在
        mock_agent_service.get_agent_info.return_value = {
            'agent_id': 'human_01',
            'agent_type': 'human'
        }

        # Mock task_service
        mock_task_service.submit_command.return_value = 'task-uuid-12345'

        response = client.post(
            '/api/agent/human_01/command',
            json={'command': 'move forward'}
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert data['task_id'] == 'task-uuid-12345'

        # 验证调用
        mock_task_service.submit_command.assert_called_once_with('human_01', 'move forward')

    @patch('agent_server.app.controllers.agent_controller.agent_service')
    def test_send_command_missing_command(self, mock_agent_service, client):
        """测试缺少 command 参数"""
        response = client.post(
            '/api/agent/human_01/command',
            json={}
        )

        assert response.status_code == 400
        data = response.get_json()
        assert data['success'] is False
        assert 'command is required' in data['error']

    @patch('agent_server.app.controllers.agent_controller.agent_service')
    def test_send_command_agent_not_found(self, mock_agent_service, client):
        """测试 Agent 不存在"""
        mock_agent_service.get_agent_info.return_value = None

        response = client.post(
            '/api/agent/non_existent/command',
            json={'command': 'move forward'}
        )

        assert response.status_code == 404
        data = response.get_json()
        assert data['success'] is False
        assert 'not found' in data['error'].lower()


class TestGetTaskStatus:
    """测试查询任务状态接口"""

    @patch('agent_server.app.controllers.agent_controller.task_service')
    def test_get_task_status_success(self, mock_task_service, client):
        """测试成功查询任务状态"""
        mock_task_service.get_task_status.return_value = {
            'success': True,
            'status': 'SUCCESS',
            'result': {'message': 'Command executed'}
        }

        response = client.get('/api/agent/command/task/task-uuid-12345')

        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert data['status'] == 'SUCCESS'

        # 验证调用
        mock_task_service.get_task_status.assert_called_once_with('task-uuid-12345')


class TestDeleteAgent:
    """测试删除 Agent 接口"""

    @patch('agent_server.app.controllers.agent_controller.agent_service')
    def test_delete_agent_success(self, mock_agent_service, client):
        """测试成功删除 Agent"""
        mock_agent_service.delete_agent.return_value = (True, "")

        response = client.delete('/api/agent/human_01')

        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True

        # 验证调用
        mock_agent_service.delete_agent.assert_called_once_with('human_01')

    @patch('agent_server.app.controllers.agent_controller.agent_service')
    def test_delete_agent_not_found(self, mock_agent_service, client):
        """测试删除不存在的 Agent"""
        mock_agent_service.delete_agent.return_value = (False, "Agent not found")

        response = client.delete('/api/agent/non_existent')

        assert response.status_code == 404
        data = response.get_json()
        assert data['success'] is False
        assert 'error' in data


class TestListAgents:
    """测试获取所有 Agent 列表接口"""

    @patch('agent_server.app.controllers.agent_controller.agent_service')
    def test_list_agents_success(self, mock_agent_service, client):
        """测试成功获取 Agent 列表"""
        mock_agent_service.get_all_agents.return_value = {
            'human_01': {
                'agent_id': 'human_01',
                'agent_type': 'human',
                'status': 'active'
            },
            'robot_01': {
                'agent_id': 'robot_01',
                'agent_type': 'machine',
                'owner_id': 'human_01'
            }
        }

        response = client.get('/api/agent')

        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert 'agents' in data
        assert len(data['agents']) == 2

        # 验证调用
        mock_agent_service.get_all_agents.assert_called_once()

    @patch('agent_server.app.controllers.agent_controller.agent_service')
    def test_list_agents_empty(self, mock_agent_service, client):
        """测试空 Agent 列表"""
        mock_agent_service.get_all_agents.return_value = {}

        response = client.get('/api/agent')

        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert len(data['agents']) == 0
