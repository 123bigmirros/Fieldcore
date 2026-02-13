# -*- coding: utf-8 -*-
"""
Command Queue Service - 命令队列服务

为每个 machine 维护命令队列，使用后台线程执行命令
"""

import time
import threading
import logging
from typing import Dict, Optional

from ..utils.ring_buffer import RingBuffer

logger = logging.getLogger(__name__)


class CommandQueueService:
    """命令队列服务 - 单例"""

    _instance: Optional["CommandQueueService"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, '_initialized'):
            return

        # 为每个 machine_id 维护一个命令队列（主线程创建/删除，消费者线程只读）
        self._queues: Dict[str, RingBuffer] = {}

        # 消费者线程控制
        self._running = False
        self._consumer_thread: Optional[threading.Thread] = None

        # 命令执行回调函数（由 world_service 提供）
        self._execute_callback = None

        # 配置
        self.buffer_capacity = 100
        self.poll_interval = 0.1

        self._initialized = True

    def set_execute_callback(self, callback):
        """设置命令执行回调函数"""
        self._execute_callback = callback

    def create_queue(self, machine_id: str):
        """为 machine 创建命令队列（仅主线程调用）"""
        if machine_id not in self._queues:
            self._queues[machine_id] = RingBuffer(self.buffer_capacity)

    def remove_queue(self, machine_id: str):
        """移除 machine 的命令队列（仅主线程调用）"""
        if machine_id in self._queues:
            del self._queues[machine_id]

    def enqueue_command(self, machine_id: str, action: str, params: dict) -> bool:
        """将命令添加到队列（生产者接口，仅主线程调用）"""
        if machine_id not in self._queues:
            return False

        queue = self._queues[machine_id]
        command = {'action': action, 'params': params}
        return queue.put(command)

    def start_consumer(self):
        """启动消费者线程"""
        if self._running:
            return

        self._running = True
        self._consumer_thread = threading.Thread(
            target=self._consumer_loop,
            daemon=True,
            name="CommandQueueConsumer"
        )
        self._consumer_thread.start()

    def stop_consumer(self):
        """停止消费者线程"""
        if not self._running:
            return

        self._running = False
        if self._consumer_thread:
            self._consumer_thread.join(timeout=2.0)

    def _consumer_loop(self):
        """消费者循环：不断从队列中取出命令并执行"""
        while self._running:
            try:
                # 复制队列字典，避免在迭代时字典被修改
                queues_snapshot = dict(self._queues)

                # 遍历所有队列，执行命令
                for machine_id, queue in queues_snapshot.items():
                    if not queue.is_empty():
                        command = queue.get()
                        if command and self._execute_callback:
                            try:
                                self._execute_callback(
                                    machine_id,
                                    command['action'],
                                    command['params']
                                )
                            except Exception as e:
                                logger.error(f"执行命令失败: machine_id={machine_id}, error={e}")

                time.sleep(self.poll_interval)

            except Exception as e:
                logger.error(f"消费者循环异常: {e}")
                time.sleep(self.poll_interval)


# 全局实例
command_queue_service = CommandQueueService()

