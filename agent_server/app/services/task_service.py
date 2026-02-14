# -*- coding: utf-8 -*-
"""
Task Service - Task Management Service

Uses a thread pool to execute commands asynchronously within the main process,
with results stored in Redis. This way worker threads share agent_service
in-memory data with the Flask main process.
"""

import json
import uuid
import redis
from concurrent.futures import ThreadPoolExecutor
from threading import Lock
from typing import Optional

from ..config import config
from app.logger import logger


class TaskService:
    """
    Task Management Service - Singleton

    Uses a thread pool instead of Celery to solve the problem of forked
    processes being unable to share memory.
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
        logger.info(f"Redis connected successfully: {config.REDIS_HOST}:{config.REDIS_PORT}")

        self._key_prefix = config.REDIS_TASK_KEY_PREFIX
        self._task_ttl = config.REDIS_TASK_TTL
        self._executor = ThreadPoolExecutor(max_workers=4)
        self._initialized = True

    def _task_key(self, agent_id: str) -> str:
        return f"{self._key_prefix}{agent_id}"

    def _result_key(self, task_id: str) -> str:
        return f"task_result:{task_id}"

    def submit_command(self, agent_id: str, command: str) -> str:
        """Submit a command task to the thread pool (in-process, shared memory)"""
        task_id = str(uuid.uuid4())

        # Record the current agent's task_id
        self.redis_client.setex(
            self._task_key(agent_id), self._task_ttl, task_id
        )

        # Store initial status
        self.redis_client.setex(
            self._result_key(task_id),
            self._task_ttl,
            json.dumps({
                'status': 'PENDING',
                'success': True,
                'message': 'Task pending execution'
            }),
        )

        # Execute in thread pool
        self._executor.submit(self._run_command, agent_id, command, task_id)

        logger.info(f"Task submitted: agent_id={agent_id}, task_id={task_id}")
        return task_id

    def _run_command(self, agent_id: str, command: str, task_id: str):
        """Execute command in a thread"""
        from .agent_service import agent_service

        current = self.redis_client.get(self._task_key(agent_id))
        if current != task_id:
            logger.warning(f"Task {task_id} has been superseded")
            return

        try:
            logger.info(f"Executing command: agent_id={agent_id}, task_id={task_id}")
            success, result = agent_service.send_command(agent_id, command)

            if success:
                logger.info(f"Command executed successfully: agent_id={agent_id}")
                data = {
                    'status': 'SUCCESS',
                    'success': True,
                    'result': result,
                    'error': None,
                }
            else:
                logger.warning(f"Command execution failed: agent_id={agent_id}, error={result}")
                data = {
                    'status': 'SUCCESS',
                    'success': False,
                    'result': None,
                    'error': result,
                }

        except Exception as e:
            logger.error(f"Task execution exception: agent_id={agent_id}, error={e}")
            data = {'status': 'FAILURE', 'success': False, 'error': str(e)}

        self.redis_client.setex(
            self._result_key(task_id), self._task_ttl, json.dumps(data)
        )
        self.redis_client.delete(self._task_key(agent_id))

    def get_task_status(self, task_id: str) -> dict:
        """Get task status"""
        raw = self.redis_client.get(self._result_key(task_id))
        if not raw:
            return {'success': False, 'status': 'UNKNOWN', 'error': 'Task does not exist'}
        return json.loads(raw)

    def get_agent_task_id(self, agent_id: str) -> Optional[str]:
        return self.redis_client.get(self._task_key(agent_id))

    def clear_agent_task(self, agent_id: str):
        self.redis_client.delete(self._task_key(agent_id))


# Global instance
task_service = TaskService()
