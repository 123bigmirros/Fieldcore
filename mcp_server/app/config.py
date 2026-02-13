# -*- coding: utf-8 -*-
"""MCP Server 配置"""

import os


class Config:
    HOST = os.getenv('MCP_SERVER_HOST', '0.0.0.0')
    PORT = int(os.getenv('MCP_SERVER_PORT', 8003))
    WORLD_SERVER_URL = os.getenv('WORLD_SERVER_URL', 'http://localhost:8005')


config = Config()

