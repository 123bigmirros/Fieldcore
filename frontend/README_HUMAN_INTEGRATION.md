# OpenManus Human 集成前端

这是一个集成了 Human 管理功能的前端界面，在保留原始地图可视化功能的基础上，增加了 Human 管理和指令控制功能。

## 🚀 新增功能

### 1. 登录界面
- 进入系统时需要输入 Human ID
- 可选择创建的机器人数量（默认3个）
- 自动调用 `human_manager_server.py` 的 API 创建 Human 和对应的机器人

### 2. 指令控制
- **双击空格键**：在地图界面快速打开指令输入框
- 支持多行文本指令输入
- 异步发送指令，无需等待返回结果
- Ctrl+Enter 快捷发送

### 3. 退出功能
- 状态面板中的"退出系统"按钮
- 自动删除当前 Human 及其所有机器人
- 返回登录界面

## 🎮 使用方法

### 启动步骤
1. 启动 MCP 服务器：`python run_mcp_server.py`
2. 启动 Human 管理服务器：`python human_manager_server.py`
3. 启动前端：`cd frontend && npm run dev`

### 操作流程
1. **登录**：输入 Human ID 和机器人数量，点击"创建Human"
2. **查看地图**：观察机器人和障碍物的实时状态
3. **发送指令**：双击空格键，输入指令，发送
4. **退出**：点击"退出系统"按钮

## 🔧 技术特点

- **完全兼容**：保留了所有原始的地图可视化功能
- **最小修改**：复用了99%的原有代码
- **用户友好**：简洁的界面和直观的操作方式
- **异步处理**：指令发送不阻塞界面操作

## 📡 API 集成

自动调用以下 Human Manager API：
- `POST /api/humans` - 创建 Human
- `POST /api/humans/{human_id}/command` - 发送指令
- `DELETE /api/humans/{human_id}` - 删除 Human

## 🎯 快捷键

- `双击空格`：打开指令输入框
- `Ctrl+Enter`：发送指令
- `Ctrl+D`：显示调试信息
- `Ctrl+G`：切换网格显示
