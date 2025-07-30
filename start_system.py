#!/usr/bin/env python3
"""
启动整个OpenManus系统
1. 启动MCP服务器
2. 启动API服务器
3. 提供前端访问信息
"""

import subprocess
import time
import sys
import os
import signal
import threading

def start_mcp_server():
    """启动MCP服务器"""
    print("🚀 启动MCP服务器...")
    try:
        process = subprocess.Popen([sys.executable, "run_mcp_server.py"],
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE)
        time.sleep(3)  # 等待MCP服务器启动
        if process.poll() is None:
            print("✅ MCP服务器启动成功")
            return process
        else:
            print("❌ MCP服务器启动失败")
            return None
    except Exception as e:
        print(f"❌ 启动MCP服务器时出错: {e}")
        return None

def start_api_server():
    """启动API服务器"""
    print("🚀 启动API服务器...")
    try:
        process = subprocess.Popen([sys.executable, "app/api_server.py"],
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE)
        time.sleep(3)  # 等待API服务器启动
        if process.poll() is None:
            print("✅ API服务器启动成功")
            return process
        else:
            print("❌ API服务器启动失败")
            return None
    except Exception as e:
        print(f"❌ 启动API服务器时出错: {e}")
        return None

def start_frontend():
    """启动前端开发服务器"""
    print("🚀 启动前端开发服务器...")
    try:
        os.chdir("frontend")
        process = subprocess.Popen(["npm", "run", "dev"],
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE)
        os.chdir("..")
        time.sleep(5)  # 等待前端服务器启动
        if process.poll() is None:
            print("✅ 前端开发服务器启动成功")
            return process
        else:
            print("❌ 前端开发服务器启动失败")
            return None
    except Exception as e:
        print(f"❌ 启动前端开发服务器时出错: {e}")
        return None

def cleanup(processes):
    """清理进程"""
    print("\n🧹 正在清理进程...")
    for process in processes:
        if process and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()

def main():
    """主函数"""
    processes = []

    try:
        # 启动MCP服务器
        mcp_process = start_mcp_server()
        if not mcp_process:
            print("❌ 无法启动MCP服务器，退出")
            return
        processes.append(mcp_process)

        # 启动API服务器
        api_process = start_api_server()
        if not api_process:
            print("❌ 无法启动API服务器，退出")
            cleanup(processes)
            return
        processes.append(api_process)

        # 启动前端服务器
        frontend_process = start_frontend()
        if frontend_process:
            processes.append(frontend_process)

        print("\n" + "="*50)
        print("🎉 OpenManus系统启动成功！")
        print("="*50)
        print("📱 前端界面: http://localhost:3000")
        print("🔧 API服务器: http://localhost:8000")
        print("🤖 MCP服务器: 正在运行")
        print("\n💡 现在可以运行测试脚本:")
        print("   python examples/test_human_machine_lineup_simple.py")
        print("\n按 Ctrl+C 停止所有服务")
        print("="*50)

        # 保持运行
        try:
            while True:
                time.sleep(1)
                # 检查进程是否还在运行
                for i, process in enumerate(processes):
                    if process and process.poll() is not None:
                        print(f"⚠️  进程 {i+1} 已停止")
        except KeyboardInterrupt:
            print("\n👋 收到停止信号")

    except Exception as e:
        print(f"❌ 启动过程中出错: {e}")
    finally:
        cleanup(processes)
        print("✅ 所有进程已清理")

if __name__ == "__main__":
    main()
