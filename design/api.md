# OpenManus API Reference

All endpoints return a unified response envelope:

```json
{
  "success": true,
  "data": { ... },
  "error": null
}
```

Error responses:

```json
{
  "success": false,
  "data": null,
  "error": {
    "code": "MACHINE_NOT_FOUND",
    "message": "Machine robot_99 not found"
  }
}
```

## Error Codes

| Code | Description |
|------|-------------|
| VALIDATION_ERROR | Request body failed validation |
| API_KEY_MISSING | Authorization header not provided |
| API_KEY_INVALID | API key is not valid |
| BEARER_PREFIX_REQUIRED | Authorization header must start with "Bearer " |
| AGENT_NOT_FOUND | Agent does not exist |
| INVALID_AGENT_TYPE | agent_type must be "human" or "machine" |
| OWNER_NOT_FOUND | Owner (human) does not exist |
| MACHINE_NOT_FOUND | Machine does not exist |
| MACHINE_ALREADY_EXISTS | Machine ID already registered |
| POSITION_COLLISION | Position is occupied |
| COMMAND_QUEUE_FULL | Command queue is full |
| TOOL_NOT_FOUND | MCP tool does not exist |
| TOOL_EXECUTION_FAILED | MCP tool execution failed |
| TASK_NOT_FOUND | Async task does not exist |
| INTERNAL_ERROR | Unexpected server error |

---

## Authentication (Agent Server, port 8004)

All agent and proxy endpoints require `Authorization: Bearer <api_key>` header.

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/auth/register` | Register and get API key |
| GET | `/api/v1/auth/verify` | Verify API key |

### POST /api/v1/auth/register

Request:
```json
{
  "agent_id": "human_01"
}
```

Response:
```json
{
  "success": true,
  "data": {
    "api_key": "sk-xxxxxxxx",
    "agent_id": "human_01"
  },
  "error": null
}
```

---

## Agents (Agent Server, port 8004)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/agents` | Create agent |
| GET | `/api/v1/agents` | List agents (paginated) |
| GET | `/api/v1/agents/<id>` | Get agent info |
| PUT | `/api/v1/agents/<id>` | Update agent |
| POST | `/api/v1/agents/<id>/commands` | Send command |
| GET | `/api/v1/agents/tasks/<task_id>` | Get task status |
| DELETE | `/api/v1/agents/<id>` | Delete agent |

### POST /api/v1/agents — Create Human

```json
{
  "agent_type": "human",
  "agent_id": "human_01",
  "machine_count": 3
}
```

### POST /api/v1/agents — Create Machine

```json
{
  "agent_type": "machine",
  "agent_id": "robot_01",
  "owner_id": "human_01",
  "position": [0, 0, 0]
}
```

### POST /api/v1/agents/<id>/commands

```json
{
  "command": "move forward"
}
```

### GET /api/v1/agents?page=1&limit=10

Paginated response:
```json
{
  "success": true,
  "data": {
    "items": [ ... ],
    "pagination": {
      "page": 1,
      "limit": 10,
      "total": 25,
      "pages": 3
    }
  },
  "error": null
}
```

---

## World Proxy (Agent Server, port 8004)

Frontend calls the Agent Server proxy instead of the World Server directly.

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/world/view?human_id=...` | Fog-of-war filtered view (auth required) |

---

## MCP Tools (MCP Server, port 8003)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/mcp/tools` | List available tools |
| POST | `/api/v1/mcp/tools/<tool_name>/invoke` | Invoke a tool |

### POST /api/v1/mcp/tools/<tool_name>/invoke

```json
{
  "parameters": {
    "machine_id": "robot_01",
    "direction": [1, 0, 0]
  }
}
```

### Tool naming convention

- `human_*` — Human Agent tools (e.g. `human_send_short_command`)
- `machine_*` — Machine Agent tools (e.g. `machine_check_environment`, `machine_step_movement`, `machine_laser_attack`, `machine_get_self_status`)

---

## World (World Server, port 8005)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/world/machines` | Register machine |
| GET | `/api/v1/world/machines` | List machines (paginated) |
| POST | `/api/v1/world/machines/<id>/actions` | Execute action |
| GET | `/api/v1/world/machines/<id>/view` | Get machine field-of-view |
| POST | `/api/v1/world/state` | Save world state |
| GET | `/api/v1/world/view` | Fog-of-war view |
| GET | `/api/v1/world/obstacles` | List obstacles |
| GET | `/api/v1/world/carried-resources` | List carried resources |
| GET | `/api/v1/world/debug/machines` | Debug: all machines |
| GET | `/api/v1/world/debug/obstacles` | Debug: all obstacles |
| POST | `/api/v1/world/debug/reset` | Debug: reset world |

### POST /api/v1/world/machines

```json
{
  "machine_id": "robot_01",
  "position": [5, 3, 0],
  "owner": "human_01",
  "life_value": 10,
  "machine_type": "worker",
  "size": 1.0,
  "facing_direction": [1.0, 0.0],
  "view_size": 3
}
```

### POST /api/v1/world/machines/<id>/actions

```json
{
  "action": "move",
  "params": {
    "direction": [1, 0, 0],
    "distance": 1
  }
}
```

---

## Startup Order

```bash
python start_servers.py          # Start all services (ordered)
python start_servers.py --stop   # Stop all services
python start_servers.py --status # Check service status
```

Manual startup (order matters):
1. World Server: `cd world_server && python main.py`
2. MCP Server: `cd mcp_server && python main.py`
3. Agent Server: `cd agent_server && python main.py`
4. Agent Worker: `cd agent_server && python main.py worker`
5. Frontend: `cd frontend && npm run dev`

## Directory Structure

```
OpenManus/
├── shared/                # Shared utilities (response, pagination, validation, error codes)
├── world_server/          # World management microservice
│   ├── app/
│   │   ├── controllers/
│   │   ├── services/
│   │   └── models/
│   └── main.py
├── mcp_server/            # MCP tool microservice
│   ├── app/
│   │   ├── controllers/
│   │   └── services/
│   └── main.py
├── agent_server/          # Agent management microservice
│   ├── app/
│   │   ├── controllers/
│   │   ├── services/
│   │   └── models/
│   └── main.py
├── frontend/              # Vue 3 + Vite frontend
│   └── src/
└── app/                   # Shared core code
    ├── agent/             # Agent implementations
    ├── tool/              # Tool definitions
    └── service/           # HTTP clients
```
