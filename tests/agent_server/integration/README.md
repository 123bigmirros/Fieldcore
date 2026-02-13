# API 集成测试

这个目录包含对实际运行的 Agent Server API 的集成测试。

## 前置条件

1. **Agent Server 正在运行**
   ```bash
   cd agent_server
   python main.py
   ```
   或者使用启动脚本：
   ```bash
   python start_servers.py
   ```

2. **Redis 正在运行**（用于任务管理）
   ```bash
   redis-server
   ```

3. **可选：Celery Worker 正在运行**（用于异步任务执行）
   ```bash
   cd agent_server
   python main.py worker
   ```

## 运行测试

### 方法 1: 使用 pytest

```bash
# 运行所有集成测试
pytest tests/agent_server/integration/test_api_endpoints.py -v -s

# 运行特定测试
pytest tests/agent_server/integration/test_api_endpoints.py::TestAPIIntegration::test_create_human_agent -v -s
```

### 方法 2: 直接运行 Python 脚本

```bash
python tests/agent_server/integration/test_api_endpoints.py
```

## 配置

### 修改服务器地址

如果 Agent Server 运行在不同的端口，修改 `test_api_endpoints.py` 中的：

```python
BASE_URL = "http://localhost:8004"  # 修改为实际端口
```

### 使用自定义 API Key

可以通过环境变量设置：

```bash
export TEST_API_KEY="your-api-key-here"
pytest tests/agent_server/integration/test_api_endpoints.py -v -s
```

或者测试会自动注册新用户获取 API Key。

## 测试内容

- ✅ 健康检查
- ✅ 用户注册（获取 API Key）
- ✅ 创建 Human Agent
- ✅ 创建 Machine Agent
- ✅ 获取 Agent 信息
- ✅ 获取所有 Agent 列表
- ✅ 更新 Agent 信息
- ✅ 发送命令
- ✅ 查询任务状态
- ✅ 删除 Agent
- ✅ API Key 验证

## 注意事项

- 这些测试会实际调用运行中的服务，可能会创建和删除数据
- 测试会自动清理创建的测试数据
- 如果服务未运行，测试会失败并显示连接错误

