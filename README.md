# Fieldcore

A multi-agent command system for coordinating intelligent robots through LLM-powered human commanders. Currently a real-time strategy game — designed to evolve into a real-world multi-robot control platform.

![Fieldcore](image.png)

## What is Fieldcore?

Fieldcore lets a human commander issue high-level orders (e.g., "scout the north area" or "attack enemy base") that an LLM decomposes into concrete actions for multiple robots. Each robot perceives its local environment, executes movement and combat commands, and reports back — all visualized in a real-time web interface.

### Key Features

- **LLM-Powered Command** — Natural language orders are decomposed into multi-step robot tasks
- **Multi-Robot Coordination** — Register and control multiple machines simultaneously
- **Real-Time Visualization** — Vue 3 frontend with grid world, fog of war, laser effects, and live position tracking
- **Fog of War** — Robots only see within their vision radius; strategic information is limited
- **Microservice Architecture** — Clean separation of world state, agent logic, tool protocol, and UI
- **Extensible Tool System** — MCP (Model Context Protocol) for adding custom robot capabilities

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌──────────────┐
│   Frontend   │────▶│ Agent Server │────▶│ World Server │
│  (Vue 3)     │     │  (Flask)     │     │  (Flask)     │
│  port 3000   │     │  port 8004   │     │  port 8005   │
└─────────────┘     └──────┬───────┘     └──────────────┘
                           │
                    ┌──────▼───────┐
                    │  MCP Server  │
                    │  (Flask)     │
                    │  port 8003   │
                    └──────────────┘
```

| Service | Role |
|---------|------|
| **World Server** | Core world state — positions, obstacles, collisions, persistence |
| **Agent Server** | Agent lifecycle, authentication, async task execution (Celery) |
| **MCP Server** | Tool registry and invocation via Model Context Protocol |
| **Frontend** | Real-time grid visualization with interactive command panel |

### Agent Types

- **Human Agent** — LLM-powered commander that interprets orders and coordinates machines
- **Machine Agent** — Executes movement, attack, and observation commands on the grid
- **MCP Agent** — Base class for agents using Model Context Protocol tools

## Quick Start

### Prerequisites

- Python 3.10+
- Node.js 18+
- RabbitMQ (for Celery async tasks)
- Redis

### 1. Install Dependencies

```bash
pip install -r requirements.txt
cd frontend && npm install
```

### 2. Configure LLM

Copy and edit the config file:

```bash
cp config/config.example-model-ollama.toml config/config.toml
```

Edit `config/config.toml` with your LLM provider settings (OpenAI, Anthropic, Azure, Ollama, etc.).

### 3. Start All Services

```bash
python start_servers.py
```

This starts World Server → MCP Server → Agent Server → Agent Worker → Frontend in the correct order.

### 4. Open the UI

Visit `http://localhost:3000`, register a human agent, and start issuing commands.

### Managing Services

```bash
python start_servers.py --status  # Check service status
python start_servers.py --stop    # Stop all services
```

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `WORLD_SERVER_HOST/PORT` | `0.0.0.0:8005` | World server binding |
| `AGENT_SERVER_HOST/PORT` | `0.0.0.0:8004` | Agent server binding |
| `MCP_SERVER_HOST/PORT` | `0.0.0.0:8003` | MCP server binding |
| `CELERY_BROKER_URL` | `amqp://guest:guest@localhost:5672/` | RabbitMQ broker |
| `REDIS_HOST/PORT/DB` | `localhost:6379/0` | Redis connection |

LLM configuration lives in `config/config.toml`. See `config/config.example-*.toml` for provider-specific examples (OpenAI, Anthropic, Azure, Google, Ollama).

## Project Structure

```
fieldcore/
├── app/                  # Shared core — agents, tools, LLM, prompts
├── world_server/         # World state microservice
├── agent_server/         # Agent management microservice
├── mcp_server/           # MCP tool microservice
├── frontend/             # Vue 3 + Vite frontend
├── shared/               # Shared utilities (response envelope, validation)
├── config/               # Configuration files
├── design/               # API documentation
├── tests/                # Test suite
└── start_servers.py      # Service orchestrator
```

## Development

```bash
# Run tests
pytest tests/

# Code formatting (pre-commit hooks: black, isort, autoflake)
pre-commit run --all-files
```

## Roadmap

- [ ] Real robot integration (ROS 2 bridge)
- [ ] Multi-human collaborative command
- [ ] Persistent world with save/load
- [ ] Plugin system for custom tools and behaviors
- [ ] Mobile command interface

## License

MIT
