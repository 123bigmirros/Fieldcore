# -*- coding: utf-8 -*-
"""
Agent Controller API 集成测试

测试实际运行的 API 端点（需要服务正在运行）

使用方法:
    1. 确保 agent_server 正在运行 (python agent_server/main.py)
    2. 确保 Redis 正在运行
    3. 运行测试: pytest tests/agent_server/integration/test_api_endpoints.py -v -s
"""

import pytest
import requests
import time
from typing import Dict, Optional


# API 配置
BASE_URL = "http://localhost:8004"  # agent_server 默认端口（可在 config.py 中修改）
API_PREFIX = "/api/agent"
AUTH_PREFIX = "/api/auth"

# 测试用的 API Key（需要根据实际情况修改）
# 如果没有 API Key，需要先调用注册接口获取
TEST_API_KEY = None  # 将在测试开始时自动获取或使用默认值


class TestAPIIntegration:
    """API 集成测试类"""

    def __init__(self):
        self.api_key = self._get_or_create_api_key()

    def _get_or_create_api_key(self) -> str:
        """获取或创建 API Key"""
        # 尝试使用环境变量中的 API Key
        import os
        api_key = os.getenv('TEST_API_KEY')

        if api_key:
            print(f"使用环境变量中的 API Key: {api_key[:10]}...")
            return api_key

        # 尝试注册新用户获取 API Key
        try:
            register_data = {}  # 注册接口不需要参数
            response = requests.post(
                f"{BASE_URL}{AUTH_PREFIX}/register",
                json=register_data,
                timeout=5
            )

            if response.status_code == 201:
                result = response.json()
                api_key = result.get('api_key')
                if api_key:
                    print(f"✅ 成功注册并获取 API Key: {api_key[:20]}...")
                    return api_key
            else:
                print(f"⚠️ 注册用户失败: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"⚠️ 注册用户异常: {e}")

        # 如果都失败了，返回 None，让测试跳过
        print("⚠️ 无法获取 API Key，测试将跳过需要认证的接口")
        return None

    @property
    def headers(self) -> Dict[str, str]:
        """获取请求头（包含 API Key）"""
        if not self.api_key:
            return {"Content-Type": "application/json"}
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    def test_health_check(self):
        """测试健康检查端点"""
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        assert response.status_code == 200
        data = response.json()
        assert data.get('status') == 'ok'
        print(f"✅ 健康检查通过: {data}")

    def test_create_human_agent(self):
        """测试创建 Human Agent"""
        if not self.api_key:
            pytest.skip("需要 API Key")

        data = {
            "agent_type": "human",
            "agent_id": f"test_human_{int(time.time())}",
            "machine_count": 3
        }

        response = requests.post(
            f"{BASE_URL}{API_PREFIX}",
            json=data,
            headers=self.headers,
            timeout=30  # 增加超时时间，因为创建 Agent 可能需要连接其他服务
        )

        print(f"创建 Human Agent 响应: {response.status_code}")
        print(f"响应内容: {response.text}")

        # 处理超时或其他网络错误
        if response.status_code in [200, 400]:
            result = response.json()
            if response.status_code == 200:
                assert result.get('success') is True
                assert 'agent_id' in result
                print(f"✅ 成功创建 Human Agent: {result.get('agent_id')}")
                return result.get('agent_id')
            else:
                print(f"⚠️ 创建失败: {result.get('error', 'Unknown error')}")
                return None
        elif response.status_code == 401:
            print(f"❌ 认证失败，请检查 API Key")
            return None
        else:
            print(f"⚠️ 意外状态码: {response.status_code}")
            return None

    def test_create_machine_agent(self, human_agent_id: Optional[str] = None):
        """测试创建 Machine Agent"""
        # 如果没有提供 human_agent_id，先创建一个
        if not human_agent_id:
            human_data = {
                "agent_type": "human",
                "agent_id": f"test_human_{int(time.time())}",
                "machine_count": 3
            }
            human_response = requests.post(
                f"{BASE_URL}{API_PREFIX}",
                json=human_data,
                headers=self.headers,
                timeout=10
            )
            if human_response.status_code == 200:
                human_agent_id = human_response.json().get('agent_id')

        if not human_agent_id:
            pytest.skip("无法创建 Human Agent，跳过 Machine Agent 测试")

        data = {
            "agent_type": "machine",
            "agent_id": f"test_machine_{int(time.time())}",
            "owner_id": human_agent_id,
            "position": [0, 0, 0]
        }

        response = requests.post(
            f"{BASE_URL}{API_PREFIX}",
            json=data,
            headers=self.headers,
            timeout=30  # 增加超时时间，因为创建 Agent 可能需要连接其他服务
        )

        print(f"创建 Machine Agent 响应: {response.status_code}")
        print(f"响应内容: {response.text}")

        assert response.status_code in [200, 400]
        result = response.json()
        if response.status_code == 200:
            assert result.get('success') is True
            assert 'agent_id' in result
            print(f"✅ 成功创建 Machine Agent: {result.get('agent_id')}")
            return result.get('agent_id')
        else:
            print(f"⚠️ 创建失败: {result.get('error', 'Unknown error')}")
            return None

    def test_get_agent_info(self, agent_id: str = "test_human_001"):
        """测试获取 Agent 信息"""
        response = requests.get(
            f"{BASE_URL}{API_PREFIX}/{agent_id}",
            headers=self.headers,
            timeout=10
        )

        print(f"获取 Agent 信息响应: {response.status_code}")
        print(f"响应内容: {response.text}")

        # 404 也是有效的响应（Agent 不存在）
        assert response.status_code in [200, 404]
        if response.status_code == 200:
            result = response.json()
            assert result.get('success') is True
            assert 'agent' in result
            print(f"✅ 成功获取 Agent 信息: {result.get('agent')}")

    def test_list_agents(self):
        """测试获取所有 Agent 列表"""
        response = requests.get(
            f"{BASE_URL}{API_PREFIX}",
            headers=self.headers,
            timeout=10
        )

        print(f"获取 Agent 列表响应: {response.status_code}")
        print(f"响应内容: {response.text}")

        assert response.status_code == 200
        result = response.json()
        assert result.get('success') is True
        assert 'agents' in result
        print(f"✅ 成功获取 Agent 列表，共 {len(result.get('agents', {}))} 个")

    def test_update_agent_info(self, agent_id: str = "test_machine_001"):
        """测试更新 Agent 信息"""
        data = {
            "position": [1, 2, 0],
            "life_value": 15
        }

        response = requests.put(
            f"{BASE_URL}{API_PREFIX}/{agent_id}",
            json=data,
            headers=self.headers,
            timeout=10
        )

        print(f"更新 Agent 信息响应: {response.status_code}")
        print(f"响应内容: {response.text}")

        # 400 或 404 也是有效的响应（Agent 不存在或更新失败）
        assert response.status_code in [200, 400, 404]
        if response.status_code == 200:
            result = response.json()
            assert result.get('success') is True
            print(f"✅ 成功更新 Agent 信息")

    def test_send_command(self, agent_id: str = "test_human_001"):
        """测试发送命令"""
        data = {
            "command": "move forward"
        }

        response = requests.post(
            f"{BASE_URL}{API_PREFIX}/{agent_id}/command",
            json=data,
            headers=self.headers,
            timeout=10
        )

        print(f"发送命令响应: {response.status_code}")
        print(f"响应内容: {response.text}")

        # 404 也是有效的响应（Agent 不存在）
        assert response.status_code in [200, 400, 404]
        if response.status_code == 200:
            result = response.json()
            assert result.get('success') is True
            assert 'task_id' in result
            task_id = result.get('task_id')
            print(f"✅ 成功发送命令，任务 ID: {task_id}")

            # 等待一下，然后查询任务状态
            time.sleep(1)
            self.test_get_task_status(task_id)
            return task_id
        else:
            print(f"⚠️ 发送命令失败: {response.json().get('error', 'Unknown error')}")
            return None

    def test_get_task_status(self, task_id: str = "test-task-id"):
        """测试查询任务状态"""
        response = requests.get(
            f"{BASE_URL}{API_PREFIX}/command/task/{task_id}",
            headers=self.headers,
            timeout=10
        )

        print(f"查询任务状态响应: {response.status_code}")
        print(f"响应内容: {response.text}")

        assert response.status_code == 200
        result = response.json()
        assert 'status' in result
        print(f"✅ 任务状态: {result.get('status')}")

    def test_delete_agent(self, agent_id: str = "test_human_001"):
        """测试删除 Agent"""
        response = requests.delete(
            f"{BASE_URL}{API_PREFIX}/{agent_id}",
            headers=self.headers,
            timeout=10
        )

        print(f"删除 Agent 响应: {response.status_code}")
        print(f"响应内容: {response.text}")

        # 404 也是有效的响应（Agent 不存在）
        assert response.status_code in [200, 404]
        if response.status_code == 200:
            result = response.json()
            assert result.get('success') is True
            print(f"✅ 成功删除 Agent")

    def test_register_user(self):
        """测试注册用户获取 API Key"""
        data = {
            "metadata": {
                "test": True,
                "description": "测试用户"
            }
        }

        response = requests.post(
            f"{BASE_URL}{AUTH_PREFIX}/register",
            json=data,
            timeout=10
        )

        print(f"注册用户响应: {response.status_code}")
        print(f"响应内容: {response.text}")

        assert response.status_code in [201, 400]  # 201 成功，400 可能是已存在
        if response.status_code == 201:
            result = response.json()
            assert result.get('success') is True
            assert 'api_key' in result
            api_key = result.get('api_key')
            print(f"✅ 成功注册用户，API Key: {api_key[:20]}...")
            return api_key
        return None

    def test_api_key_required(self):
        """测试 API Key 验证"""
        # 不带 API Key 的请求应该返回 401
        response = requests.post(
            f"{BASE_URL}{API_PREFIX}",
            json={"agent_type": "human", "agent_id": "test"},
            timeout=10
        )

        print(f"无 API Key 请求响应: {response.status_code}")
        assert response.status_code == 401
        print("✅ API Key 验证正常工作")


def test_all_endpoints_workflow():
    """测试完整的 API 工作流程"""
    test = TestAPIIntegration()

    if not test.api_key:
        pytest.skip("无法获取 API Key，跳过测试")

    print("\n" + "="*60)
    print("开始 API 集成测试工作流")
    print("="*60)

    # 1. 健康检查
    print("\n1. 测试健康检查...")
    test.test_health_check()

    # 2. 创建 Human Agent
    print("\n2. 测试创建 Human Agent...")
    human_id = test.test_create_human_agent()

    # 3. 创建 Machine Agent
    print("\n3. 测试创建 Machine Agent...")
    machine_id = test.test_create_machine_agent(human_id)

    # 4. 获取 Agent 信息
    if human_id:
        print(f"\n4. 测试获取 Agent 信息 (human_id: {human_id})...")
        test.test_get_agent_info(human_id)

    # 5. 获取所有 Agent 列表
    print("\n5. 测试获取所有 Agent 列表...")
    test.test_list_agents()

    # 6. 更新 Agent 信息
    if machine_id:
        print(f"\n6. 测试更新 Agent 信息 (machine_id: {machine_id})...")
        test.test_update_agent_info(machine_id)

    # 7. 发送命令
    if human_id:
        print(f"\n7. 测试发送命令 (agent_id: {human_id})...")
        task_id = test.test_send_command(human_id)

    # 8. API Key 验证
    print("\n8. 测试 API Key 验证...")
    test.test_api_key_required()

    # 9. 清理：删除创建的 Agent
    if machine_id:
        print(f"\n9. 清理：删除 Machine Agent (machine_id: {machine_id})...")
        test.test_delete_agent(machine_id)

    if human_id:
        print(f"\n10. 清理：删除 Human Agent (human_id: {human_id})...")
        test.test_delete_agent(human_id)

    print("\n" + "="*60)
    print("API 集成测试工作流完成")
    print("="*60)


if __name__ == "__main__":
    # 直接运行此文件时执行完整工作流
    test_all_endpoints_workflow()

