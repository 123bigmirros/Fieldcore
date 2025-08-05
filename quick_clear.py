#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快速清理脚本 - 一键清空所有机器人和障碍物
"""

import requests

def quick_clear():
    """快速清理世界状态"""
    server_url = "http://localhost:8003"

    try:
        print("🧹 清空世界状态...")
        response = requests.post(f"{server_url}/mcp/reset", timeout=5)

        if response.status_code == 200:
            result = response.json()
            if result.get('status') == 'ok':
                print("✅ 清理完成!")
                return True

        print("❌ 清理失败")
        return False

    except Exception as e:
        print(f"❌ 错误: {e}")
        print("💡 请确保MCP服务器正在运行")
        return False

if __name__ == "__main__":
    quick_clear()
