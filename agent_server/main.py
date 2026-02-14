#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Agent Server — agent lifecycle, command execution, and auth.

Usage:
    python main.py          # Start Flask API server
    python main.py worker   # Start Celery Worker
"""

import sys
import os
import logging
import argparse

# Add paths
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)
sys.path.insert(0, os.path.dirname(current_dir))

from flask import Flask
from flask_cors import CORS

from agent_server.app.config import config
from agent_server.app.controllers.agent_controller import agent_bp
from agent_server.app.controllers.auth_controller import auth_bp
from agent_server.app.controllers.proxy_controller import proxy_bp


def create_app() -> Flask:
    """Create the Flask application."""
    flask_app = Flask(__name__)
    CORS(flask_app)
    flask_app.register_blueprint(auth_bp)
    flask_app.register_blueprint(agent_bp)
    flask_app.register_blueprint(proxy_bp)

    @flask_app.route("/health", methods=["GET"])
    def health_check():
        return {"status": "ok", "service": "agent_server"}

    return flask_app


def run_server():
    """Start the Flask API server."""
    log = logging.getLogger("werkzeug")
    log.setLevel(logging.ERROR)

    flask_app = create_app()

    print("=" * 50)
    print("Agent Server")
    print("=" * 50)
    print(f"Address: http://{config.HOST}:{config.PORT}")
    print(f"MCP Server: {config.MCP_SERVER_URL}")
    print(f"World Server: {config.WORLD_SERVER_URL}")
    print("\nAPI:")
    print("  Auth:")
    print("    POST   /api/v1/auth/register         - Register, get API key")
    print("    POST   /api/v1/auth/verify            - Verify API key")
    print("  Agents:")
    print("    POST   /api/v1/agents                 - Create agent (auth)")
    print("    GET    /api/v1/agents                 - List agents (auth)")
    print("    GET    /api/v1/agents/<id>            - Get agent info (auth)")
    print("    PUT    /api/v1/agents/<id>            - Update agent (auth)")
    print("    POST   /api/v1/agents/<id>/commands   - Send command (auth)")
    print("    GET    /api/v1/agents/tasks/<id>      - Task status (auth)")
    print("    DELETE /api/v1/agents/<id>            - Delete agent (auth)")
    print("  World Proxy:")
    print("    GET    /api/v1/world/view             - Fog-of-war view (auth)")
    print("=" * 50)
    print("\nNote: Start World Server and MCP Server first.")
    print("Service started\n")

    flask_app.run(host=config.HOST, port=config.PORT, debug=False)


def run_worker():
    """Start the Celery Worker."""
    from agent_server.app.services.tasks import celery_app

    print("=" * 50)
    print("Celery Worker — async task processing")
    print("=" * 50)
    print(f"Broker: {config.CELERY_BROKER_URL}")
    print(f"Backend: {config.CELERY_RESULT_BACKEND}")
    print("Worker started\n")

    celery_app.worker_main(["worker", "--loglevel=info"])


def main():
    """Entry point."""
    parser = argparse.ArgumentParser(description="Agent Server")
    parser.add_argument(
        "mode",
        nargs="?",
        default="server",
        choices=["server", "worker"],
        help="Run mode: server (default) or worker",
    )

    args = parser.parse_args()

    if args.mode == "worker":
        run_worker()
    else:
        run_server()


if __name__ == "__main__":
    main()
