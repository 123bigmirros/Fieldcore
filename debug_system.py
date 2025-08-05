#!/usr/bin/env python3
"""
系统调试脚本 - 验证MCP服务器和机器人是否正常工作
"""

import asyncio
import sys
import os
import requests
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.logger import logger
from app.agent.human import create_human_commander


async def test_basic_functionality():
    """测试基本功能"""
    logger.info("🔍 开始系统调试...")

    # 1. 测试HTTP服务器是否运行
    logger.info("\n=== 测试1: HTTP服务器连接 ===")
    try:
        response = requests.get("http://localhost:8003/mcp/health", timeout=5)
        logger.info(f"✅ HTTP服务器响应: {response.status_code}")
        if response.status_code == 200:
            logger.info(f"健康检查结果: {response.json()}")
    except Exception as e:
        logger.error(f"❌ HTTP服务器连接失败: {e}")
        return False

    # 2. 测试障碍物端点
    logger.info("\n=== 测试2: 障碍物端点 ===")
    try:
        response = requests.get("http://localhost:8003/mcp/obstacles", timeout=5)
        logger.info(f"✅ 障碍物端点响应: {response.status_code}")
        if response.status_code == 200:
            data = response.json() if isinstance(response.json(), dict) else response.text
            logger.info(f"障碍物数据: {len(data) if isinstance(data, dict) else 'text response'}")
    except Exception as e:
        logger.error(f"❌ 障碍物端点失败: {e}")

    # 3. 测试Human Agent创建和简单命令
    logger.info("\n=== 测试3: Human Agent功能 ===")
    try:
        human = await create_human_commander(
            human_id="debug_commander",
            machine_count=1,  # 只创建一个机器人进行测试
            mcp_connection_params={
                "connection_type": "http_api",
                "server_url": "http://localhost:8003"
            }
        )
        logger.info("✅ Human Agent创建成功")

        # 手动创建一个测试机器人
        from app.agent.machine import MachineAgent
        from app.agent.world_manager import Position

        machine = MachineAgent(
            machine_id="test_01",
            location=Position(0.0, 0.0, 0.0),
            size=1.0,
            agent_type="machine"
        )

        machine.mcp_clients = human.mcp_clients
        machine.available_tools = human.available_tools

        await machine.register_machine()
        await machine.start_command_listener()

        human.machines["test_01"] = machine
        logger.info("✅ 测试机器人创建成功")

        # 4. 测试简单移动命令
        logger.info("\n=== 测试4: 简单移动命令 ===")
        simple_task = "让test_01号机器人移动到位置(1,1,0)"
        logger.info(f"执行任务: {simple_task}")

        result = await human.run(simple_task)
        logger.info(f"✅ 任务执行结果: {result}")

        # 5. 检查机器人是否真的移动了
        logger.info("\n=== 测试5: 验证移动结果 ===")
        final_status = await human.get_all_machines()
        logger.info(f"最终机器人状态: {final_status}")

        # 清理测试机器人
        await machine.stop_command_listener()
        await human.call_tool("mcp_python_remove_machine", machine_id="test_01")
        logger.info("🧹 测试机器人已清理")

        return True

    except Exception as e:
        logger.error(f"❌ Human Agent测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test_basic_functionality())
    if success:
        logger.info("🎉 系统调试完成，基本功能正常！")
    else:
        logger.error("💥 系统存在问题，需要修复！")
