"""
Machine Command Service - 机器人命令服务层

封装机器人命令的验证、入队和执行逻辑。
提供简洁的命令管理接口。
"""

from typing import Any, Callable
from app.service.world_service import world_service
from app.service.task_queue_service import task_queue_service
from app.logger import logger


class MachineCommandService:
    """
    机器人命令服务层

    封装机器人命令相关的所有操作，包括验证、入队和执行。
    """

    def __init__(self):
        """初始化机器人命令服务"""
        logger.info("MachineCommandService initialized")

    def register_executor(self, executor: Callable):
        """
        注册命令执行器

        Args:
            executor: 命令执行函数
        """
        task_queue_service.set_task_executor(executor)
        logger.info("Machine command executor registered")

    def execute_command_async(
        self,
        machine_id: str,
        command: str,
        human_id: str = ""
    ) -> str:
        """
        异步执行机器人命令（立即返回任务ID）

        Args:
            machine_id: 机器人ID
            command: 命令内容
            human_id: 所有者ID

        Returns:
            str: 任务ID

        Raises:
            ValueError: 机器人不存在
        """
        # 验证机器人是否存在
        self._validate_machine(machine_id)

        # 异步入队
        job_id = task_queue_service.enqueue_task(
            machine_id=machine_id,
            command=command,
            human_id=human_id
        )

        logger.info(f"✅ Command queued for machine {machine_id} (job: {job_id})")
        return job_id

    def execute_command_sync(
        self,
        machine_id: str,
        command: str,
        human_id: str = "",
        timeout: int = 300
    ) -> Any:
        """
        同步执行机器人命令（等待完成并返回结果）

        Args:
            machine_id: 机器人ID
            command: 命令内容
            human_id: 所有者ID
            timeout: 超时时间（秒）

        Returns:
            Any: 命令执行结果

        Raises:
            ValueError: 机器人不存在
            TimeoutError: 执行超时
            Exception: 执行失败
        """
        # 验证机器人是否存在
        self._validate_machine(machine_id)

        # 同步执行（等待完成）
        result = task_queue_service.enqueue_and_wait(
            machine_id=machine_id,
            command=command,
            human_id=human_id,
            wait_timeout=timeout
        )

        logger.info(f"✅ Command completed for machine {machine_id}")
        return result

    def execute_command(
        self,
        machine_id: str,
        command: str,
        offline: bool = True,
        human_id: str = ""
    ) -> Any:
        """
        执行机器人命令（统一接口）

        Args:
            machine_id: 机器人ID
            command: 命令内容
            offline: 是否异步执行（True=异步，False=同步）
            human_id: 所有者ID

        Returns:
            Any: 如果异步返回任务ID，如果同步返回执行结果

        Raises:
            ValueError: 机器人不存在
            TimeoutError: 同步模式下超时
            Exception: 执行失败
        """
        if offline:
            return self.execute_command_async(machine_id, command, human_id)
        else:
            return self.execute_command_sync(machine_id, command, human_id)

    def _validate_machine(self, machine_id: str):
        """
        验证机器人是否存在

        Args:
            machine_id: 机器人ID

        Raises:
            ValueError: 机器人不存在
        """
        if not world_service.machine_exists(machine_id):
            raise ValueError(f"Machine {machine_id} not found in world registry")

    def get_command_status(self, job_id: str) -> str:
        """
        获取命令执行状态

        Args:
            job_id: 任务ID

        Returns:
            str: 任务状态
        """
        status = task_queue_service.get_job_status(job_id)
        return status or "unknown"

    def get_command_result(self, job_id: str) -> Any:
        """
        获取命令执行结果

        Args:
            job_id: 任务ID

        Returns:
            Any: 任务结果，如果未完成则返回 None
        """
        return task_queue_service.get_job_result(job_id)


# 全局机器人命令服务实例
machine_command_service = MachineCommandService()
