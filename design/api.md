# OpenManus API 设计

## agent_controller (端口: 8004)

管理 Human 和 Machine 的创建、查询、更新和命令执行。

| 接口            | 方法   | 路径                    | 描述            |
| --------------- | ------ | ----------------------- | --------------- |
| agentCreate     | POST   | /api/agent              | 创建 Agent      |
| getAgentInfo    | GET    | /api/agent/<id>         | 获取 Agent 信息 |
| updateAgentInfo | PUT    | /api/agent/<id>         | 更新 Agent 信息 |
| sendCmd         | POST   | /api/agent/<id>/command | 发送命令        |
| deleteAgent     | DELETE | /api/agent/<id>         | 删除 Agent      |
| listAgents      | GET    | /api/agent              | 获取所有 Agent  |

### agentCreate 请求

创建 Human:
```json
{
  "agent_type": "human",
  "agent_id": "human_01",
  "machine_count": 3
}
```

创建 Machine (必须指定 owner):
```json
{
  "agent_type": "machine",
  "agent_id": "robot_01",
  "owner_id": "human_01",
  "position": [0, 0, 0]  // 可选，不提供则自动寻找
}
```

### getAgentInfo 响应

Human:
```json
{
  "agent_id": "human_01",
  "agent_type": "human",
  "status": "active",
  "machine_ids": ["robot_01", "robot_02"]
}
```

Machine:
```json
{
  "agent_id": "robot_01",
  "agent_type": "machine",
  "owner_id": "human_01",
  "position": [0, 0, 0],
  "life_value": 10,
  "status": "active"
}
```

### updateAgentInfo 请求

更新 Machine:
```json
{
  "position": [1, 2, 0],
  "life_value": 15
}
```

### sendCmd 请求

```json
{
  "command": "move forward"
}
```

---

## mcp_controller (端口: 8003)

MCP 工具服务，提供工具查询和调用。**工具通过命名约定区分**。

| 接口       | 方法 | 路径                | 描述         |
| ---------- | ---- | ------------------- | ------------ |
| list_tools | GET  | /api/mcp/list_tools | 获取工具列表 |
| call_tool  | POST | /api/mcp/call_tool  | 调用工具     |

### 工具命名约定

- **Human 工具** (以 `human_` 开头): Human Agent 使用
  - `human_send_short_command` - 发送短期命令
  - `human_send_long_command` - 发送长期命令

- **Machine 工具** (以 `machine_` 开头): Machine Agent 使用
  - `machine_check_environment` - 环境检测
  - `machine_step_movement` - 移动
  - `machine_laser_attack` - 攻击
  - `machine_get_self_status` - 获取状态

---

## world_controller (端口: 8005)

世界管理服务，管理机器人和地图状态。

| 接口             | 方法 | 路径                         | 描述       |
| ---------------- | ---- | ---------------------------- | ---------- |
| machine_register | POST | /api/world/machine_register  | 注册机器人 |
| machine_action   | POST | /api/world/machine_action    | 执行动作   |
| save_world       | POST | /api/world/save_world        | 保存世界   |
| machine_view     | GET  | /api/world/machine_view/{id} | 获取视野   |

---

## 启动顺序

```bash
# 1. World Server (必须先启动)
cd world_server && python main.py

# 2. MCP Server
python -m mcp_server.main

# 3. Agent Server
python -m agent_server.main
```

## 目录结构

```
OpenManus/
├── world_server/          # 世界管理微服务
│   ├── app/
│   │   ├── controllers/
│   │   ├── services/
│   │   └── models/
│   └── main.py
├── mcp_server/            # MCP 工具微服务
│   ├── app/
│   │   ├── controllers/
│   │   └── services/
│   └── main.py
├── agent_server/          # Agent 管理微服务
│   ├── app/
│   │   ├── controllers/
│   │   ├── services/
│   │   └── models/
│   └── main.py
└── app/                   # 共享代码
    ├── tool/              # 工具定义
    └── service/           # 客户端
```
