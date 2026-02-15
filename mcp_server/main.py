#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MCP Server — tool service via Model Context Protocol.

Provides tool listing and invocation API.
"""

import sys
import os
import logging

# Add paths
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)
sys.path.insert(0, os.path.dirname(current_dir))  # project root

from flask import Flask
from flask_cors import CORS

from mcp_server.app.config import config
from mcp_server.app.controllers.mcp_controller import mcp_bp


def create_app() -> Flask:
    """Create the Flask application."""
    flask_app = Flask(__name__)
    CORS(flask_app)
    flask_app.register_blueprint(mcp_bp)

    @flask_app.route("/health", methods=["GET"])
    def health_check():
        return {"status": "ok", "service": "mcp_server"}

    return flask_app


def main():
    """Entry point."""
    log = logging.getLogger("werkzeug")
    log.setLevel(logging.ERROR)

    flask_app = create_app()

    print("=" * 50)
    print("MCP Server")
    print("=" * 50)
    print(f"Address: http://{config.HOST}:{config.PORT}")
    print(f"World Server: {config.WORLD_SERVER_URL}")
    print("\nAPI:")
    print("  GET  /api/v1/mcp/tools                    - List tools")
    print("  POST /api/v1/mcp/tools/<name>/invoke       - Invoke tool")
    print("  GET  /health                               - Health check")
    print("=" * 50)
    print("\nNote: Start World Server first.")
    print("Service started\n")

    flask_app.run(host=config.HOST, port=config.PORT, debug=False, threaded=True)


if __name__ == "__main__":
    main()
