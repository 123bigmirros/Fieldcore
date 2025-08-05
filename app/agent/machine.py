"""
Machine Agent - 智能机器人，执行来自Human Agent的本地任务
"""

import asyncio
import json
import time
import uuid
from typing import Any, Dict, List, Optional

from pydantic import Field

from app.agent.mcp import MCPAgent
from app.agent.world_manager import Position
from app.logger import logger
from app.prompt.machine import (
    SYSTEM_PROMPT,
    NEXT_STEP_PROMPT,
    COMMAND_LISTENER_PROMPT,
    MOVE_COMMAND_PROMPT,
    ACTION_COMMAND_PROMPT,
    ENVIRONMENT_CHECK_PROMPT,
    COMMAND_ERROR_PROMPT,
    STATUS_UPDATE_PROMPT,
    LISTENER_START_PROMPT
)


class MachineAgent(MCPAgent):
    """
    智能机器人Agent - 由Human Agent直接管理

    具备以下核心能力：
    - 精确的3D空间移动控制
    - 智能环境感知和分析
    - 灵活的动作执行系统
    - 实时状态监控和报告
    - 高效的命令响应机制
    """

    name: str = "smart_machine"
    description: str = "智能机器人，能够在虚拟世界中移动并执行各种任务"

    # 使用prompt文件中的提示词
    system_prompt: str = SYSTEM_PROMPT
    next_step_prompt: str = NEXT_STEP_PROMPT

    # Agent类型
    agent_type: str = "machine"

    # 机器人特有属性
    machine_id: str = Field(default_factory=lambda: f"machine_{uuid.uuid4().hex[:8]}")
    location: Position = Field(default_factory=lambda: Position(0.0, 0.0, 0.0))
    life_value: int = Field(default=10)
    machine_type: str = Field(default="worker")
    size: float = Field(default=1.0)  # 机器人大小（碰撞检测半径）

    # 执行状态跟踪
    current_command: Optional[Dict[str, Any]] = None
    current_command_task: Optional[asyncio.Task] = None  # 当前执行的命令任务
    current_command_id: Optional[str] = None  # 当前执行的命令ID
    command_history: List[Dict[str, Any]] = Field(default_factory=list)
    is_listening: bool = False
    last_action: Optional[str] = None

    def __init__(self,
                 machine_id: Optional[str] = None,
                 location: Optional[Position] = None,
                 life_value: int = 10,
                 machine_type: str = "worker",
                 size: float = 1.0,
                 **kwargs):
        """
        直接初始化 - 不需要判断变量

        Args:
            machine_id: 机器人ID，可选
            location: 初始位置，可选
            life_value: 生命值
            machine_type: 机器人类型
            size: 机器人大小（碰撞检测半径）
        """
        super().__init__(**kwargs)

        # 设置机器人特有属性
        if machine_id:
            self.machine_id = machine_id
        if location:
            self.location = location
        self.life_value = life_value
        self.machine_type = machine_type
        self.size = size

        logger.info(f"🤖 Smart Machine {self.machine_id} 已创建 at {self.location} (size: {self.size})")

    async def initialize(self, **kwargs) -> None:
        """
        直接初始化流程 - 连接MCP并注册机器人
        """
        # 设置默认MCP连接参数
        if not kwargs:
            kwargs = {
                "connection_type": "stdio",
                "command": "python",
                "args": ["-m", "app.mcp.server"]
            }

        # 初始化MCP连接
        await super().initialize(**kwargs)

        # 直接注册机器人
        await self.register_machine()

        # 更新系统提示词
        await self.update_system_prompt()

        logger.info(f"✅ Smart Machine {self.machine_id} 初始化完成")

    async def initialize_with_shared_connection(self, shared_client) -> None:
        """
        使用共享的MCP连接初始化（用于Human Agent管理）
        """
        self.client = shared_client
        self.initialized = True

        # 更新系统提示词包含机器人信息
        await self.update_system_prompt()

        logger.info(f"✅ Smart Machine {self.machine_id} 共享连接初始化完成")

    async def register_machine(self) -> None:
        """直接注册机器人到MCP服务器"""
        try:
            result = await self.call_tool(
                "mcp_python_register_machine",
                machine_id=self.machine_id,
                position=list(self.location.coordinates),
                life_value=self.life_value,
                machine_type=self.machine_type,
                size=self.size
            )
            logger.info(f"📡 Machine {self.machine_id} 注册结果: {result}")
        except Exception as e:
            logger.warning(f"❌ 注册机器人 {self.machine_id} 失败: {e}")

    async def update_system_prompt(self) -> None:
        """更新系统提示词包含当前机器人信息"""
        x, y, z = self.location.coordinates[0], self.location.coordinates[1], self.location.coordinates[2] if len(self.location.coordinates) > 2 else 0.0
        formatted_prompt = self.system_prompt.format(
            machine_id=self.machine_id,
            machine_type=self.machine_type,
            current_position=f"({x}, {y}, {z})",
            life_value=self.life_value
        )

        from app.schema import Message
        self.memory.add_message(Message.system_message(formatted_prompt))

    async def remove_from_world(self) -> None:
        """从世界中移除机器人"""
        try:
            result = await self.call_tool(
                "mcp_python_remove_machine",
                machine_id=self.machine_id
            )
            logger.info(f"🗑️ Machine {self.machine_id} 移除结果: {result}")
        except Exception as e:
            logger.warning(f"❌ 移除机器人 {self.machine_id} 失败: {e}")

    async def cleanup(self, *args, **kwargs):
        """清理机器人资源 - 空实现，避免自动删除机器人"""
        # 不做任何实际清理，避免自动删除机器人
        pass

    def _should_finish_execution(self, name: str, **kwargs) -> bool:
        """确定工具执行是否应该结束agent"""
        # 检查生命值是否过低
        if self.life_value <= 0:
            return True

        # 调用父类方法
        return super()._should_finish_execution(name, **kwargs)

    async def start_command_listener(self) -> None:
        """启动命令监听器，处理来自Human的命令"""
        try:
            # 创建后台任务来监听命令
            import asyncio
            task = asyncio.create_task(self._listen_for_commands())
            self._command_listener_task = task
            logger.info(f"🎧 Machine {self.machine_id} 命令监听器已启动")
        except Exception as e:
            logger.error(f"启动命令监听器失败: {e}")

    async def _listen_for_commands(self) -> None:
        """监听命令队列的后台任务"""
        try:
            while True:
                try:
                    # 获取待处理的命令
                    result = await self.call_tool("mcp_python_get_machine_commands", machine_id=self.machine_id)

                    if result and hasattr(result, 'output'):
                        commands = result.output
                        if isinstance(commands, str):
                            import json
                            try:
                                commands = json.loads(commands)
                            except:
                                commands = []

                                                # 处理命令列表 - 挤占式执行（只执行最新命令）
                        if isinstance(commands, list):
                            # 找到最新的待处理命令
                            latest_command = None
                            for command_data in commands:
                                if isinstance(command_data, dict) and command_data.get("status") == "pending":
                                    latest_command = command_data

                            # 如果有新命令，执行挤占逻辑
                            if latest_command:
                                await self._preempt_and_execute_command(latest_command)

                                                # 处理命令字典（兼容旧格式）- 挤占式执行
                        elif isinstance(commands, dict):
                            # 找到最新的待处理命令
                            latest_command = None
                            latest_command_id = None
                            for command_id, command_data in commands.items():
                                if command_data.get("status") == "pending":
                                    latest_command = command_data
                                    latest_command_id = command_id

                            # 如果有新命令，执行挤占逻辑
                            if latest_command:
                                # 确保command_data包含command_id
                                latest_command["command_id"] = latest_command_id
                                await self._preempt_and_execute_command(latest_command)

                    # 等待一段时间再检查
                    await asyncio.sleep(1)

                except Exception as e:
                    logger.error(f"Machine {self.machine_id} 命令监听错误: {e}")
                    await asyncio.sleep(2)

        except asyncio.CancelledError:
            logger.info(f"Machine {self.machine_id} 命令监听器已停止")
        except Exception as e:
            logger.error(f"Machine {self.machine_id} 命令监听器异常: {e}")

    async def _preempt_and_execute_command(self, new_command_data: dict) -> None:
        """挤占式命令执行：取消当前命令，执行新命令"""
        new_command_id = new_command_data.get("command_id")

        # 如果有正在执行的命令，先取消它
        if self.current_command_task and not self.current_command_task.done():
            old_command_id = self.current_command_id
            logger.info(f"🔄 Machine {self.machine_id} 新命令 {new_command_id} 挤占旧命令 {old_command_id}")

            # 取消当前任务
            self.current_command_task.cancel()
            try:
                await self.current_command_task
            except asyncio.CancelledError:
                logger.info(f"✅ Machine {self.machine_id} 成功取消旧命令 {old_command_id}")

            # 更新旧命令状态为已取消
            if old_command_id:
                await self.call_tool("mcp_python_update_command_status",
                                   command_id=old_command_id,
                                   status="cancelled",
                                   error="Preempted by new command")

        # 执行新命令
        logger.info(f"🤖 Machine {self.machine_id} 开始执行新命令: {new_command_data}")
        self.current_command_id = new_command_id
        self.current_command = new_command_data

        # 创建新的命令执行任务
        self.current_command_task = asyncio.create_task(
            self._process_single_command(new_command_data)
        )

        # 等待命令完成（如果被取消会抛出异常）
        try:
            await self.current_command_task
        except asyncio.CancelledError:
            logger.info(f"⚡ Machine {self.machine_id} 命令 {new_command_id} 被新命令挤占")
            raise
        finally:
            # 清理状态
            if self.current_command_id == new_command_id:  # 确保是当前命令
                self.current_command_task = None
                self.current_command_id = None
                self.current_command = None

    async def _process_single_command(self, command_data: dict) -> None:
        """处理单个命令（包含状态更新）"""
        command_id = command_data.get("command_id")
        try:
            # 更新命令状态为执行中
            await self.call_tool("mcp_python_update_command_status",
                               command_id=command_id,
                               status="executing")

            # 执行命令
            await self._execute_command(command_data)

            # 更新命令状态为完成
            await self.call_tool("mcp_python_update_command_status",
                               command_id=command_id,
                               status="completed")

        except Exception as e:
            logger.error(f"Machine {self.machine_id} 处理命令 {command_id} 失败: {e}")
            # 更新命令状态为失败
            await self.call_tool("mcp_python_update_command_status",
                               command_id=command_id,
                               status="failed",
                               error=str(e))

    async def _execute_command(self, command_data: dict) -> None:
        """执行具体的命令"""
        try:
            command_type = command_data.get("command_type")
            parameters = command_data.get("parameters", {})

            logger.info(f"🤖 Machine {self.machine_id} 执行命令: {command_type}")

            if command_type == "move_to":
                # 直接移动命令
                position = parameters.get("position", [0, 0, 0])
                await self.call_tool("mcp_python_movement",
                                   machine_id=self.machine_id,
                                   coordinates=position)

            elif command_type == "step_move":
                # 逐步移动命令
                direction = parameters.get("direction", [1, 0, 0])
                distance = parameters.get("distance", 1.0)
                await self.call_tool("mcp_python_step_movement",
                                   machine_id=self.machine_id,
                                   direction=direction,
                                   distance=distance)

            elif command_type == "check_environment":
                # 检查环境命令
                await self.call_tool("mcp_python_check_environment", machine_id=self.machine_id)

            elif command_type == "laser_attack":
                # 激光攻击命令
                range_val = parameters.get("range", 5.0)
                damage = parameters.get("damage", 1)
                await self.call_tool("mcp_python_laser_attack",
                                   machine_id=self.machine_id,
                                   range=range_val,
                                   damage=damage)
                # 设置last_action以便前端检测（添加时间戳确保唯一性）
                timestamp = int(time.time() * 1000)  # 毫秒时间戳
                self.last_action = f"laser_attack(range:{range_val}, damage:{damage}, time:{timestamp})"

            elif command_type == "perform_action":
                # 兼容旧的perform_action命令，转换为具体攻击类型
                action = parameters.get("action", "")
                if action == "laser_attack":
                    range_val = parameters.get("range", 5.0)
                    damage = parameters.get("damage", 1)
                    await self.call_tool("mcp_python_laser_attack",
                                       machine_id=self.machine_id,
                                       range=range_val,
                                       damage=damage)
                    # 设置last_action以便前端检测（添加时间戳确保唯一性）
                    timestamp = int(time.time() * 1000)  # 毫秒时间戳
                    self.last_action = f"laser_attack(range:{range_val}, damage:{damage}, time:{timestamp})"
                else:
                    logger.warning(f"Machine {self.machine_id} 不支持的动作类型: {action}")

            else:
                logger.warning(f"Machine {self.machine_id} 未知命令类型: {command_type}")

        except Exception as e:
            logger.error(f"Machine {self.machine_id} 执行命令失败: {e}")

    async def stop_command_listener(self) -> None:
        """停止命令监听器"""
        if hasattr(self, '_command_listener_task') and self._command_listener_task:
            self._command_listener_task.cancel()
            try:
                await self._command_listener_task
            except asyncio.CancelledError:
                pass
            logger.info(f"🎧 Machine {self.machine_id} 命令监听器已停止")

    async def get_pending_commands(self) -> List[Dict[str, Any]]:
        """从MCP服务器获取待执行命令"""
        try:
            result = await self.call_tool("mcp_python_get_machine_commands", machine_id=self.machine_id)

            if isinstance(result, str) and result.startswith('['):
                commands = json.loads(result)
                return commands
            elif hasattr(result, 'output') and result.output:
                return json.loads(result.output)
            else:
                return []

        except Exception as e:
            logger.error(f"❌ 获取机器人 {self.machine_id} 命令失败: {e}")
            return []

    async def execute_command(self, command: Dict[str, Any]) -> None:
        """执行单个命令"""
        command_id = command.get("command_id")
        command_type = command.get("command_type")
        parameters = command.get("parameters", {})

        self.current_command = command
        logger.info(f"⚡ Machine {self.machine_id} 执行命令 {command_id}: {command_type}")

        try:
            # 更新命令状态为执行中
            await self.call_tool(
                "mcp_python_update_command_status",
                command_id=command_id,
                status="executing"
            )

            # 根据命令类型执行
            result = await self.process_command_type(command_type, parameters)

            # 更新命令状态为完成
            await self.call_tool(
                "mcp_python_update_command_status",
                command_id=command_id,
                status="completed",
                result=result
            )

            # 更新命令历史
            command["result"] = result
            command["status"] = "completed"
            self.command_history.append(command)

            logger.info(f"✅ Machine {self.machine_id} 完成命令 {command_id}: {result}")

        except Exception as e:
            error_msg = f"命令执行失败: {str(e)}"
            logger.error(f"❌ Machine {self.machine_id} 命令 {command_id} 失败: {error_msg}")

            # 添加错误处理提示
            from app.schema import Message
            self.memory.add_message(Message.system_message(
                COMMAND_ERROR_PROMPT.format(
                    command_id=command_id,
                    error_type=type(e).__name__,
                    error_message=str(e)
                )
            ))

            # 更新命令状态为失败
            await self.call_tool(
                "mcp_python_update_command_status",
                command_id=command_id,
                status="failed",
                error=error_msg
            )

        finally:
            self.current_command = None

    async def process_command_type(self, command_type: str, parameters: Dict[str, Any]) -> str:
        """处理不同类型的命令"""
        if command_type == "move_to":
            return await self.handle_move_to_command(parameters)
        elif command_type == "perform_action":
            # 兼容旧的perform_action命令，转换为具体攻击类型
            action = parameters.get("action", "")
            if action == "laser_attack":
                return await self.handle_laser_attack_command(parameters)
            else:
                return f"不支持的动作类型: {action}"
        elif command_type == "check_environment":
            return await self.handle_environment_check_command(parameters)
        elif command_type == "laser_attack":
            return await self.handle_laser_attack_command(parameters)
        else:
            return f"未知命令类型: {command_type}"

    async def handle_move_to_command(self, parameters: Dict[str, Any]) -> str:
        """处理移动命令"""
        try:
            position = parameters.get("position", [])
            if len(position) >= 2:
                x, y = position[0], position[1]
                z = position[2] if len(position) > 2 else 0.0

                # 添加移动提示
                from app.schema import Message
                current_x, current_y, current_z = self.location.coordinates[0], self.location.coordinates[1], self.location.coordinates[2] if len(self.location.coordinates) > 2 else 0.0
                self.memory.add_message(Message.system_message(
                    MOVE_COMMAND_PROMPT.format(
                        target_position=f"({x}, {y}, {z})",
                        current_position=f"({current_x}, {current_y}, {current_z})"
                    )
                ))

                # 使用MCP工具更新位置
                result = await self.call_tool(
                    "mcp_python_update_machine_position",
                    machine_id=self.machine_id,
                    new_position=[x, y, z]
                )

                # 更新本地位置
                self.location = Position(x, y, z)
                self.last_action = f"move_to({x}, {y}, {z})"

                await self.update_status()
                return f"Machine {self.machine_id} 已移动到 ({x}, {y}, {z})"
            else:
                return "无效的位置参数"

        except Exception as e:
            return f"移动命令失败: {str(e)}"

    # Note: Generic action handling removed - use specific action tools like laser_attack

    async def handle_environment_check_command(self, parameters: Dict[str, Any]) -> str:
        """处理环境检查命令"""
        try:
            check_type = parameters.get("check_type", "general")
            radius = parameters.get("radius", 3.0)

            # 添加环境检查提示
            from app.schema import Message
            current_x, current_y, current_z = self.location.coordinates[0], self.location.coordinates[1], self.location.coordinates[2] if len(self.location.coordinates) > 2 else 0.0
            self.memory.add_message(Message.system_message(
                ENVIRONMENT_CHECK_PROMPT.format(
                    check_type=check_type,
                    radius=radius,
                    current_position=f"({current_x}, {current_y}, {current_z})"
                )
            ))

            # 使用MCP工具检查环境
            result = await self.call_tool(
                "mcp_python_check_environment",
                machine_id=self.machine_id,
                radius=radius
            )

            self.last_action = f"check_environment({check_type})"
            await self.update_status()
            return f"Machine {self.machine_id} 环境检查完成 (半径: {radius})"

        except Exception as e:
            return f"环境检查失败: {str(e)}"

    async def handle_laser_attack_command(self, parameters: Dict[str, Any]) -> str:
        """处理激光攻击命令"""
        try:
            range_val = parameters.get("range", 5.0)
            damage = parameters.get("damage", 1)

            # 使用MCP工具执行激光攻击
            result = await self.call_tool(
                "mcp_python_laser_attack",
                machine_id=self.machine_id,
                range=range_val,
                damage=damage
            )

            self.last_action = f"laser_attack(range:{range_val}, damage:{damage})"
            await self.update_status()
            return f"Machine {self.machine_id} 发射激光攻击 (射程: {range_val}, 伤害: {damage})"

        except Exception as e:
            return f"激光攻击失败: {str(e)}"

    async def update_status(self) -> None:
        """更新机器人状态"""
        # 更新世界管理器中的last_action
        if self.last_action:
            try:
                await self.call_tool(
                    "mcp_python_update_machine_action",
                    machine_id=self.machine_id,
                    action=self.last_action
                )
            except Exception as e:
                logger.warning(f"Failed to update machine action: {e}")

        # 添加状态更新提示
        from app.schema import Message
        x, y, z = self.location.coordinates[0], self.location.coordinates[1], self.location.coordinates[2] if len(self.location.coordinates) > 2 else 0.0
        self.memory.add_message(Message.system_message(
            STATUS_UPDATE_PROMPT.format(
                machine_id=self.machine_id,
                new_position=f"({x}, {y}, {z})",
                life_value=self.life_value,
                last_action=self.last_action or "无"
            )
        ))

    async def run(self, request: Optional[str] = None) -> str:
        """
        运行机器人Agent或启动命令监听器
        """
        try:
            if request and request.lower() == "start_listener":
                # 启动命令监听器循环
                await self.start_command_listener()
                return f"Machine {self.machine_id} 命令监听器已启动"

            # 检查机器人是否仍然活跃
            try:
                machine_info_result = await self.call_tool("mcp_python_get_machine_info", machine_id=self.machine_id)
                if "not found" in str(machine_info_result).lower():
                    return f"Machine {self.machine_id} 不活跃"
            except Exception as e:
                logger.warning(f"检查机器人状态失败: {e}")

            # 更新系统提示词包含当前状态
            await self.update_system_prompt()

            # 添加当前状态信息
            from app.schema import Message
            self.memory.add_message(Message.system_message(
                f"🎯 当前状态：位置 {self.location}, 生命值 {self.life_value}\n"
                f"📊 执行历史：{len(self.command_history)} 个命令\n"
                f"🎧 监听状态：{'活跃' if self.is_listening else '停止'}\n"
                f"💡 请使用可用工具响应请求。"
            ))

            # 使用父类MCP agent执行
            result = await super().run(request)
            return result

        except Exception as e:
            logger.error(f"❌ Machine {self.machine_id} 执行错误: {e}")
            return f"Machine {self.machine_id} 遇到错误: {str(e)}"


# 便捷创建函数
async def create_smart_machine(machine_id: str = None,
                              location: Position = None,
                              life_value: int = 10,
                              machine_type: str = "worker",
                              size: float = 1.0) -> MachineAgent:
    """
    便捷创建和初始化Smart Machine

    Args:
        machine_id: 机器人ID
        location: 初始位置
        life_value: 生命值
        machine_type: 机器人类型
        size: 机器人大小（碰撞检测半径）

    Returns:
        已初始化的Smart Machine
    """
    machine = MachineAgent(
        machine_id=machine_id,
        location=location or Position(0.0, 0.0, 0.0),
        life_value=life_value,
        machine_type=machine_type,
        size=size
    )
    await machine.initialize()
    return machine
