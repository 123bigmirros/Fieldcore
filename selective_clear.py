#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
选择性清理脚本 - 可以选择清理机器人、障碍物或全部
"""

import requests
import json
import sys
import argparse


def get_status(server_url):
    """获取当前状态"""
    try:
        # 获取机器人
        machines_resp = requests.get(f"{server_url}/mcp/machines", timeout=5)
        machine_count = 0
        if machines_resp.status_code == 200:
            try:
                data = machines_resp.json()
                if isinstance(data, str):
                    data = json.loads(data)
                machine_count = len(data) if data else 0
            except:
                pass

        # 获取障碍物
        obstacles_resp = requests.get(f"{server_url}/mcp/obstacles", timeout=5)
        obstacle_count = 0
        if obstacles_resp.status_code == 200:
            try:
                data = obstacles_resp.json()
                if isinstance(data, str):
                    data = json.loads(data)
                obstacle_count = len(data) if data else 0
            except:
                pass

        return machine_count, obstacle_count

    except Exception as e:
        print(f"⚠️  获取状态失败: {e}")
        return 0, 0


def clear_machines(server_url):
    """清理所有机器人"""
    try:
        print("🤖 清理机器人...")

        # 获取所有机器人
        machines_resp = requests.get(f"{server_url}/mcp/machines", timeout=5)
        if machines_resp.status_code != 200:
            print("❌ 无法获取机器人列表")
            return False

        machines_data = machines_resp.json()
        if isinstance(machines_data, str):
            machines_data = json.loads(machines_data)

        if not machines_data:
            print("ℹ️  没有机器人需要清理")
            return True

        # 逐个移除机器人
        removed_count = 0
        for machine_id in machines_data.keys():
            try:
                result = requests.post(f"{server_url}/mcp/call_tool",
                                     json={
                                         'tool_name': 'remove_machine',
                                         'parameters': {'machine_id': machine_id}
                                     }, timeout=5)
                if result.status_code == 200:
                    removed_count += 1
                    print(f"  ✅ 移除机器人: {machine_id}")
            except Exception as e:
                print(f"  ❌ 移除机器人 {machine_id} 失败: {e}")

        print(f"🎯 机器人清理完成: {removed_count}/{len(machines_data)}")
        return removed_count == len(machines_data)

    except Exception as e:
        print(f"❌ 清理机器人失败: {e}")
        return False


def clear_obstacles(server_url):
    """清理所有障碍物"""
    try:
        print("🧱 清理障碍物...")

        result = requests.post(f"{server_url}/mcp/call_tool",
                             json={
                                 'tool_name': 'clear_all_obstacles',
                                 'parameters': {}
                             }, timeout=5)

        if result.status_code == 200:
            print("✅ 障碍物清理完成")
            return True
        else:
            print("❌ 障碍物清理失败")
            return False

    except Exception as e:
        print(f"❌ 清理障碍物失败: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="选择性清理OpenManus世界状态")
    parser.add_argument('--machines', '-m', action='store_true', help='只清理机器人')
    parser.add_argument('--obstacles', '-o', action='store_true', help='只清理障碍物')
    parser.add_argument('--all', '-a', action='store_true', help='清理所有(默认)')
    parser.add_argument('--url', default='http://localhost:8003', help='服务器地址')

    args = parser.parse_args()

    print("🧹 OpenManus 选择性清理工具")
    print("-" * 40)

    # 检查连接
    try:
        health_resp = requests.get(f"{args.url}/mcp/health", timeout=5)
        if health_resp.status_code != 200:
            print(f"❌ 无法连接到服务器: {args.url}")
            return
    except Exception as e:
        print(f"❌ 服务器连接失败: {e}")
        return

    # 获取当前状态
    machine_count, obstacle_count = get_status(args.url)
    print(f"📊 当前状态: 🤖 {machine_count} 机器人, 🧱 {obstacle_count} 障碍物")

    if machine_count == 0 and obstacle_count == 0:
        print("✅ 世界已经是空的")
        return

    # 确定清理范围
    clear_machines_flag = args.machines or args.all or (not args.machines and not args.obstacles)
    clear_obstacles_flag = args.obstacles or args.all or (not args.machines and not args.obstacles)

    success = True

    # 执行清理
    if clear_machines_flag and machine_count > 0:
        success &= clear_machines(args.url)

    if clear_obstacles_flag and obstacle_count > 0:
        success &= clear_obstacles(args.url)

    # 验证结果
    final_machine_count, final_obstacle_count = get_status(args.url)
    print(f"📊 最终状态: 🤖 {final_machine_count} 机器人, 🧱 {final_obstacle_count} 障碍物")

    if success:
        print("🎉 清理完成!")
    else:
        print("⚠️  清理过程中有部分失败")


if __name__ == "__main__":
    main()
