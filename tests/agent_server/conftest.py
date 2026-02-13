# -*- coding: utf-8 -*-
"""
Pytest 配置文件

提供共享的 fixtures 和测试配置
"""

import pytest
import sys
import os
from pathlib import Path
from unittest.mock import patch

# 添加项目根目录到路径（和 agent_server/main.py 一样的方式）
project_root = Path(__file__).parent.parent.parent
agent_server_dir = project_root / 'agent_server'

# 确保 agent_server 可以作为包导入（用于 agent_server.app 路径）
# 注意：项目根目录必须在最前面，这样 agent_server 才能作为包被导入
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
# agent_server 目录也需要在路径中，用于 app 的直接导入
if str(agent_server_dir) not in sys.path:
    sys.path.insert(1, str(agent_server_dir))


# Mock require_api_key 装饰器
def mock_require_api_key(f):
    """Mock 版本的 require_api_key 装饰器"""
    def wrapper(*args, **kwargs):
        # 自动添加 user_id
        if 'user_id' not in kwargs:
            kwargs['user_id'] = 'test_user_01'
        return f(*args, **kwargs)
    wrapper.__name__ = f.__name__
    wrapper.__wrapped__ = f
    return wrapper


# 在 conftest 中全局 mock 装饰器
# 使用延迟导入，避免在导入时出错
@pytest.fixture(scope='session', autouse=True)
def mock_auth_decorator():
    """自动 mock require_api_key 装饰器"""
    # 确保路径已设置
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    if str(agent_server_dir) not in sys.path:
        sys.path.insert(1, str(agent_server_dir))

    # 确保 agent_server 包可以被正确导入
    import agent_server
    # 直接导入 app 子模块（使用相对导入）
    from agent_server import app

    # 使用 agent_server.app 路径导入（因为 auth_decorator.py 内部使用这个路径）
    from agent_server.app.utils.auth_decorator import require_api_key as original_decorator
    import agent_server.app.utils.auth_decorator as auth_decorator_module
    auth_decorator_module.require_api_key = mock_require_api_key
    yield
    # 恢复原始装饰器
    auth_decorator_module.require_api_key = original_decorator


@pytest.fixture(scope='session')
def project_path():
    """返回项目根目录路径"""
    return project_root

