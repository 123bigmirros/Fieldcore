# -*- coding: utf-8 -*-
"""
Command Queue Service

Maintains a command queue per machine, executed by a background thread
"""

import time
import threading
import logging
from typing import Dict, Optional

from ..utils.ring_buffer import RingBuffer

logger = logging.getLogger(__name__)


class CommandQueueService:
    """Command queue service - singleton"""

    _instance: Optional["CommandQueueService"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, '_initialized'):
            return

        # Command queue per machine_id (created/deleted by main thread, read-only by consumer thread)
        self._queues: Dict[str, RingBuffer] = {}

        # Consumer thread control
        self._running = False
        self._consumer_thread: Optional[threading.Thread] = None

        # Command execution callback (provided by world_service)
        self._execute_callback = None

        # Configuration
        self.buffer_capacity = 100
        self.poll_interval = 0.1

        self._initialized = True

    def set_execute_callback(self, callback):
        """Set the command execution callback"""
        self._execute_callback = callback

    def create_queue(self, machine_id: str):
        """Create a command queue for a machine (main thread only)"""
        if machine_id not in self._queues:
            self._queues[machine_id] = RingBuffer(self.buffer_capacity)

    def remove_queue(self, machine_id: str):
        """Remove a machine's command queue (main thread only)"""
        if machine_id in self._queues:
            del self._queues[machine_id]

    def enqueue_command(self, machine_id: str, action: str, params: dict) -> bool:
        """Add a command to the queue (producer interface, main thread only)"""
        if machine_id not in self._queues:
            return False

        queue = self._queues[machine_id]
        command = {'action': action, 'params': params}
        return queue.put(command)

    def start_consumer(self):
        """Start the consumer thread"""
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
        """Stop the consumer thread"""
        if not self._running:
            return

        self._running = False
        if self._consumer_thread:
            self._consumer_thread.join(timeout=2.0)

    def _consumer_loop(self):
        """Consumer loop: continuously dequeue and execute commands"""
        while self._running:
            try:
                # Snapshot queue dict to avoid modification during iteration
                queues_snapshot = dict(self._queues)

                # Iterate all queues and execute commands
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
                                logger.error(f"Command execution failed: machine_id={machine_id}, error={e}")

                time.sleep(self.poll_interval)

            except Exception as e:
                logger.error(f"Consumer loop error: {e}")
                time.sleep(self.poll_interval)


# Global instance
command_queue_service = CommandQueueService()

