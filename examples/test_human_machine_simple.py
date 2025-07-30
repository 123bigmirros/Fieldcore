"""
最简单的Human-Machine协作测试
"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.logger import logger
from app.agent.human import HumanAgent
from app.agent.world_manager import Position


async def simple_test():
    """最简单的Human-Machine协作测试"""
    logger.info("🚀 开始最简单的Human-Machine协作测试")

    # 直接创建Human Agent，让它拥有3个Machine Agent
    human = HumanAgent(
        human_id="simple_commander",
        machine_count=3
    )

    # 初始化Human Agent（会自动创建3个Machine Agent）
    await human.initialize()

    try:
        # 启动所有Machine Agent的命令监听器
        logger.info("🎧 启动所有机器人的命令监听器...")
        listener_tasks = []
        for machine_id, machine in human.machines.items():
            task = asyncio.create_task(
                machine.start_command_listener(check_interval=0.5)
            )
            listener_tasks.append(task)
            logger.info(f"  ✅ {machine_id} 监听器已启动")

        # 等待监听器启动
        await asyncio.sleep(1)

        # 命令Human让Machine排成一排
        task = "让所有机器人排成一排，间距2米，从原点开始沿x轴正方向排列"
        logger.info(f"\n📋 执行任务: {task}")

        # 创建Human执行任务
        human_task = asyncio.create_task(human.run(task))

        # 让Human执行一段时间，Machine监听器会自动处理命令
        logger.info("⏳ 等待任务执行（15秒）...")
        await asyncio.sleep(15)

        # 停止所有监听器
        logger.info("\n🛑 停止所有机器人监听器...")
        for machine_id, machine in human.machines.items():
            await machine.stop_command_listener()

        # 取消所有任务
        for task in listener_tasks:
            task.cancel()
        human_task.cancel()

        try:
            await asyncio.gather(*listener_tasks, human_task, return_exceptions=True)
        except:
            pass

        # 检查最终状态
        logger.info("\n📊 检查最终状态:")
        final_status = await human.get_all_machines()
        logger.info(f"✅ 所有机器人状态: {final_status}")

        # 检查每个机器人的详细状态
        for machine_id in human.machines.keys():
            status = await human.get_machine_status(machine_id)
            logger.info(f"🤖 {machine_id}: {status}")

        logger.info("\n🎉 测试完成！")

    except Exception as e:
        logger.error(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

    finally:
        # 确保停止所有监听器
        for machine_id, machine in human.machines.items():
            try:
                await machine.stop_command_listener()
            except:
                pass

        # 清理资源
        await human.cleanup()
        logger.info("🧹 测试完成，资源已清理")


if __name__ == "__main__":
    asyncio.run(simple_test())
