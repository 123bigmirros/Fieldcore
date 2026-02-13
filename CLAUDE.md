# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

OpenManus is a multi-agent system for managing intelligent robots (machines) coordinated by human agents. It uses a microservices architecture with a Vue.js frontend for real-time visualization.

## Architecture

Four microservices communicate via REST APIs:

- **World Server** (port 8005, `world_server/`) — Core world state: robot positions, obstacles, registration, actions, persistence
- **MCP Server** (port 8006, `mcp_server/`) — Tool listing and invocation via Model Context Protocol
- **Agent Server** (port 8007, `agent_server/`) — Agent lifecycle, command execution, auth. Includes a Celery worker for async tasks
- **Frontend** (port 3000, `frontend/`) — Vue 3 + Vite visualization with real-time coordinate rendering

Shared core code lives in `app/` — agent implementations, service layer, tools, prompts, LLM integration, and config.

Startup order matters: World Server → MCP Server → Agent Server → Agent Worker → Frontend.

### Agent Types

- **Human Agent** — LLM-powered commander that decomposes tasks and coordinates machines
- **Machine Agent** — Executes movement/attack commands, reports status and environment
- **MCP Agent** — Base class for agents using Model Context Protocol tools

## Commands

### Start/Stop All Services
```bash
python start_servers.py          # Start all services (ordered)
python start_servers.py --stop   # Stop all services
python start_servers.py --status # Check service status
```

### Individual Services
```bash
cd world_server && python main.py        # World Server
cd mcp_server && python main.py          # MCP Server
cd agent_server && python main.py        # Agent Server API
cd agent_server && python main.py worker # Agent Worker (Celery)
```

### Frontend
```bash
cd frontend && npm install && npm run dev   # Dev server
cd frontend && npm run build                # Production build
```

### Tests
```bash
pytest tests/                        # All tests
pytest tests/agent_server/           # Agent server tests only
pytest tests/agent_server/test_foo.py::TestClass::test_method  # Single test
```

### Code Formatting (pre-commit)
```bash
pre-commit run --all-files
```

## Configuration

- LLM and system config: `config/config.toml`
- Environment variables for service binding: `WORLD_SERVER_HOST/PORT`, `AGENT_SERVER_HOST/PORT`, `MCP_SERVER_HOST/PORT`
- Celery broker: `CELERY_BROKER_URL` (default: `amqp://guest:guest@localhost:5672/`)
- Redis: `REDIS_HOST`, `REDIS_PORT`, `REDIS_DB`

## Code Style

Pre-commit hooks enforce: black (formatting), isort (imports, profile=black, 2 blank lines after imports), autoflake (unused imports/variables), trailing whitespace cleanup. Each microservice follows a controllers/services/models structure (Flask + Pydantic).

## Logs

Service logs go to `logs/servers/<service_name>.log`.
