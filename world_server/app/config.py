# -*- coding: utf-8 -*-
"""World service configuration"""

import os
from typing import Tuple


class Config:
    """Base configuration"""
    HOST = os.getenv('WORLD_SERVER_HOST', '0.0.0.0')
    PORT = int(os.getenv('WORLD_SERVER_PORT', 8005))
    DEBUG = os.getenv('WORLD_SERVER_DEBUG', 'false').lower() == 'true'

    # World configuration
    WORLD_BOUNDS: Tuple[float, float] = (
        float(os.getenv('WORLD_BOUNDS_MIN', '-100.0')),
        float(os.getenv('WORLD_BOUNDS_MAX', '100.0'))
    )

    # Machine default configuration
    DEFAULT_LIFE_VALUE = int(os.getenv('DEFAULT_LIFE_VALUE', '10'))
    DEFAULT_MACHINE_TYPE = os.getenv('DEFAULT_MACHINE_TYPE', 'worker')
    DEFAULT_SIZE = float(os.getenv('DEFAULT_SIZE', '1.0'))
    DEFAULT_VIEW_SIZE = int(os.getenv('DEFAULT_VIEW_SIZE', '3'))


config = Config()

