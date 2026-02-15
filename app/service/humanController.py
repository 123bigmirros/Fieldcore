# -*- coding: utf-8 -*-
"""
Human 控制器 - 封装 Human 和 Machine 的创建和管理逻辑
"""

import os
from typing import Tuple

from app.agent.human import HumanAgent
from app.logger import logger
from app.service.position_utils import find_random_valid_position


MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://localhost:8003")


class HumanController:
    """Human 控制器，负责 Human 和 Machine 的生命周期管理"""

    @staticmethod
    async def create_human_with_machines(
        human_id: str,
        machine_count: int,
        mcp_server_url: str = MCP_SERVER_URL
    ) -> Tuple[HumanAgent, int]:
        """
        创建 Human Agent 并创建指定数量的机器人

        Args:
            human_id: Human Agent 的 ID
            machine_count: 要创建的机器人数量
            mcp_server_url: MCP 服务器 URL

        Returns:
            (HumanAgent 实例, 实际创建的机器人数量)
        """
        human = HumanAgent(
            human_id=human_id,
            machine_count=0
        )

        await human.initialize(
            connection_type="http_api",
            server_url=mcp_server_url
        )

        created_count = 0
        for i in range(machine_count):
            machine_id = f"{human_id}_robot_{i+1:02d}"

            position = find_random_valid_position()
            if position:
                success = await human.create_machine_at_position(machine_id, position)
                if success:
                    created_count += 1
                    logger.info(f"✅ 机器人 {machine_id} 创建成功")
                else:
                    logger.warning(f"⚠️ 机器人 {machine_id} 创建失败")
            else:
                logger.warning(f"⚠️ 无法为机器人 {machine_id} 找到合法位置")

        return human, created_count

    @staticmethod
    async def cleanup_human(human_agent: HumanAgent) -> None:
        """清理 Human Agent"""
        try:
            await human_agent.cleanup()
            logger.info(f"🧹 Human Agent {human_agent.human_id} 清理完成")
        except Exception as e:
            logger.error(f"❌ Human Agent {human_agent.human_id} 清理失败: {e}")

    @staticmethod
    async def execute_human_command(human_agent: HumanAgent, command: str) -> str:
        """执行 Human Agent 命令"""
        try:
            result = await human_agent.run(command)
            logger.info(f"📋 Human {human_agent.human_id} 执行命令: {command}")
            return result
        except Exception as e:
            logger.error(f"❌ Human {human_agent.human_id} 命令执行失败: {e}")
            raise
