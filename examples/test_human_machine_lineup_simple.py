"""
障碍物环境测试 - 创建带有障碍物的测试环境
"""

import asyncio
import sys
import os
import random
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.logger import logger
from app.agent.human import create_human_commander


async def create_obstacle_environment(human):
    """创建障碍物环境：外围正方形 + 内部随机障碍物"""
    logger.info("🏗️ 创建障碍物环境...")

    # 清理现有障碍物
    await human.call_tool("mcp_python_clear_all_obstacles")

    # 创建外围正方形障碍物 (边长约30单位，无间隙)
    wall_size = 15
    wall_thickness = 1.5  # 增加障碍物厚度，确保无法穿越

    obstacles = []

    # 上边墙 - 连续无间隙
    for i in range(-wall_size, wall_size + 1, 1):  # 改为step=1，无间隙
        obstacles.append(("wall_top_" + str(i), [i, wall_size, 0], wall_thickness))

    # 下边墙 - 连续无间隙
    for i in range(-wall_size, wall_size + 1, 1):  # 改为step=1，无间隙
        obstacles.append(("wall_bottom_" + str(i), [i, -wall_size, 0], wall_thickness))

    # 左边墙 - 连续无间隙，完全覆盖角落
    for i in range(-wall_size, wall_size + 1, 1):  # 完全覆盖，包括角落
        obstacles.append(("wall_left_" + str(i), [-wall_size, i, 0], wall_thickness))

    # 右边墙 - 连续无间隙，完全覆盖角落
    for i in range(-wall_size, wall_size + 1, 1):  # 完全覆盖，包括角落
        obstacles.append(("wall_right_" + str(i), [wall_size, i, 0], wall_thickness))

    # 在内部添加随机障碍物
    random.seed(42)  # 固定随机种子，确保可重现
    inner_obstacles = []
    for i in range(20):  # 添加20个随机障碍物
        while True:
            x = random.randint(-wall_size + 3, wall_size - 3)
            y = random.randint(-wall_size + 3, wall_size - 3)

            # 确保不在原点附近（为机器人创建留出空间）
            if abs(x) > 3 or abs(y) > 3:
                inner_obstacles.append((f"inner_obstacle_{i}", [x, y, 0], wall_thickness))
                break

    obstacles.extend(inner_obstacles)

    # 创建所有障碍物
    created_count = 0
    for obstacle_id, position, size in obstacles:
        try:
            result = await human.call_tool(
                "mcp_python_add_obstacle",
                obstacle_id=obstacle_id,
                position=position,
                size=size,
                obstacle_type="static"
            )
            if "successfully" in str(result):
                created_count += 1
        except Exception as e:
            logger.warning(f"创建障碍物 {obstacle_id} 失败: {e}")

    logger.info(f"✅ 成功创建了 {created_count} 个障碍物")

    # 验证边界完整性 - 重点测试上下边界
    logger.info("🔍 验证边界完整性...")
    boundary_test_positions = [
        # 上下边界测试（重点）
        [0, wall_size + 0.5, 0],         # 上边界外
        [0, -wall_size - 0.5, 0],        # 下边界外
        [wall_size//2, wall_size + 0.5, 0],    # 上边界外-右侧
        [-wall_size//2, wall_size + 0.5, 0],   # 上边界外-左侧
        [wall_size//2, -wall_size - 0.5, 0],   # 下边界外-右侧
        [-wall_size//2, -wall_size - 0.5, 0],  # 下边界外-左侧
        # 角落测试
        [wall_size + 0.5, wall_size + 0.5, 0],      # 右上角外
        [-wall_size - 0.5, wall_size + 0.5, 0],     # 左上角外
        [wall_size + 0.5, -wall_size - 0.5, 0],     # 右下角外
        [-wall_size - 0.5, -wall_size - 0.5, 0],    # 左下角外
        # 左右边界测试
        [wall_size + 0.5, 0, 0],         # 右边界外
        [-wall_size - 0.5, 0, 0],        # 左边界外
        # 内部安全位置测试
        [0, 0, 0],                       # 中心
        [wall_size - 1, 0, 0],           # 右边界内
        [-wall_size + 1, 0, 0],          # 左边界内
        [0, wall_size - 1, 0],           # 上边界内
        [0, -wall_size + 1, 0],          # 下边界内
    ]

    # 分类显示边界检查结果
    up_down_issues = []
    left_right_issues = []
    corner_issues = []

    for pos in boundary_test_positions:
        try:
            collision_result = await human.call_tool(
                "mcp_python_check_collision",
                position=pos,
                size=1.0
            )
            import json
            collision_info = json.loads(collision_result.output if hasattr(collision_result, 'output') else str(collision_result))
            is_blocked = collision_info.get("collision", False)
            status = "🔒 被阻挡" if is_blocked else "⚠️  可通过"

            # 分类问题
            x, y = pos[0], pos[1]
            if not is_blocked:  # 只记录有问题的位置
                if abs(y) > wall_size:  # 上下边界问题
                    up_down_issues.append(f"({x}, {y})")
                elif abs(x) > wall_size:  # 左右边界问题
                    left_right_issues.append(f"({x}, {y})")
                elif abs(x) > wall_size and abs(y) > wall_size:  # 角落问题
                    corner_issues.append(f"({x}, {y})")

            logger.info(f"  位置 {pos}: {status}")
        except Exception as e:
            logger.warning(f"  检查位置 {pos} 失败: {e}")

    # 汇总报告
    logger.info("📋 边界检查汇总:")
    if up_down_issues:
        logger.warning(f"  ⚠️  上下边界问题: {', '.join(up_down_issues)}")
    else:
        logger.info("  ✅ 上下边界完好")

    if left_right_issues:
        logger.warning(f"  ⚠️  左右边界问题: {', '.join(left_right_issues)}")
    else:
        logger.info("  ✅ 左右边界完好")

    if corner_issues:
        logger.warning(f"  ⚠️  角落边界问题: {', '.join(corner_issues)}")
    else:
        logger.info("  ✅ 角落边界完好")

    return created_count


async def find_safe_positions(human, count=5):
    """找到安全的机器人初始位置"""
    safe_positions = []
    attempts = 0
    max_attempts = 100

    while len(safe_positions) < count and attempts < max_attempts:
        attempts += 1
        # 在原点附近寻找安全位置
        x = random.randint(-2, 2)
        y = random.randint(-2, 2)
        z = 0

        # 检查这个位置是否安全
        try:
            collision_result = await human.call_tool(
                "mcp_python_check_collision",
                position=[x, y, z],
                size=1.0
            )

            if hasattr(collision_result, 'output'):
                collision_data = collision_result.output
            else:
                collision_data = str(collision_result)

            # 解析碰撞结果
            import json
            try:
                collision_info = json.loads(collision_data)
                if not collision_info.get("collision", True):
                    safe_positions.append([x, y, z])
                    logger.info(f"找到安全位置: ({x}, {y}, {z})")
            except:
                pass

        except Exception as e:
            logger.warning(f"检查位置 ({x}, {y}, {z}) 失败: {e}")

    logger.info(f"找到 {len(safe_positions)} 个安全位置")
    return safe_positions


async def test_obstacle_environment():
    """测试障碍物环境中的机器人导航"""
    logger.info("🚀 开始障碍物环境测试")
    logger.info("🔧 边界问题修复说明:")
    logger.info("  - 已修复墙体间隙问题 (step=1, 连续墙体)")
    logger.info("  - 增加墙体厚度 (1.5) 防止穿越")
    logger.info("  - 🎯 重点修复上下边界: 左右墙完全覆盖角落")
    logger.info("  - 📊 添加分类边界完整性验证")
    logger.info("  - 🔍 实时监控边界状态")
    logger.info("📡 连接到现有的MCP服务器...")

    # 创建Human Commander，先不创建机器人
    human = await create_human_commander(
        human_id="obstacle_commander",
        machine_count=0,  # 先不创建机器人
        mcp_connection_params={
            "connection_type": "http_api",
            "server_url": "http://localhost:8003"
        }
    )

    try:
        # 创建障碍物环境
        obstacle_count = await create_obstacle_environment(human)

        # 找到安全位置
        safe_positions = await find_safe_positions(human, count=5)

        if not safe_positions:
            logger.error("❌ 没有找到安全位置来放置机器人")
            return

        # 手动创建机器人在安全位置
        from app.agent.machine import MachineAgent
        from app.agent.world_manager import Position

        for i, position in enumerate(safe_positions):
            machine_id = f"{i+1:02d}"  # 只使用数字编码

            # 创建机器人Agent实例
            machine = MachineAgent(
                machine_id=machine_id,
                location=Position(*position),
                life_value=10,
                machine_type="worker",
                size=1.0,
                agent_type="machine"
            )

            # 共享Human Agent的MCP连接
            machine.mcp_clients = human.mcp_clients
            machine.available_tools = human.available_tools

            # 注册机器人
            await machine.register_machine()
            await machine.start_command_listener()

            # 添加到管理列表
            human.machines[machine_id] = machine

            logger.info(f"  🤖 创建机器人 {machine_id} 在位置 {position}")

        # 显示环境状态
        machines_result = await human.get_all_machines()
        obstacles_result = await human.call_tool("mcp_python_get_all_obstacles")

        logger.info(f"📊 当前环境状态:")
        logger.info(f"  - 障碍物数量: {obstacle_count}")
        logger.info(f"  - 机器人数量: {len(safe_positions)}")

        # 测试导航任务
        logger.info("\n🎯 开始导航测试...")
        test_tasks = [
            "让所有机器人移动到各自附近的安全位置",
            "检查所有机器人的状态",
            "让01号机器人尝试找到一条到达(5,5,0)的路径",
        ]

        # for task in test_tasks:
        #     logger.info(f"\n📋 执行任务: {task}")
        #     try:
        #         result = await human.run(task)
        #         logger.info(f"✅ 任务结果: {result}")
        #     except Exception as e:
        #         logger.error(f"❌ 任务失败: {e}")

        # 连续命令输入循环
        logger.info("\n🔄 进入连续命令模式，输入 'quit' 或 'exit' 退出")
        logger.info("💡 可用命令示例:")
        logger.info("  - '让01号机器人移动到位置(3,3,0)'")
        logger.info("  - '让所有机器人聚集到原点附近'")
        logger.info("  - '检查所有机器人的状态'")
        logger.info("  - '让02号和03号机器人交换位置'")

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

                # 显示当前状态并检查边界
                final_status = await human.get_all_machines()
                logger.info(f"📊 当前状态: {final_status}")

                # 检查是否有机器人越界
                try:
                    import json
                    if hasattr(final_status, 'output'):
                        machines_data = json.loads(final_status.output)
                    else:
                        machines_data = json.loads(str(final_status))

                    wall_size = 15  # 与创建环境时保持一致
                    out_of_bounds = []
                    for machine_id, machine_info in machines_data.items():
                        pos = machine_info.get('position', [0, 0, 0])
                        x, y = pos[0], pos[1]
                        if abs(x) > wall_size - 1 or abs(y) > wall_size - 1:
                            out_of_bounds.append(f"机器人 {machine_id} 位置 ({x}, {y})")

                    if out_of_bounds:
                        logger.warning(f"⚠️  边界警告: {'; '.join(out_of_bounds)} 接近或越过边界!")
                    else:
                        logger.info("✅ 所有机器人都在边界内")

                except Exception as e:
                    logger.debug(f"边界检查失败: {e}")

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
        # 保持环境运行状态
        logger.info("✅ 测试完成，环境保持运行状态")
        logger.info("🌐 前端地址: http://localhost:3000")
        logger.info("💡 机器人和障碍物将在前端显示")


if __name__ == "__main__":
    asyncio.run(test_obstacle_environment())
