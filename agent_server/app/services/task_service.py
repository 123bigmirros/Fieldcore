# -*- coding: utf-8 -*-
"""
Task Service - 任务管理服务

负责异步任务的提交、取消和状态查询
使用 Redis 实现多 worker 之间的状态共享
"""

import redis
from threading import Lock
from typing import Optional
from ..config import config
from app.logger import logger


class TaskService:
    """
    任务管理服务 - 单例模式

    管理每个 agent 的任务，确保同一 agent 只有一个任务在执行
    """

    _instance = None
    _lock = Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, '_initialized'):
            return

        # 初始化 Redis 连接
        self.redis_client = redis.Redis(
            host=config.REDIS_HOST,
            port=config.REDIS_PORT,
            db=config.REDIS_DB,
            password=config.REDIS_PASSWORD,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5,
            retry_on_timeout=True
        )
        self.redis_client.ping()
        logger.info(f"✅ Redis 连接成功: {config.REDIS_HOST}:{config.REDIS_PORT}")

        self._key_prefix = config.REDIS_TASK_KEY_PREFIX
        self._task_ttl = config.REDIS_TASK_TTL
        self._initialized = True

    def _key(self, agent_id: str) -> str:
        """生成 Redis 键"""
        return f"{self._key_prefix}{agent_id}"

    def submit_command(self, agent_id: str, command: str) -> str:
        """提交命令任务，自动取消旧任务"""
        from .tasks import execute_command, celery_app

        # 取消旧任务
        old_task_id = self._get_and_clear_task_id(agent_id)
        if old_task_id:
            self._revoke_task(celery_app, old_task_id, agent_id)

        # 提交新任务
        task = execute_command.delay(agent_id, command)
        self._set_task_id(agent_id, task.id)

        logger.info(f"📤 提交任务: agent_id={agent_id}, task_id={task.id}")
        return task.id

    def _revoke_task(self, celery_app, task_id: str, agent_id: str):
        """撤销任务"""
        try:
            state = celery_app.AsyncResult(task_id).state
            terminate = state in ('STARTED', 'PROGRESS')
            celery_app.control.revoke(task_id, terminate=terminate)
            logger.info(f"🛑 {'终止' if terminate else '撤销'}任务: agent_id={agent_id}, task_id={task_id}")
        except Exception as e:
            logger.warning(f"取消任务失败: {e}")

    def get_task_status(self, task_id: str) -> dict:
        """获取任务状态"""
        from .tasks import celery_app

        task = celery_app.AsyncResult(task_id)
        if task.state == 'PENDING':
            return {'success': True, 'status': task.state, 'message': '任务等待执行'}
        elif task.state == 'SUCCESS':
            return {'success': True, 'status': task.state, **task.result}
        else:
            return {'success': False, 'status': task.state, 'error': str(task.info)}

    def get_agent_task_id(self, agent_id: str) -> Optional[str]:
        """获取 agent 的当前任务 ID"""
        return self.redis_client.get(self._key(agent_id))

    def clear_agent_task(self, agent_id: str):
        """清除 agent 的任务记录"""
        self.redis_client.delete(self._key(agent_id))

    def _set_task_id(self, agent_id: str, task_id: str):
        """设置任务 ID（带过期时间）"""
        self.redis_client.setex(self._key(agent_id), self._task_ttl, task_id)

    def _get_and_clear_task_id(self, agent_id: str) -> Optional[str]:
        """获取并清除任务 ID（原子操作）"""
        try:
            return self.redis_client.getdel(self._key(agent_id))
        except AttributeError:
            # Redis < 6.2，使用 GET + DEL
            task_id = self.redis_client.get(self._key(agent_id))
            if task_id:
                self.redis_client.delete(self._key(agent_id))
            return task_id


# 全局实例
task_service = TaskService()

