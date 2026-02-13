# Agent Server Package
# 确保 app 子模块可以被导入
import sys
from pathlib import Path

# 添加当前目录到路径，使 app 可以作为子模块导入
_current_dir = Path(__file__).parent
if str(_current_dir) not in sys.path:
    sys.path.insert(0, str(_current_dir))

# 显式导入 app 子模块，确保它可以被识别
try:
    from . import app
except ImportError:
    # 如果相对导入失败，尝试绝对导入
    import importlib
    importlib.import_module('agent_server.app')
