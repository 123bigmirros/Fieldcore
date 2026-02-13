# 测试说明

## 目录结构

```
tests/
├── agent_server/              # Agent Server 测试
│   ├── controllers/          # Controller 测试
│   │   └── test_agent_controller.py
│   └── conftest.py           # Pytest 配置
└── sandbox/                  # 沙箱测试（已存在）
```

## 运行测试

### 安装依赖

```bash
pip install pytest pytest-mock
```

### 运行所有测试

```bash
# 从项目根目录运行
pytest tests/

# 运行特定模块
pytest tests/agent_server/

# 运行特定测试文件
pytest tests/agent_server/controllers/test_agent_controller.py

# 运行特定测试类
pytest tests/agent_server/controllers/test_agent_controller.py::TestAgentCreate

# 运行特定测试方法
pytest tests/agent_server/controllers/test_agent_controller.py::TestAgentCreate::test_create_human_success
```

### 查看测试覆盖率

```bash
pip install pytest-cov
pytest --cov=agent_server tests/agent_server/
```

## 测试规范

1. **测试文件命名**：`test_*.py`
2. **测试类命名**：`Test*`
3. **测试方法命名**：`test_*`
4. **使用 Mock**：所有外部依赖都应该被 Mock
5. **独立性**：每个测试应该独立，不依赖其他测试的执行顺序

