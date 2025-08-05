#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
清空世界状态脚本 - 移除所有机器人和障碍物

基于 run_mcp_server.py 中的重置端点实现
"""

import requests
import json
import sys
import time


def clear_world_state(server_url="http://localhost:8003"):
    """
    清空世界状态：移除所有机器人和障碍物

    Args:
        server_url: MCP HTTP服务器地址
    """
    print("🧹 开始清空世界状态...")

    try:
        # 1. 检查服务器健康状态
        print("📡 检查服务器连接...")
        health_url = f"{server_url}/mcp/health"
        health_response = requests.get(health_url, timeout=5)

        if health_response.status_code == 200:
            health_data = health_response.json()
            machine_count = health_data.get('machine_count', 0)
            print(f"✅ 服务器连接正常，当前机器人数量: {machine_count}")
        else:
            print(f"⚠️  服务器健康检查失败: {health_response.status_code}")
            return False

    except requests.exceptions.RequestException as e:
        print(f"❌ 无法连接到服务器 {server_url}")
        print(f"   错误: {e}")
        print(f"💡 请确保MCP服务器正在运行: python run_mcp_server.py")
        return False

    try:
        # 2. 获取当前状态
        print("📊 获取当前世界状态...")

        # 获取机器人数量
        machines_response = requests.get(f"{server_url}/mcp/machines", timeout=5)
        machine_count = 0
        if machines_response.status_code == 200:
            try:
                machines_data = machines_response.json()
                if isinstance(machines_data, str):
                    machines_data = json.loads(machines_data)
                machine_count = len(machines_data) if machines_data else 0
            except (json.JSONDecodeError, TypeError):
                machine_count = 0

        # 获取障碍物数量
        obstacles_response = requests.get(f"{server_url}/mcp/obstacles", timeout=5)
        obstacle_count = 0
        if obstacles_response.status_code == 200:
            try:
                obstacles_data = obstacles_response.json()
                if isinstance(obstacles_data, str):
                    obstacles_data = json.loads(obstacles_data)
                obstacle_count = len(obstacles_data) if obstacles_data else 0
            except (json.JSONDecodeError, TypeError):
                obstacle_count = 0

        print(f"   🤖 机器人数量: {machine_count}")
        print(f"   🧱 障碍物数量: {obstacle_count}")

        if machine_count == 0 and obstacle_count == 0:
            print("✅ 世界已经是空的，无需清理")
            return True

    except requests.exceptions.RequestException as e:
        print(f"⚠️  获取状态失败: {e}")
        print("继续尝试清理...")

    try:
        # 3. 执行重置操作
        print("🔄 执行世界重置操作...")
        reset_url = f"{server_url}/mcp/reset"
        reset_response = requests.post(reset_url, timeout=10)

        if reset_response.status_code == 200:
            result = reset_response.json()
            if result.get('status') == 'ok':
                print("✅ 世界重置成功!")
                print(f"   📝 {result.get('message', '所有机器人和障碍物已移除')}")
                return True
            else:
                print(f"❌ 重置失败: {result}")
                return False
        else:
            print(f"❌ 重置请求失败: HTTP {reset_response.status_code}")
            print(f"   响应: {reset_response.text}")
            return False

    except requests.exceptions.RequestException as e:
        print(f"❌ 重置操作失败: {e}")
        return False


def verify_clear_state(server_url="http://localhost:8003"):
    """验证清理结果"""
    print("🔍 验证清理结果...")

    try:
        # 等待一下确保操作完成
        time.sleep(1)

        # 检查机器人
        machines_response = requests.get(f"{server_url}/mcp/machines", timeout=5)
        machine_count = 0
        if machines_response.status_code == 200:
            try:
                machines_data = machines_response.json()
                if isinstance(machines_data, str):
                    machines_data = json.loads(machines_data)
                machine_count = len(machines_data) if machines_data else 0
            except:
                pass

        # 检查障碍物
        obstacles_response = requests.get(f"{server_url}/mcp/obstacles", timeout=5)
        obstacle_count = 0
        if obstacles_response.status_code == 200:
            try:
                obstacles_data = obstacles_response.json()
                if isinstance(obstacles_data, str):
                    obstacles_data = json.loads(obstacles_data)
                obstacle_count = len(obstacles_data) if obstacles_data else 0
            except:
                pass

        print(f"📊 验证结果:")
        print(f"   🤖 剩余机器人: {machine_count}")
        print(f"   🧱 剩余障碍物: {obstacle_count}")

        if machine_count == 0 and obstacle_count == 0:
            print("✅ 验证通过: 世界状态已完全清空")
            return True
        else:
            print("⚠️  验证失败: 仍有残留对象")
            return False

    except Exception as e:
        print(f"⚠️  验证过程出错: {e}")
        return False


def main():
    """主函数"""
    print("=" * 60)
    print("🧹 OpenManus 世界状态清理工具")
    print("=" * 60)

    # 默认服务器地址
    default_url = "http://localhost:8003"

    # 检查命令行参数
    if len(sys.argv) > 1:
        server_url = sys.argv[1]
        print(f"🌐 使用指定服务器地址: {server_url}")
    else:
        server_url = default_url
        print(f"🌐 使用默认服务器地址: {server_url}")

    # 执行清理
    success = clear_world_state(server_url)

    if success:
        # 验证结果
        verify_clear_state(server_url)
        print("\n🎉 世界状态清理完成!")
        print("💡 你现在可以重新运行测试脚本创建新的环境")
    else:
        print("\n❌ 世界状态清理失败!")
        print("💡 请检查MCP服务器是否正常运行")
        sys.exit(1)


if __name__ == "__main__":
    main()
