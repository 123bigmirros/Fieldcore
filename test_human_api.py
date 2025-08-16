#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Human管理API测试脚本 - 简单测试
"""

import json
import time
import requests

# Human管理服务器地址
BASE_URL = "http://localhost:8004"

def test_api(method, endpoint, data=None):
    """测试API"""
    url = f"{BASE_URL}{endpoint}"

    try:
        if method.upper() == 'GET':
            response = requests.get(url)
        elif method.upper() == 'POST':
            response = requests.post(url, json=data)
        elif method.upper() == 'DELETE':
            response = requests.delete(url)

        print(f"\n📡 {method} {endpoint}")
        print(f"状态码: {response.status_code}")

        if response.status_code < 400:
            result = response.json()
            print(f"响应: {json.dumps(result, indent=2, ensure_ascii=False)}")
            return result
        else:
            print(f"错误: {response.text}")
            return None

    except Exception as e:
        print(f"请求失败: {e}")
        return None

def check_all_machines():
    """检查MCP服务器中的所有机器人"""
    try:
        mcp_url = "http://localhost:8003/mcp/call_tool"
        response = requests.post(mcp_url, json={
            "tool_name": "get_all_machines",
            "parameters": {}
        })

        if response.status_code == 200:
            result = response.json()
            if 'result' in result:
                import json
                machines = json.loads(result['result'])
                print(f"🤖 MCP服务器中的所有机器人: {list(machines.keys())}")
                return machines
            print(f"MCP响应: {result}")
            return {}
        else:
            print(f"❌ 无法获取机器人列表: {response.status_code}")
            return {}
    except Exception as e:
        print(f"获取所有机器人失败: {e}")
        return {}

def get_machine_position(machine_id):
    """通过MCP服务器获取机器人位置"""
    try:
        mcp_url = "http://localhost:8003/mcp/call_tool"
        response = requests.post(mcp_url, json={
            "tool_name": "get_machine_info",
            "parameters": {"machine_id": machine_id}
        })

        if response.status_code == 200:
            result = response.json()
            if 'result' in result:
                import json
                machine_info = json.loads(result['result'])
                return machine_info.get('position')
        print(f"MCP响应: {result}")
        return None
    except Exception as e:
        print(f"获取机器人位置失败: {e}")
        return None

def main():
    """主测试函数"""
    print("🚀 Human管理API测试")
    print("=" * 50)

    # 1. 创建Human
    print("\n🤖 步骤1: 创建Human")
    result = test_api("POST", "/api/humans", {
        "human_id": "test_commander",
        "machine_count": 3
    })

    if not result or result.get('status') != 'success':
        print("❌ 创建失败")
        return

    machine_count = result.get('machine_count', 0)
    print(f"✅ 创建成功，机器人数量: {machine_count}")

    # 等待一下让机器人完全注册
    print("\n⏳ 等待机器人完全初始化...")
    time.sleep(3)

    # 检查MCP服务器中的机器人
    print("\n🔍 检查MCP服务器中的机器人状态...")
    all_machines = check_all_machines()

    # 2. 获取3号机器人的初始位置
    target_machine = "test_commander_robot_01"  # 使用已知的机器人ID
    print(f"🎯 目标机器人: {target_machine}")

    if target_machine not in all_machines:
        print(f"❌ 机器人 {target_machine} 不在MCP服务器的注册列表中")
        print(f"   可用机器人: {list(all_machines.keys())}")
        return

    print(f"\n📍 步骤2: 获取{target_machine}的初始位置")
    initial_position = get_machine_position(target_machine)
    if initial_position:
        print(f"✅ 初始位置: {initial_position}")
        initial_y = initial_position[1]  # Y坐标
    else:
        print("❌ 无法获取初始位置")
        return

    # 3. 发送向下移动命令
    print(f"\n🎯 步骤3: 发送命令让{target_machine}向下移动3个单位")
    command_result = test_api("POST", "/api/humans/test_commander/command", {
        "command": "3号机器人向下移动3个单位"
    })

    if not command_result or command_result.get('status') != 'success':
        print("❌ 命令发送失败")
        return

    print("✅ 命令发送成功")

    # 4. 等待执行并检查结果
    print("\n⏳ 等待命令执行...")
    time.sleep(3)

    print(f"\n🔍 步骤4: 检查{target_machine}的最终位置")
    final_position = get_machine_position(target_machine)

    if final_position:
        print(f"✅ 最终位置: {final_position}")
        final_y = final_position[1]  # Y坐标

        # 检查是否向下移动了3个单位（Y坐标减少3）
        expected_y = initial_y - 3
        movement = initial_y - final_y

        print(f"\n📊 移动分析:")
        print(f"  初始Y坐标: {initial_y}")
        print(f"  最终Y坐标: {final_y}")
        print(f"  实际移动: {movement}个单位")
        print(f"  期望移动: 3个单位（向下）")

        if abs(movement - 3) < 0.1:  # 允许小误差
            print("✅ 移动成功！机器人正确向下移动了3个单位")
            success = True
        else:
            print("❌ 移动异常！实际移动距离与期望不符")
            success = False
    else:
        print("❌ 无法获取最终位置")
        success = False

    # 5. 获取最终状态
    print("\n📋 步骤5: 获取最终状态")
    test_api("GET", "/api/humans")

    # 6. 清理（可选）
    print(f"\n🧹 步骤6: 清理测试环境")
    cleanup = input("是否删除测试Human? (y/N): ").strip().lower()
    if cleanup == 'y':
        test_api("DELETE", "/api/humans/test_commander")
        print("✅ 清理完成")

    print("\n" + "=" * 50)
    if success:
        print("🎉 测试完全成功！Human成功控制机器人移动")
    else:
        print("⚠️  测试部分成功，但移动验证失败")
    print("=" * 50)

def quick_test():
    """快速测试 - 仅发送命令，不验证位置"""
    print("🚀 Human管理API快速测试")
    print("=" * 30)

    # 创建Human
    result = test_api("POST", "/api/humans", {
        "human_id": "quick_test",
        "machine_count": 3
    })

    if result and result.get('status') == 'success':
        # 发送命令
        test_api("POST", "/api/humans/quick_test/command", {
            "command": "3号机器人向下移动3个单位"
        })

        # 清理
        time.sleep(1)
        test_api("DELETE", "/api/humans/quick_test")
        print("✅ 快速测试完成")
    else:
        print("❌ 快速测试失败")

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "quick":
        quick_test()
    else:
        main()
