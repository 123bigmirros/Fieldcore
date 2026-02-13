# -*- coding: utf-8 -*-
"""
简单的 API 测试脚本

快速测试各个接口，不依赖 pytest
"""

import requests
import time
import json

BASE_URL = "http://localhost:8004"
API_PREFIX = "/api/agent"
AUTH_PREFIX = "/api/auth"


def print_response(title, response):
    """打印响应信息"""
    print(f"\n{'='*60}")
    print(f"{title}")
    print(f"{'='*60}")
    print(f"状态码: {response.status_code}")
    try:
        print(f"响应内容: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    except:
        print(f"响应内容: {response.text}")


def get_api_key():
    """获取 API Key"""
    print("\n🔑 获取 API Key...")
    response = requests.post(f"{BASE_URL}{AUTH_PREFIX}/register", json={}, timeout=5)
    print_response("注册用户", response)

    if response.status_code == 201:
        api_key = response.json().get('api_key')
        print(f"✅ API Key: {api_key[:30]}...")
        return api_key
    return None


def test_endpoints(api_key):
    """测试各个端点"""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    # 1. 健康检查
    print("\n1️⃣ 健康检查")
    response = requests.get(f"{BASE_URL}/health", timeout=5)
    print_response("健康检查", response)

    # 2. 创建 Human Agent
    print("\n2️⃣ 创建 Human Agent")
    human_id = f"test_human_{int(time.time())}"
    data = {
        "agent_type": "human",
        "agent_id": human_id,
        "machine_count": 3
    }
    response = requests.post(f"{BASE_URL}{API_PREFIX}", json=data, headers=headers, timeout=30)
    print_response("创建 Human Agent", response)

    if response.status_code != 200:
        print("❌ 创建 Human Agent 失败，后续测试可能无法进行")
        return

    # 3. 获取 Agent 信息
    print("\n3️⃣ 获取 Agent 信息")
    response = requests.get(f"{BASE_URL}{API_PREFIX}/{human_id}", headers=headers, timeout=10)
    print_response("获取 Agent 信息", response)

    # 4. 获取所有 Agent 列表
    print("\n4️⃣ 获取所有 Agent 列表")
    response = requests.get(f"{BASE_URL}{API_PREFIX}", headers=headers, timeout=10)
    print_response("获取 Agent 列表", response)

    # 5. 发送命令
    print("\n5️⃣ 发送命令")
    data = {"command": "move forward"}
    response = requests.post(f"{BASE_URL}{API_PREFIX}/{human_id}/command", json=data, headers=headers, timeout=30)
    print_response("发送命令", response)

    if response.status_code == 200:
        task_id = response.json().get('task_id')

        # 6. 查询任务状态
        if task_id:
            print("\n6️⃣ 查询任务状态")
            time.sleep(2)  # 等待任务执行
            response = requests.get(f"{BASE_URL}{API_PREFIX}/command/task/{task_id}", headers=headers, timeout=10)
            print_response("查询任务状态", response)

    # 7. 测试无 API Key 的请求
    print("\n7️⃣ 测试 API Key 验证")
    response = requests.post(f"{BASE_URL}{API_PREFIX}", json={"agent_type": "human", "agent_id": "test"}, timeout=10)
    print_response("无 API Key 请求", response)
    if response.status_code == 401:
        print("✅ API Key 验证正常工作")


if __name__ == "__main__":
    print("="*60)
    print("Agent Server API 集成测试")
    print("="*60)

    # 获取 API Key
    api_key = get_api_key()

    if not api_key:
        print("❌ 无法获取 API Key，退出测试")
        exit(1)

    # 测试各个端点
    test_endpoints(api_key)

    print("\n" + "="*60)
    print("测试完成")
    print("="*60)

