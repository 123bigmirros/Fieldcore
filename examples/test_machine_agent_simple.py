"""
简化的Machine Agent测试 - 验证Machine Agent是否正确运行
"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.logger import logger
from app.agent.machine import create_smart_machine
from app.agent.world_manager import Position


async def test_machine_basic_functionality():
    """测试Machine Agent基本功能"""
    logger.info("🚀 开始Machine Agent基本功能测试")

    # 创建Machine Agent
    machine = await create_smart_machine(
        machine_id="test_robot_01",
        location=Position(0.0, 0.0, 0.0),
        life_value=10,
        machine_type="worker"
    )

    try:
        # 测试1: 检查机器人状态
        logger.info("\n📊 测试1: 检查机器人状态")
        result = await machine.call_tool("mcp_python_get_machine_info", machine_id="test_robot_01")
        logger.info(f"机器人状态: {result}")

        # 测试2: 检查命令队列
        logger.info("\n📋 测试2: 检查命令队列")
        commands = await machine.get_pending_commands()
        logger.info(f"待执行命令数量: {len(commands)}")

        # 测试3: 发送测试命令到自己
        logger.info("\n📤 测试3: 发送移动命令")
        send_result = await machine.call_tool(
            "mcp_python_send_command_to_machine",
            machine_id="test_robot_01",
            command_type="move_to",
            parameters={"position": [2.0, 0.0, 0.0]}
        )
        logger.info(f"命令发送结果: {send_result}")

        # 测试4: 再次检查命令队列
        logger.info("\n📋 测试4: 再次检查命令队列")
        commands = await machine.get_pending_commands()
        logger.info(f"待执行命令数量: {len(commands)}")
        if commands:
            logger.info(f"命令详情: {commands[0]}")

        # 测试5: 手动执行一个命令
        if commands:
            logger.info("\n⚡ 测试5: 手动执行命令")
            command = commands[0]
            await machine.execute_command(command)

            # 检查执行后的状态
            result = await machine.call_tool("mcp_python_get_machine_info", machine_id="test_robot_01")
            logger.info(f"执行后机器人状态: {result}")

        logger.info("\n✅ Machine Agent基本功能测试完成")

    except Exception as e:
        logger.error(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

    finally:
        # 清理资源
        await machine.cleanup()
        logger.info("🧹 Machine Agent测试完成，资源已清理")


async def test_machine_listener():
    """测试Machine Agent命令监听器"""
    logger.info("\n🚀 开始Machine Agent监听器测试")

    # 创建Machine Agent
    machine = await create_smart_machine(
        machine_id="test_robot_02",
        location=Position(1.0, 1.0, 0.0),
        life_value=10,
        machine_type="worker"
    )

    try:
        # 在后台启动命令监听器
        logger.info("🎧 启动命令监听器（5秒）")

        # 创建监听器任务
        listener_task = asyncio.create_task(
            machine.start_command_listener(check_interval=0.5)
        )

        # 等待一小段时间让监听器启动
        await asyncio.sleep(0.5)

        # 发送几个测试命令
        logger.info("📤 发送测试命令...")

        # 命令1: 移动
        await machine.call_tool(
            "mcp_python_send_command_to_machine",
            machine_id="test_robot_02",
            command_type="move_to",
            parameters={"position": [3.0, 2.0, 0.0]}
        )

        # 命令2: 动作
        await machine.call_tool(
            "mcp_python_send_command_to_machine",
            machine_id="test_robot_02",
            command_type="perform_action",
            parameters={"action_type": "scan", "target": "environment"}
        )

        # 让监听器运行一段时间来处理命令
        logger.info("⏳ 等待命令执行（5秒）...")
        await asyncio.sleep(5)

        # 停止监听器
        await machine.stop_command_listener()

        # 取消监听器任务
        listener_task.cancel()
        try:
            await listener_task
        except asyncio.CancelledError:
            pass

        # 检查最终状态
        result = await machine.call_tool("mcp_python_get_machine_info", machine_id="test_robot_02")
        logger.info(f"🏁 最终机器人状态: {result}")

        # 检查命令历史
        logger.info(f"📚 命令历史数量: {len(machine.command_history)}")
        for i, cmd in enumerate(machine.command_history):
            logger.info(f"  命令{i+1}: {cmd['command_type']} - {cmd.get('status', 'unknown')}")

        logger.info("\n✅ Machine Agent监听器测试完成")

    except Exception as e:
        logger.error(f"❌ 监听器测试失败: {e}")
        import traceback
        traceback.print_exc()

    finally:
        # 确保监听器停止
        await machine.stop_command_listener()
        # 清理资源
        await machine.cleanup()
        logger.info("🧹 Machine Agent监听器测试完成，资源已清理")


async def main():
    """运行所有Machine Agent测试"""
    logger.info("🎯 开始完整的Machine Agent测试套件")

    # 基本功能测试
    await test_machine_basic_functionality()

    # 等待一下
    await asyncio.sleep(1)

    # 监听器测试
    await test_machine_listener()

    logger.info("🎉 所有Machine Agent测试完成！")


if __name__ == "__main__":
    asyncio.run(main())
