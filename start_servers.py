#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Startup script — start all services at once.

Usage:
    python start_servers.py          # Start all services
    python start_servers.py --stop   # Stop all services
    python start_servers.py --status # Show service status
"""

import os
import sys
import time
import signal
import subprocess
import argparse
from pathlib import Path


# Project root directory
PROJECT_ROOT = Path(__file__).parent.absolute()

# Log directory
LOGS_DIR = PROJECT_ROOT / 'logs' / 'servers'
LOGS_DIR.mkdir(parents=True, exist_ok=True)

# Service configuration
SERVICES = {
    'world_server': {
        'name': 'World Server',
        'dir': PROJECT_ROOT / 'world_server',
        'cmd': [sys.executable, 'main.py'],
        'port': 8005,
    },
    'mcp_server': {
        'name': 'MCP Server',
        'dir': PROJECT_ROOT / 'mcp_server',
        'cmd': [sys.executable, 'main.py'],
        'port': 8003,
    },
    'agent_server': {
        'name': 'Agent Server',
        'dir': PROJECT_ROOT / 'agent_server',
        'cmd': [sys.executable, 'main.py'],
        'port': 8004,
    },
    'agent_worker': {
        'name': 'Agent Worker',
        'dir': PROJECT_ROOT / 'agent_server',
        'cmd': [sys.executable, 'main.py', 'worker'],
        'port': None,  # Worker does not use an HTTP port
    },
}

# Store process PIDs
PIDS_FILE = PROJECT_ROOT / '.server_pids'


def save_pids(pids: dict):
    """Save process PIDs to file."""
    with open(PIDS_FILE, 'w') as f:
        for name, pid in pids.items():
            f.write(f"{name}:{pid}\n")


def load_pids() -> dict:
    """Load process PIDs from file."""
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
    """Remove PID file."""
    if PIDS_FILE.exists():
        PIDS_FILE.unlink()


def check_port(port: int) -> bool:
    """Check if a port is in use."""
    import socket
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1)
            result = s.connect_ex(('localhost', port))
            return result == 0
    except:
        return False


def start_service(name: str, config: dict) -> int:
    """Start a single service."""
    print(f"\nStarting {config['name']}...")

    # Check port
    if config.get('port'):
        if check_port(config['port']):
            print(f"  Port {config['port']} already in use, skipping")
            return None

    # Log file path
    log_file = LOGS_DIR / f"{name}.log"

    # Change to service directory
    os.chdir(config['dir'])

    # Start process, redirect output to log file
    log_f = None
    try:
        # Open log file (append mode, keep open)
        log_f = open(log_file, 'a', encoding='utf-8', buffering=1)

        # Write separator for new startup
        log_f.write(f"\n{'='*60}\n")
        log_f.write(f"Started at: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
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

        # Do not close log_f — let the process keep writing
        # File will be closed automatically when the process exits

        # Wait briefly, check if process started successfully
        time.sleep(1.0)
        if process.poll() is not None:
            print(f"  FAILED: {config['name']} exited immediately")
            if log_f:
                log_f.close()
            # Read last few lines of log
            try:
                with open(log_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    if lines:
                        print("  Error output (last 10 lines):")
                        for line in lines[-10:]:
                            print(f"    {line.rstrip()}")
            except:
                pass
            return None

        print(f"  OK: {config['name']} started (PID: {process.pid})")
        print(f"      Log: {log_file}")
        return process.pid

    except Exception as e:
        print(f"  ERROR starting {config['name']}: {e}")
        if log_f:
            log_f.close()
        return None
    finally:
        # Switch back to project root
        os.chdir(PROJECT_ROOT)


def stop_service(name: str, pid: int):
    """Stop a single service."""
    try:
        # Check if process exists
        os.kill(pid, 0)
        # Process exists, send SIGTERM
        os.kill(pid, signal.SIGTERM)
        # Wait for process to exit
        for _ in range(10):
            try:
                os.kill(pid, 0)
                time.sleep(0.1)
            except ProcessLookupError:
                break
        else:
            # Force kill if still running
            try:
                os.kill(pid, signal.SIGKILL)
            except ProcessLookupError:
                pass

        print(f"  Stopped {name} (PID: {pid})")
        return True
    except ProcessLookupError:
        # Process not found is normal (may have failed to start or already exited)
        return False
    except Exception as e:
        print(f"  ERROR stopping {name}: {e}")
        return False


def start_all():
    """Start all services."""
    print("=" * 60)
    print("Starting all services")
    print("=" * 60)

    pids = {}

    # Start services in order
    service_order = ['world_server', 'mcp_server', 'agent_server', 'agent_worker']

    for service_name in service_order:
        if service_name in SERVICES:
            config = SERVICES[service_name]
            pid = start_service(service_name, config)
            if pid:
                pids[service_name] = pid
            time.sleep(1)

    # Save PIDs
    if pids:
        save_pids(pids)
        print("\n" + "=" * 60)
        print("All services started")
        print("=" * 60)
        print("\nRunning services:")
        for name, pid in pids.items():
            print(f"  {SERVICES[name]['name']}: PID {pid}")
        print(f"\nLog directory: {LOGS_DIR}")
        print("  Service logs:")
        for name in pids.keys():
            log_file = LOGS_DIR / f"{name}.log"
            print(f"    - {SERVICES[name]['name']}: {log_file}")
        print(f"\nUse 'python start_servers.py --stop' to stop all services")
        print(f"Use 'tail -f {LOGS_DIR}/<service>.log' to follow logs")
    else:
        print("\nNo services started successfully")


def stop_all():
    """Stop all services."""
    print("=" * 60)
    print("Stopping all services")
    print("=" * 60)

    pids = load_pids()

    stopped_count = 0
    not_found_count = 0

    # Stop services recorded in PID file
    if pids:
        for name, pid in pids.items():
            service_name = SERVICES.get(name, {}).get('name', name)
            if stop_service(service_name, pid):
                stopped_count += 1
            else:
                not_found_count += 1
            time.sleep(0.3)

    # Clean up processes occupying ports (even if not in PID file)
    print("\nChecking and cleaning up port-occupying processes...")
    import subprocess
    for service_name, config in SERVICES.items():
        port = config.get('port')
        if port:
            try:
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
                            try:
                                os.kill(pid, 0)
                                os.kill(pid, signal.SIGKILL)
                            except ProcessLookupError:
                                pass
                            print(f"  Stopped process on port {port} (PID: {pid})")
                            stopped_count += 1
                        except (ProcessLookupError, PermissionError):
                            pass
            except (subprocess.TimeoutExpired, FileNotFoundError):
                pass

    # Clean up all worker processes
    print("Cleaning up worker processes...")
    try:
        result = subprocess.run(
            ['pkill', '-f', 'python.*main.py worker'],
            capture_output=True,
            text=True,
            timeout=2
        )
        if result.returncode == 0:
            print("  Worker processes cleaned up")
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    if not_found_count > 0:
        print(f"\nNote: {not_found_count} service(s) were not running")

    clear_pids()
    print("\nAll services stopped")


def show_status():
    """Show service status."""
    print("=" * 60)
    print("Service Status")
    print("=" * 60)

    pids = load_pids()

    if not pids:
        print("No services running")
        return

    for name, pid in pids.items():
        config = SERVICES.get(name, {})
        service_name = config.get('name', name)

        # Check if process exists
        try:
            os.kill(pid, 0)
            status = "running"
        except ProcessLookupError:
            status = "stopped"
        except:
            status = "unknown"

        port_info = ""
        if config.get('port'):
            port_status = "in use" if check_port(config['port']) else "free"
            port_info = f" | port {config['port']}: {port_status}"

        log_file = LOGS_DIR / f"{name}.log"
        log_info = f" | log: {log_file.name}"

        print(f"  {service_name}: {status} (PID: {pid}){port_info}{log_info}")

    print(f"\nAll logs: {LOGS_DIR}")


def main():
    parser = argparse.ArgumentParser(description='Start/stop all services')
    parser.add_argument(
        '--stop',
        action='store_true',
        help='Stop all services'
    )
    parser.add_argument(
        '--status',
        action='store_true',
        help='Show service status'
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
        print("\n\nInterrupted by user")
        stop_all()
        sys.exit(0)
