"""
Human控制器 - 封装Human和Machine的创建和管理逻辑
"""

import json
import random
from typing import Tuple, Optional

from app.agent.human import HumanAgent
from app.logger import logger


class HumanController:
    """Human控制器，负责Human和Machine的生命周期管理"""

    @staticmethod
    async def find_random_valid_position(human_agent: HumanAgent, max_attempts: int = 50) -> Optional[list]:
        """
        在地图范围内找到一个合法的随机位置

        Args:
            human_agent: Human Agent实例
            max_attempts: 最大尝试次数

        Returns:
            合法位置的坐标列表 [x, y, z]，如果找不到则返回None
        """
        map_range = 14

        for _ in range(max_attempts):
            # 生成随机坐标
            x = random.randint(-map_range + 1, map_range - 1)
            y = random.randint(-map_range + 1, map_range - 1)
            position = [float(x), float(y), 0.0]

            # 检查位置是否合法（无碰撞）
            try:
                result = await human_agent.call_tool("mcp_python_check_collision",
                                                   position=position, size=1.0)
                # 解析检查结果 - HTTPMCPTool返回嵌套JSON
                if hasattr(result, 'output'):
                    # 第一层解析：ToolResult.output -> dict
                    outer_data = json.loads(result.output)
                    # 第二层解析：dict['output'] -> 碰撞检测结果
                    if outer_data.get('output'):
                        collision_data = json.loads(outer_data['output'])
                        if not collision_data.get('collision', True):  # 无碰撞
                            return position
            except Exception as e:
                logger.warning(f"位置检查失败 {position}: {e}")
                continue

        logger.error(f"尝试了 {max_attempts} 次都无法找到合法位置")
        return None

    @staticmethod
    async def create_human_with_machines(human_id: str,
                                       machine_count: int,
                                       mcp_server_url: str = "http://localhost:8003") -> Tuple[HumanAgent, int]:
        """
        创建Human Agent并创建指定数量的机器人

        Args:
            human_id: Human Agent的ID
            machine_count: 要创建的机器人数量
            mcp_server_url: MCP服务器URL

        Returns:
            (HumanAgent实例, 实际创建的机器人数量)
        """
        # 创建Human Agent（不自动创建机器人）
        human = HumanAgent(
            human_id=human_id,
            machine_count=0  # 不让Human Agent自动创建机器人
        )

        # 初始化连接到MCP服务器
        await human.initialize(
            connection_type="http_api",
            server_url=mcp_server_url
        )

        # 在随机位置创建机器人并立即注册
        created_count = 0
        for i in range(machine_count):
            machine_id = f"{human_id}_robot_{i+1:02d}"

            # 找到合法的随机位置
            position = await HumanController.find_random_valid_position(human)
            if position:
                success = await human.create_machine_at_position(machine_id, position)
                if success:
                    # 创建成功，立即注册到MCP控制系统
                    try:
                        await human.call_tool("mcp_python_register_machine_control", machine_id=machine_id)
                        created_count += 1
                        logger.info(f"🤖 为 {human_id} 创建机器人 {machine_id} 在位置 {position}")
                        logger.info(f"✅ 注册机器人 {machine_id} 到MCP控制系统 (owner: {human_id})")
                    except Exception as e:
                        logger.error(f"❌ 注册机器人 {machine_id} 失败: {e}")
                else:
                    logger.warning(f"⚠️ 机器人 {machine_id} 创建失败")
            else:
                logger.warning(f"⚠️ 无法为机器人 {machine_id} 找到合法位置")

        return human, created_count

    @staticmethod
    async def cleanup_human(human_agent: HumanAgent) -> None:
        """
        清理Human Agent

        Args:
            human_agent: 要清理的Human Agent实例
        """
        try:
            await human_agent.cleanup()
            logger.info(f"🧹 Human Agent {human_agent.human_id} 清理完成")
        except Exception as e:
            logger.error(f"❌ Human Agent {human_agent.human_id} 清理失败: {e}")

    @staticmethod
    async def execute_human_command(human_agent: HumanAgent, command: str) -> str:
        """
        执行Human Agent命令

        Args:
            human_agent: Human Agent实例
            command: 要执行的命令

        Returns:
            命令执行结果
        """
        try:
            result = await human_agent.run(command)
            logger.info(f"📋 Human {human_agent.human_id} 执行命令: {command}")
            return result
        except Exception as e:
            logger.error(f"❌ Human {human_agent.human_id} 命令执行失败: {e}")
            raise
