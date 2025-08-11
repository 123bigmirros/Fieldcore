"""
Human Agent - 智能指挥官，负责分解任务并协调多个机器人完成任务
"""

import json
import uuid
from typing import Any, Dict, List, Optional

from pydantic import Field

from app.agent.mcp import MCPAgent
from app.logger import logger
from app.prompt.human import (
    SYSTEM_PROMPT,
    NEXT_STEP_PROMPT,
    TASK_ANALYSIS_PROMPT,
    COMMAND_ERROR_PROMPT,
    TASK_COMPLETION_PROMPT,
    MACHINE_DISCOVERY_PROMPT
)


class HumanAgent(MCPAgent):
    """
    智能Human Agent - 直接创建和管理Machine Agent
    """

    name: str = "human_commander"
    description: str = "智能指挥官，负责协调和控制多个机器人完成复杂任务"

    # 使用prompt文件中的提示词
    system_prompt: str = SYSTEM_PROMPT
    next_step_prompt: str = NEXT_STEP_PROMPT

    # Agent类型
    agent_type: str = "human"

    # Human特有属性
    human_id: str = Field(default_factory=lambda: f"commander_{uuid.uuid4().hex[:8]}")

    # 直接拥有Machine Agent实例
    machines: Dict[str, Any] = Field(default_factory=dict)  # machine_id -> MachineAgent实例
    machine_info_cache: Dict[str, Any] = Field(default_factory=dict)

    # 执行状态跟踪
    current_task: Optional[str] = None
    active_commands: Dict[str, str] = Field(default_factory=dict)  # command_id -> machine_id

    def __init__(self,
                 human_id: Optional[str] = None,
                 machine_count: int = 3,
                 **kwargs):
        """
        直接初始化 - 不需要判断变量

        Args:
            human_id: 指挥官ID，可选
            machine_count: 要创建的机器人数量
        """
        super().__init__(**kwargs)

        if human_id:
            self.human_id = human_id

        self.machine_count = machine_count

        logger.info(f"🤖 Human Commander {self.human_id} 已创建，将管理 {machine_count} 个机器人")

    async def initialize(self, **kwargs) -> None:
        """
        直接初始化流程 - 连接到MCP服务器并创建机器人
        """
        connection_type = kwargs.get("connection_type", "http_api")

        if connection_type == "internal":
            # 内部连接模式 - 直接使用服务器实例
            server_instance = kwargs.get("server_instance")
            if server_instance:
                self.mcp_clients = {"internal": server_instance}
                self.available_tools = list(server_instance.tools.keys())
                logger.info(f"Human Commander {self.human_id} 使用内部连接模式")
            else:
                raise ValueError("Internal connection requires server_instance")
        else:
            # 外部连接模式
            if not kwargs or connection_type == "http_api":
                kwargs = {
                    "connection_type": "http_api",
                    "server_url": "http://localhost:8003"
                }
            # 初始化MCP连接
            await super().initialize(**kwargs)

        # 直接创建并添加机器人
        await self.create_machines()

        logger.info(f"✅ Human Commander {self.human_id} 初始化完成，机器人由MCP服务器管理")

    async def create_machines(self) -> None:
        """在MCP服务器中注册机器人，不再在Human Agent本地创建Machine Agent实例"""
        try:
            from app.agent.world_manager import Position
            import random

            # 如果machine_count为0，则不创建机器人
            if self.machine_count == 0:
                logger.info("🤖 Human Agent 不创建本地机器人，机器人将由MCP服务器管理")
                return

            # 寻找安全位置来放置机器人
            safe_positions = await self._find_safe_positions(self.machine_count)

            if len(safe_positions) < self.machine_count:
                logger.warning(f"⚠️  只找到 {len(safe_positions)} 个安全位置，但需要 {self.machine_count} 个位置")

            for i in range(self.machine_count):
                machine_id = f"robot_{i+1:02d}"

                # 为每个机器人分配不同的位置
                if i < len(safe_positions):
                    position = Position(*safe_positions[i])
                else:
                    # 如果安全位置不够，使用随机位置
                    position = Position(
                        random.uniform(-5.0, 5.0),
                        random.uniform(-5.0, 5.0),
                        0.0
                    )
                    logger.warning(f"⚠️  机器人 {machine_id} 使用随机位置: {position}")

                # 为每个机器人设置4个基本方向之一（上下左右）
                directions = [
                    (1.0, 0.0),   # 右 (东)
                    (0.0, 1.0),   # 上 (北)
                    (-1.0, 0.0),  # 左 (西)
                    (0.0, -1.0)   # 下 (南)
                ]
                facing_direction = directions[i % 4]  # 循环分配4个方向

                # 只在世界中注册机器人，不创建本地Agent实例
                result = await self.call_tool(
                    "mcp_python_register_machine",
                    machine_id=machine_id,
                    position=list(position.coordinates),
                    life_value=10,
                    machine_type="worker",
                    size=1.0,
                    facing_direction=list(facing_direction)
                )

                logger.info(f"  🤖 在世界中注册机器人: {machine_id} 在位置 {position}")

        except Exception as e:
            logger.error(f"创建机器人失败: {e}")

    async def _find_safe_positions(self, count: int) -> List[List[float]]:
        """找到安全的机器人初始位置"""
        safe_positions = []
        attempts = 0
        max_attempts = 50

        # 定义搜索范围
        search_range = 3

        while len(safe_positions) < count and attempts < max_attempts:
            attempts += 1

            # 在原点附近搜索安全位置
            import random
            x = random.randint(-search_range, search_range)
            y = random.randint(-search_range, search_range)
            z = 0

            # 检查这个位置是否已被占用
            position_taken = False
            for existing_pos in safe_positions:
                if abs(existing_pos[0] - x) < 1.0 and abs(existing_pos[1] - y) < 1.0:
                    position_taken = True
                    break

            if position_taken:
                continue

            # 检查这个位置是否与世界中的对象碰撞
            try:
                collision_result = await self.call_tool(
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
                    # 如果解析失败，假设位置安全
                    safe_positions.append([x, y, z])
                    logger.info(f"找到位置（解析失败，假设安全）: ({x}, {y}, {z})")

            except Exception as e:
                logger.warning(f"检查位置 ({x}, {y}, {z}) 失败: {e}")
                # 继续尝试其他位置

        logger.info(f"找到 {len(safe_positions)} 个安全位置（目标: {count}）")
        return safe_positions

    async def _register_machines_to_control_tool(self):
        """将创建的机器人注册到control_machine工具中"""
        try:
            # 查找control_machine工具
            control_tool = None
            if hasattr(self, 'available_tools') and 'control_machine' in self.available_tools:
                control_tool = self.available_tools['control_machine']
            elif hasattr(self, 'mcp_clients'):
                # 在MCP客户端中查找
                for client in self.mcp_clients.values():
                    if hasattr(client, 'available_tools') and 'control_machine' in client.available_tools:
                        control_tool = client.available_tools['control_machine']
                        break

            if control_tool and hasattr(control_tool, 'register_machine_agent'):
                for machine_id, machine in self.machines.items():
                    control_tool.register_machine_agent(machine_id, machine)
                    logger.info(f"  📡 已注册机器人 {machine_id} 到control_machine工具")
            else:
                logger.warning("未找到control_machine工具或不支持机器人注册")

        except Exception as e:
            logger.warning(f"注册机器人到control_machine工具失败: {e}")

    async def send_command_to_machine(self, machine_id: str, command_type: str, parameters: dict = None) -> dict:
        """向机器人发送命令"""
        try:
            result = await self.call_tool(
                "mcp_python_send_command_to_machine",
                machine_id=machine_id,
                command_type=command_type,
                parameters=parameters or {}
            )

            if hasattr(result, 'output') and result.output:
                # 尝试解析command_id用于跟踪
                try:
                    result_data = json.loads(result.output)
                    command_id = result_data.get("command_id")
                    if command_id:
                        self.active_commands[command_id] = machine_id
                except:
                    pass
                return {"status": "success", "data": result.output}
            else:
                return {"status": "success", "data": str(result)}
        except Exception as e:
            # 添加错误处理提示
            from app.schema import Message
            self.memory.add_message(Message.system_message(
                COMMAND_ERROR_PROMPT.format(error=str(e))
            ))
            return {"status": "error", "message": str(e)}

    async def wait_for_command_completion(self, command_id: str, timeout: int = 30) -> dict:
        """等待命令完成"""
        try:
            result = await self.call_tool(
                "mcp_python_wait_for_command_completion",
                command_id=command_id,
                timeout=timeout
            )

            # 从活动命令列表中移除已完成的命令
            if command_id in self.active_commands:
                del self.active_commands[command_id]

            # 从ToolResult中提取output
            data = result.output if hasattr(result, 'output') else str(result)
            return {"status": "success", "data": data}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    async def get_machine_status(self, machine_id: str) -> dict:
        """获取机器人状态"""
        try:
            result = await self.call_tool("mcp_python_get_machine_info", machine_id=machine_id)
            # 从ToolResult中提取output
            data = result.output if hasattr(result, 'output') else str(result)
            return {"status": "success", "data": data}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    async def call_tool(self, tool_name: str, **kwargs) -> Any:
        """重写call_tool方法以支持内部连接模式"""
        if "internal" in self.mcp_clients:
            # 内部连接模式 - 直接调用服务器方法
            server_instance = self.mcp_clients["internal"]
            try:
                result = await server_instance.server.call_tool(tool_name, kwargs)
                return result
            except Exception as e:
                logger.error(f"Error calling tool '{tool_name}' internally: {e}")
                raise
        else:
            # 外部连接模式 - 使用父类方法
            return await super().call_tool(tool_name, **kwargs)

    async def get_all_machines(self) -> dict:
        """获取所有机器人状态"""
        try:
            result = await self.call_tool("mcp_python_get_all_machines")
            # 从ToolResult中提取output
            data = result.output if hasattr(result, 'output') else str(result)
            return {"status": "success", "data": data}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    async def analyze_task(self, task: str) -> None:
        """分析任务并添加分析提示"""
        from app.schema import Message
        self.memory.add_message(Message.system_message(
            TASK_ANALYSIS_PROMPT.format(task=task)
        ))
        self.current_task = task

    async def complete_task_verification(self) -> None:
        """添加任务完成验证提示"""
        from app.schema import Message
        self.memory.add_message(Message.system_message(TASK_COMPLETION_PROMPT))

    async def run(self, request: Optional[str] = None) -> str:
        """
        直接处理自然语言指令
        """
        try:
            logger.info(f"🎯 Human Commander {self.human_id} 接收任务: {request}")

            # 更新机器人信息缓存
            await self.update_machine_cache()

            # 分析任务
            if request:
                await self.analyze_task(request)

            # 构建当前状态信息
            status_info = "机器人由MCP服务器管理"
            active_commands_info = f"活动命令数: {len(self.active_commands)}"

            # 添加状态消息
            from app.schema import Message
            self.memory.add_message(Message.system_message(
                f"🎯 当前任务状态：{status_info}\n"
                f"📊 执行状态：{active_commands_info}\n"
                f"📋 任务要求：{request}\n\n"
                f"💡 请使用可用工具分析当前状态并执行任务。"
            ))

            # 使用父类的智能执行
            result = await super().run(request)

            # 任务完成后进行验证
            await self.complete_task_verification()

            logger.info(f"✅ Human Commander {self.human_id} 任务完成")
            return result

        except Exception as e:
            logger.error(f"❌ Human Commander {self.human_id} 执行错误: {e}")
            return f"Human Commander {self.human_id} 遇到错误: {str(e)}"

    async def update_machine_cache(self) -> None:
        """更新机器人信息缓存（从MCP服务器获取所有机器人）"""
        try:
            # 获取所有机器人信息
            result = await self.call_tool("mcp_python_get_all_machines")
            result_str = result.output if hasattr(result, 'output') and result.output else str(result)

            if result and "error" not in result_str.lower():
                try:
                    all_machines = json.loads(result_str)
                    self.machine_info_cache = all_machines
                    logger.info(f"✅ 更新了 {len(all_machines)} 个机器人的信息缓存")
                except json.JSONDecodeError:
                    logger.warning("无法解析机器人信息")
            else:
                logger.warning("无法获取机器人信息")
        except Exception as e:
            logger.warning(f"更新机器人信息缓存失败: {e}")

    async def recycle_all_machines(self) -> None:
        """
        回收机器人（现在机器人由MCP服务器管理，这里只是一个占位符）
        """
        logger.info(f"♻️ Human Commander {self.human_id} 清理完成（机器人由MCP服务器管理）")

    async def cleanup(self, *args, **kwargs):
        """清理资源 - 空实现，避免自动删除机器人"""
        # 不做任何实际清理，避免自动删除机器人
        pass


# 便捷创建函数
async def create_human_commander(human_id: str = None,
                               machine_count: int = 3,
                               mcp_connection_params: dict = None) -> HumanAgent:
    """
    便捷创建和初始化Human Commander

    Args:
        human_id: 指挥官ID
        machine_count: 要创建的机器人数量
        mcp_connection_params: MCP连接参数，如果为None则使用默认参数

    Returns:
        已初始化的Human Commander
    """
    commander = HumanAgent(
        human_id=human_id,
        machine_count=machine_count
    )

    if mcp_connection_params:
        await commander.initialize(**mcp_connection_params)
    else:
        await commander.initialize()

    return commander
