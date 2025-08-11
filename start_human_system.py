#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
启动Human管理系统 - 同时启动MCP服务器和Human管理服务器
"""

import subprocess
import time
import sys
import signal
import os

def start_service(name, command, cwd=None):
    """启动一个服务"""
    print(f"🚀 启动 {name}...")
    try:
        process = subprocess.Popen(
            command,
            shell=True,
            cwd=cwd or os.getcwd(),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )
        return process
    except Exception as e:
        print(f"❌ 启动 {name} 失败: {e}")
        return None

def main():
    """主函数"""
    print("🚀 启动Human管理系统")
    print("=" * 50)

    processes = []

    try:
        # 启动MCP服务器
        mcp_process = start_service(
            "MCP服务器",
            "python run_mcp_server.py"
        )
        if mcp_process:
            processes.append(("MCP服务器", mcp_process))
            print("✅ MCP服务器启动中... (端口: 8003)")

        # 等待MCP服务器启动
        print("⏳ 等待MCP服务器完全启动...")
        time.sleep(3)

        # 启动Human管理服务器
        human_process = start_service(
            "Human管理服务器",
            "python human_manager_server.py"
        )
        if human_process:
            processes.append(("Human管理服务器", human_process))
            print("✅ Human管理服务器启动中... (端口: 8004)")

        # 等待服务启动
        time.sleep(2)

        print("\n" + "=" * 50)
        print("🎉 系统启动完成！")
        print("\n📡 服务地址:")
        print("  MCP服务器:     http://localhost:8003")
        print("  Human管理:     http://localhost:8004")
        print("  前端界面:      http://localhost:3000")

        print("\n💡 API使用示例:")
        print("  # 创建Human")
        print("  curl -X POST http://localhost:8004/api/humans \\")
        print("    -H 'Content-Type: application/json' \\")
        print("    -d '{\"human_id\": \"commander1\", \"machine_count\": 3}'")
        print()
        print("  # 发送命令")
        print("  curl -X POST http://localhost:8004/api/humans/commander1/command \\")
        print("    -H 'Content-Type: application/json' \\")
        print("    -d '{\"command\": \"让所有机器人排成一排\"}'")

        print("\n🧪 运行测试:")
        print("  python test_human_api.py")

        print("\n按 Ctrl+C 停止所有服务")

        # 等待用户中断
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        print("\n👋 收到停止信号，正在关闭服务...")

        # 终止所有进程
        for name, process in processes:
            try:
                print(f"🔄 停止 {name}...")
                process.terminate()
                process.wait(timeout=5)
                print(f"✅ {name} 已停止")
            except subprocess.TimeoutExpired:
                print(f"⚠️  强制终止 {name}...")
                process.kill()
            except Exception as e:
                print(f"❌ 停止 {name} 失败: {e}")

        print("👋 所有服务已停止")
        sys.exit(0)

    except Exception as e:
        print(f"❌ 系统启动失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
