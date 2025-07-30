#!/usr/bin/env python3
"""
测试连接到现有的MCP服务器
"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.logger import logger
from app.agent.human import create_human_commander


async def test_connect_existing_mcp():
    """测试连接到现有的MCP服务器"""
    logger.info("🚀 测试连接到现有的MCP服务器")

    # 创建Human Commander，连接到现有的MCP服务器
    human = await create_human_commander(
        human_id="commander_01",
        machine_count=3
    )

    try:
        # 获取所有机器状态
        logger.info("📊 获取所有机器状态...")
        machines = await human.get_all_machines()
        logger.info(f"✅ 当前机器状态: {machines}")

        # 执行简单任务
        task = "让所有机器人移动到位置(1,1,0)"
        logger.info(f"📋 执行任务: {task}")
        result = await human.run(task)
        logger.info(f"✅ 任务执行结果:\n{result}")

        # 再次获取机器状态
        logger.info("📊 获取更新后的机器状态...")
        machines = await human.get_all_machines()
        logger.info(f"✅ 更新后的机器状态: {machines}")

    except Exception as e:
        logger.error(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

    finally:
        # 清理资源
        await human.cleanup()
        logger.info("🧹 测试完成，资源已清理")


if __name__ == "__main__":
    asyncio.run(test_connect_existing_mcp())
