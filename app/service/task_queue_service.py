"""
Task Queue Service - 任务队列服务层

封装 Redis + RQ 队列操作，提供统一的任务管理接口。
"""

import asyncio
import time
from typing import Any, Callable, Optional, Dict
import redis
from rq import Queue
from app.logger import logger


class TaskQueueService:
    """
    任务队列服务层

    封装 Redis 和 RQ 队列的操作，提供高层次的任务管理接口。
    """

    def __init__(
        self,
        redis_host: str = 'localhost',
        redis_port: int = 6379,
        redis_db: int = 0,
        queue_name: str = 'machine_commands'
    ):
        """
        初始化任务队列服务

        Args:
            redis_host: Redis 主机地址
            redis_port: Redis 端口
            redis_db: Redis 数据库编号
            queue_name: 队列名称
        """
        # 初始化 Redis 连接
        self.redis_conn = redis.Redis(
            host=redis_host,
            port=redis_port,
            db=redis_db,
            decode_responses=False  # RQ 需要 False 来避免编码问题
        )

        # 初始化任务队列
        self.task_queue = Queue(queue_name, connection=self.redis_conn)

        # 存储任务执行器的引用
        self._task_executor: Optional[Callable] = None

        logger.info(f"TaskQueueService initialized (queue: {queue_name})")

    def set_task_executor(self, executor: Callable):
        """
        设置任务执行器

        Args:
            executor: 任务执行函数，接收 (machine_id, command, human_id) 参数
        """
        self._task_executor = executor
        logger.info("Task executor registered")

    def enqueue_task(
        self,
        machine_id: str,
        command: str,
        human_id: str = "",
        job_timeout: str = '5m'
    ) -> str:
        """
        将任务加入队列（异步模式，立即返回）

        Args:
            machine_id: 机器人ID
            command: 命令内容
            human_id: 所有者ID
            job_timeout: 任务超时时间

        Returns:
            str: Job ID
        """
        if self._task_executor is None:
            raise RuntimeError("Task executor not set. Call set_task_executor() first.")

        # 将任务加入队列
        job = self.task_queue.enqueue(
            self._task_executor,
            machine_id,
            command,
            human_id,
            job_timeout=job_timeout
        )

        logger.info(f"📥 Task {job.id} enqueued for machine {machine_id} (owner: {human_id})")
        return job.id

    def enqueue_and_wait(
        self,
        machine_id: str,
        command: str,
        human_id: str = "",
        job_timeout: str = '5m',
        wait_timeout: int = 300
    ) -> Any:
        """
        将任务加入队列并等待完成（同步模式）

        Args:
            machine_id: 机器人ID
            command: 命令内容
            human_id: 所有者ID
            job_timeout: 任务超时时间
            wait_timeout: 等待超时时间（秒）

        Returns:
            Any: 任务执行结果

        Raises:
            TimeoutError: 等待超时
            Exception: 任务执行失败
        """
        if self._task_executor is None:
            raise RuntimeError("Task executor not set. Call set_task_executor() first.")

        # 将任务加入队列
        job = self.task_queue.enqueue(
            self._task_executor,
            machine_id,
            command,
            human_id,
            job_timeout=job_timeout
        )

        logger.info(f"📥 Task {job.id} enqueued for machine {machine_id} (owner: {human_id})")
        logger.info(f"⏳ Waiting for task {job.id} to complete...")

        # 等待任务完成
        start_time = time.time()

        while job.get_status() not in ['finished', 'failed', 'canceled']:
            if time.time() - start_time > wait_timeout:
                logger.error(f"❌ Task {job.id} timed out after {wait_timeout} seconds")
                raise TimeoutError(f"Job {job.id} timed out after {wait_timeout} seconds")
            time.sleep(0.1)  # 每100ms检查一次

        # 检查任务状态
        if job.get_status() == 'failed':
            logger.error(f"❌ Task {job.id} failed: {job.exc_info}")
            raise Exception(f"Job failed: {job.exc_info}")
        elif job.get_status() == 'canceled':
            logger.error(f"❌ Task {job.id} was canceled")
            raise Exception(f"Job was canceled")

        result = job.result
        logger.info(f"✅ Task {job.id} completed")
        return result

    def get_job_status(self, job_id: str) -> Optional[str]:
        """
        获取任务状态

        Args:
            job_id: 任务ID

        Returns:
            Optional[str]: 任务状态 ('queued', 'started', 'finished', 'failed', 'canceled')
        """
        from rq.job import Job
        try:
            job = Job.fetch(job_id, connection=self.redis_conn)
            return job.get_status()
        except Exception as e:
            logger.error(f"Failed to get job status for {job_id}: {e}")
            return None

    def get_job_result(self, job_id: str) -> Optional[Any]:
        """
        获取任务结果

        Args:
            job_id: 任务ID

        Returns:
            Optional[Any]: 任务结果，如果任务未完成或失败则返回 None
        """
        from rq.job import Job
        try:
            job = Job.fetch(job_id, connection=self.redis_conn)
            if job.get_status() == 'finished':
                return job.result
            return None
        except Exception as e:
            logger.error(f"Failed to get job result for {job_id}: {e}")
            return None

    def cleanup(self):
        """清理资源"""
        if self.redis_conn:
            self.redis_conn.close()
            logger.info("TaskQueueService: Redis connection closed")


# 全局任务队列服务实例
task_queue_service = TaskQueueService()
