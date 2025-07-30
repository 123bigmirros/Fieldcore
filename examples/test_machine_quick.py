"""
快速Machine Agent测试 - 验证基本功能
"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.logger import logger
from app.agent.machine import create_smart_machine
from app.agent.world_manager import Position


async def quick_machine_test():
    """快速测试Machine Agent核心功能"""
    logger.info("🚀 开始快速Machine Agent测试")

    # 创建Machine Agent
    machine = await create_smart_machine(
        machine_id="quick_test_robot",
        location=Position(0.0, 0.0, 0.0),
        life_value=10,
        machine_type="worker"
    )

    try:
        # 测试1: 检查注册状态
        logger.info("📊 测试1: 检查机器人注册状态")
        result = await machine.call_tool("mcp_python_get_machine_info", machine_id="quick_test_robot")
        logger.info(f"✅ 机器人状态: {result}")

        # 测试2: 发送简单移动命令
        logger.info("📤 测试2: 发送移动命令")
        send_result = await machine.call_tool(
            "mcp_python_send_command_to_machine",
            machine_id="quick_test_robot",
            command_type="move_to",
            parameters={"position": [1.0, 1.0, 0.0]}
        )
        logger.info(f"✅ 命令发送结果: {send_result}")

        # 测试3: 检查命令队列
        logger.info("📋 测试3: 检查命令队列")
        commands = await machine.get_pending_commands()
        logger.info(f"✅ 待执行命令数量: {len(commands)}")

        if commands:
            logger.info(f"📄 命令详情: {commands[0]['command_type']} -> {commands[0]['parameters']}")

        # 测试4: 手动执行命令
        if commands:
            logger.info("⚡ 测试4: 手动执行一个命令")
            command = commands[0]
            await machine.execute_command(command)

            # 检查执行后状态
            result = await machine.call_tool("mcp_python_get_machine_info", machine_id="quick_test_robot")
            logger.info(f"✅ 执行后状态: {result}")

        logger.info("🎉 快速测试完成 - Machine Agent工作正常！")

    except Exception as e:
        logger.error(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

    finally:
        # 清理资源
        await machine.cleanup()
        logger.info("🧹 测试完成，资源已清理")


if __name__ == "__main__":
    asyncio.run(quick_machine_test())
