"""
简化的Human-Machine协作测试 - Human直接拥有和管理Machine Agent
支持连续命令输入
"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.logger import logger
from app.agent.human import create_human_commander


async def test_simple_human_machine_lineup():
    """测试Human Agent直接创建和管理Machine Agent进行排队"""
    logger.info("🚀 开始简化的Human-Machine协作测试")
    logger.info("📡 连接到现有的MCP服务器...")

    # 创建Human Commander，连接到现有的MCP服务器
    human = await create_human_commander(
        human_id="commander_01",
        machine_count=3,
        mcp_connection_params={
            "connection_type": "http_api",
            "server_url": "http://localhost:8003"
        }
    )

    try:
        # 执行初始排队任务
        initial_task = "让所有机器人排成一排，间距2米，从原点开始沿x轴正方向排列"
        logger.info(f"📋 执行初始任务: {initial_task}")
        result = await human.run(initial_task)
        logger.info(f"✅ 初始任务执行结果:\n{result}")

        # 连续命令输入循环
        logger.info("🔄 进入连续命令模式，输入 'quit' 或 'exit' 退出")
        logger.info("💡 可用命令示例:")
        logger.info("  - '让机器人1移动到位置(5,0,0)'")
        logger.info("  - '让所有机器人移动到y=2的位置'")
        logger.info("  - '检查所有机器人的状态'")
        logger.info("  - '让机器人2和机器人3交换位置'")

        while True:
            try:
                # 获取用户输入
                command = input("\n🤖 请输入命令 (或 'quit' 退出): ").strip()

                if command.lower() in ['quit', 'exit', 'q']:
                    logger.info("👋 退出连续命令模式")
                    break

                if not command:
                    continue

                # 执行命令
                logger.info(f"📋 执行命令: {command}")
                result = await human.run(command)
                logger.info(f"✅ 执行结果:\n{result}")

                # 显示当前状态
                final_status = await human.get_all_machines()
                logger.info(f"📊 当前状态: {final_status}")

            except KeyboardInterrupt:
                logger.info("\n👋 用户中断，退出程序")
                break
            except Exception as e:
                logger.error(f"❌ 命令执行失败: {e}")
                continue

    except Exception as e:
        logger.error(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

    finally:
        # 清理资源
        await human.cleanup()
        logger.info("🧹 测试完成，资源已清理")


if __name__ == "__main__":
    asyncio.run(test_simple_human_machine_lineup())
