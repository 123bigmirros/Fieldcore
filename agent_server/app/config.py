# -*- coding: utf-8 -*-
"""Agent Server Configuration"""

import os


class Config:
    HOST = os.getenv('AGENT_SERVER_HOST', '0.0.0.0')
    PORT = int(os.getenv('AGENT_SERVER_PORT', 8004))
    MCP_SERVER_URL = os.getenv('MCP_SERVER_URL', 'http://localhost:8003')
    WORLD_SERVER_URL = os.getenv('WORLD_SERVER_URL', 'http://localhost:8005')

    # Celery configuration
    CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', 'amqp://guest:guest@localhost:5672/')
    CELERY_RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND', 'rpc://')

    # Redis configuration (for task state sharing)
    REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
    REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
    REDIS_DB = int(os.getenv('REDIS_DB', 0))
    REDIS_PASSWORD = os.getenv('REDIS_PASSWORD', None)
    REDIS_TASK_KEY_PREFIX = 'agent_task:'  # Task key prefix
    REDIS_TASK_TTL = 3600  # Task record TTL in seconds


config = Config()

