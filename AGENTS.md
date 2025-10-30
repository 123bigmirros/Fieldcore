# Repository Guidelines

## Project Structure & Module Organization
OpenManus pairs a Python MCP backend with a Vue 3 dashboard. Core agent logic lives in `app/` (notably `app/agent`, `app/service`, and reusable utilities in `app/tool` and `app/mcp`). API entrypoints are exposed through `run_mcp.py` and `run_mcp_server.py`. Configuration samples sit in `config/`, while live secrets stay outside version control. Tests reside in `tests/sandbox`, and UI code is under `frontend/src` with components, composables, and constants. Temporary work artifacts go in `workspace/`; keep large assets out of the repo.

## Build, Test, and Development Commands
Install backend dependencies in an isolated env, then run agents with `python run_mcp.py --connection stdio` for local stdio mode or `python run_mcp_server.py` to launch the Flask + Redis stack (ensure Redis is running). Spin up the dashboard with `cd frontend && npm install && npm run dev` (Vite serves on port 5173 by default). Use `npm run build` to generate optimized assets. Execute integration-style backend flows with `python run_mcp.py --interactive` to send prompts against the configured server.

## Coding Style & Naming Conventions
Follow PEP 8 with 4-space indentation, descriptive snake_case function names, and type hints as shown in `run_mcp.py`. Add module-level docstrings for new files and log through `app.logger` instead of print. Vue components reside in PascalCase files under `frontend/src/components`, while composables stay camelCase inside `frontend/src/composables`. Keep configuration constants in `config/*.toml` and avoid duplicating defaults inline.

## Testing Guidelines
Pytest with pytest-asyncio powers the suite; target async-friendly fixtures like `local_client` and leverage temporary directories to avoid host writes. Run `pytest tests/sandbox -vv` before submitting, and narrow scope with `pytest tests/sandbox/test_sandbox.py::test_sandbox_creation`. Add regression tests alongside new modules, keeping names descriptive (e.g., `test_docker_terminal_handles_timeouts`).

## Commit & Pull Request Guidelines
Recent history favors numeric commits (e.g., `0816`); keep that identifier, but append a short summary such as `0816: tighten sandbox cleanup` for clarity. PRs should summarize behavior changes, reference any issue IDs, and list manual or automated test output. Include screenshots or terminal captures when touching the frontend or CLI UX. Tag reviewers for agent, backend, and frontend areas as needed, and confirm configuration updates in `config/` are mirrored in the example files.

## Security & Configuration Tips
Never commit personal API keys; use `.env` files or local overrides referenced by `config/config.toml`. Validate new tools or services against the sandbox before exposing them via the HTTP bridge. If you extend Redis or queue usage, document new environment variables and default values inside `config.example*.toml`.
