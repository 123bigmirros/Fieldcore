#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
启动脚本 - 同时启动所有服务

用法:
    python start_servers.py          # 启动所有服务
    python start_servers.py --stop   # 停止所有服务
    python start_servers.py --status # 查看服务状态
"""

import os
import sys
import time
import signal
import subprocess
import argparse
from pathlib import Path


# 项目根目录
PROJECT_ROOT = Path(__file__).parent.absolute()

# 日志目录
LOGS_DIR = PROJECT_ROOT / 'logs' / 'servers'
LOGS_DIR.mkdir(parents=True, exist_ok=True)

# 服务配置
SERVICES = {
    'world_server': {
        'name': '🌍 World Server',
        'dir': PROJECT_ROOT / 'world_server',
        'cmd': [sys.executable, 'main.py'],
        'port': 8005,
    },
    'mcp_server': {
        'name': '🔧 MCP Server',
        'dir': PROJECT_ROOT / 'mcp_server',
        'cmd': [sys.executable, 'main.py'],
        'port': 8006,
    },
    'agent_server': {
        'name': '👤 Agent Server',
        'dir': PROJECT_ROOT / 'agent_server',
        'cmd': [sys.executable, 'main.py'],
        'port': 8007,
    },
    'agent_worker': {
        'name': '🔄 Agent Worker',
        'dir': PROJECT_ROOT / 'agent_server',
        'cmd': [sys.executable, 'main.py', 'worker'],
        'port': None,  # Worker 不使用 HTTP 端口
    },
}

# 存储进程 PID
PIDS_FILE = PROJECT_ROOT / '.server_pids'


def save_pids(pids: dict):
    """保存进程 PID"""
    with open(PIDS_FILE, 'w') as f:
        for name, pid in pids.items():
            f.write(f"{name}:{pid}\n")


def load_pids() -> dict:
    """加载进程 PID"""
    pids = {}
    if PIDS_FILE.exists():
        with open(PIDS_FILE, 'r') as f:
            for line in f:
                line = line.strip()
                if ':' in line:
                    name, pid = line.split(':', 1)
                    pids[name] = int(pid)
    return pids


def clear_pids():
    """清除 PID 文件"""
    if PIDS_FILE.exists():
        PIDS_FILE.unlink()


def check_port(port: int) -> bool:
    """检查端口是否被占用"""
    import socket
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1)
            result = s.connect_ex(('localhost', port))
            return result == 0
    except:
        return False


def start_service(name: str, config: dict) -> int:
    """启动单个服务"""
    print(f"\n🚀 启动 {config['name']}...")

    # 检查端口
    if config.get('port'):
        if check_port(config['port']):
            print(f"⚠️  端口 {config['port']} 已被占用，跳过启动")
            return None

    # 创建日志文件路径
    log_file = LOGS_DIR / f"{name}.log"

    # 切换到服务目录
    os.chdir(config['dir'])

    # 启动进程，将日志输出到文件
    log_f = None
    try:
        # 打开日志文件（追加模式，保持打开状态）
        log_f = open(log_file, 'a', encoding='utf-8', buffering=1)

        # 写入分隔符，标识新的启动
        log_f.write(f"\n{'='*60}\n")
        log_f.write(f"启动时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        log_f.write(f"{'='*60}\n")
        log_f.flush()

        process = subprocess.Popen(
            config['cmd'],
            stdout=log_f,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True
        )

        # 注意：不关闭 log_f，让进程持续写入日志
        # 文件会在进程结束时自动关闭

        # 等待一下，检查进程是否正常启动
        time.sleep(1.0)  # 增加等待时间，让进程有时间启动
        if process.poll() is not None:
            print(f"❌ {config['name']} 启动失败（进程已退出）")
            # 关闭文件句柄（进程已退出）
            if log_f:
                log_f.close()
            # 读取日志文件的最后几行
            try:
                with open(log_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    if lines:
                        print("错误输出（最后10行）:")
                        for line in lines[-10:]:
                            print(f"  {line.rstrip()}")
            except:
                pass
            return None

        print(f"✅ {config['name']} 已启动 (PID: {process.pid})")
        print(f"   📝 日志文件: {log_file}")
        return process.pid

    except Exception as e:
        print(f"❌ 启动 {config['name']} 时出错: {e}")
        # 如果出错，关闭文件句柄
        if log_f:
            log_f.close()
        return None
    finally:
        # 切换回项目根目录
        os.chdir(PROJECT_ROOT)


def stop_service(name: str, pid: int):
    """停止单个服务"""
    try:
        # 先检查进程是否存在
        os.kill(pid, 0)  # 发送信号0检查进程是否存在
        # 进程存在，发送终止信号
        os.kill(pid, signal.SIGTERM)
        # 等待进程退出
        for _ in range(10):  # 最多等待1秒
            try:
                os.kill(pid, 0)
                time.sleep(0.1)
            except ProcessLookupError:
                break
        else:
            # 如果还没退出，强制终止
            try:
                os.kill(pid, signal.SIGKILL)
            except ProcessLookupError:
                pass

        print(f"✅ 已停止 {name} (PID: {pid})")
        return True
    except ProcessLookupError:
        # 进程不存在是正常的（可能启动失败或已退出），不显示警告
        # 只在详细模式下显示
        return False
    except Exception as e:
        print(f"❌ 停止 {name} 时出错: {e}")
        return False


def start_all():
    """启动所有服务"""
    print("=" * 60)
    print("🚀 启动所有服务")
    print("=" * 60)

    pids = {}

    # 按顺序启动服务
    service_order = ['world_server', 'mcp_server', 'agent_server', 'agent_worker']

    for service_name in service_order:
        if service_name in SERVICES:
            config = SERVICES[service_name]
            pid = start_service(service_name, config)
            if pid:
                pids[service_name] = pid
            time.sleep(1)  # 等待服务启动

    # 保存 PID
    if pids:
        save_pids(pids)
        print("\n" + "=" * 60)
        print("✅ 所有服务已启动")
        print("=" * 60)
        print("\n📋 运行中的服务:")
        for name, pid in pids.items():
            log_file = LOGS_DIR / f"{name}.log"
            print(f"  {SERVICES[name]['name']}: PID {pid}")
        print(f"\n📝 日志文件位置: {LOGS_DIR}")
        print("   各服务日志文件:")
        for name in pids.keys():
            log_file = LOGS_DIR / f"{name}.log"
            print(f"     - {SERVICES[name]['name']}: {log_file}")
        print(f"\n💡 使用 'python start_servers.py --stop' 停止所有服务")
        print(f"💡 使用 'tail -f {LOGS_DIR}/<服务名>.log' 实时查看日志")
    else:
        print("\n❌ 没有服务成功启动")


def stop_all():
    """停止所有服务"""
    print("=" * 60)
    print("🛑 停止所有服务")
    print("=" * 60)

    pids = load_pids()

    stopped_count = 0
    not_found_count = 0

    # 停止 PID 文件中记录的服务
    if pids:
        for name, pid in pids.items():
            service_name = SERVICES.get(name, {}).get('name', name)
            if stop_service(service_name, pid):
                stopped_count += 1
            else:
                not_found_count += 1
            time.sleep(0.3)

    # 清理占用端口的进程（即使不在 PID 文件中）
    print("\n🔍 检查并清理占用端口的进程...")
    import subprocess
    for service_name, config in SERVICES.items():
        port = config.get('port')
        if port:
            try:
                # 查找占用端口的进程
                result = subprocess.run(
                    ['lsof', '-ti', f':{port}'],
                    capture_output=True,
                    text=True,
                    timeout=2
                )
                if result.returncode == 0 and result.stdout.strip():
                    port_pids = [int(pid) for pid in result.stdout.strip().split('\n') if pid]
                    for pid in port_pids:
                        try:
                            os.kill(pid, signal.SIGTERM)
                            time.sleep(0.2)
                            # 如果还没退出，强制终止
                            try:
                                os.kill(pid, 0)
                                os.kill(pid, signal.SIGKILL)
                            except ProcessLookupError:
                                pass
                            print(f"  ✅ 已停止占用端口 {port} 的进程 (PID: {pid})")
                            stopped_count += 1
                        except (ProcessLookupError, PermissionError):
                            pass
            except (subprocess.TimeoutExpired, FileNotFoundError):
                pass

    # 清理所有 worker 进程
    print("🔍 清理所有 worker 进程...")
    try:
        result = subprocess.run(
            ['pkill', '-f', 'python.*main.py worker'],
            capture_output=True,
            text=True,
            timeout=2
        )
        if result.returncode == 0:
            print("  ✅ 已清理 worker 进程")
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    # 显示统计信息
    if not_found_count > 0:
        print(f"\n💡 提示: {not_found_count} 个服务进程不存在（可能启动失败或已退出）")

    clear_pids()
    print("\n✅ 所有服务已停止")


def show_status():
    """显示服务状态"""
    print("=" * 60)
    print("📊 服务状态")
    print("=" * 60)

    pids = load_pids()

    if not pids:
        print("⚠️  没有运行中的服务")
        return

    for name, pid in pids.items():
        config = SERVICES.get(name, {})
        service_name = config.get('name', name)

        # 检查进程是否存在
        try:
            os.kill(pid, 0)  # 发送信号 0 检查进程是否存在
            status = "✅ 运行中"
        except ProcessLookupError:
            status = "❌ 已停止"
        except:
            status = "❓ 未知"

        port_info = ""
        if config.get('port'):
            port_status = "占用" if check_port(config['port']) else "空闲"
            port_info = f" | 端口 {config['port']}: {port_status}"

        log_file = LOGS_DIR / f"{name}.log"
        log_info = f" | 日志: {log_file.name}"

        print(f"{service_name}: {status} (PID: {pid}){port_info}{log_info}")

    print(f"\n📝 所有日志文件位置: {LOGS_DIR}")


def main():
    parser = argparse.ArgumentParser(description='启动/停止所有服务')
    parser.add_argument(
        '--stop',
        action='store_true',
        help='停止所有服务'
    )
    parser.add_argument(
        '--status',
        action='store_true',
        help='查看服务状态'
    )

    args = parser.parse_args()

    if args.stop:
        stop_all()
    elif args.status:
        show_status()
    else:
        start_all()


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  用户中断")
        stop_all()
        sys.exit(0)

