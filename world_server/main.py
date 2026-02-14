#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
World Server — world state management microservice.

Core API:
- POST /api/v1/world/machines                     — register machine
- POST /api/v1/world/machines/<id>/actions         — execute action
- POST /api/v1/world/state                         — persist world
- GET  /api/v1/world/machines/<id>/view            — machine field-of-view
- GET  /api/v1/world/view                          — fog-of-war view
"""

import logging
from flask import Flask
from flask_cors import CORS

from app.config import config
from app.controllers.world_controller import world_bp


def create_app() -> Flask:
    """Create the Flask application."""
    app = Flask(__name__)
    CORS(app)

    # Register world controller
    app.register_blueprint(world_bp)

    @app.route("/health", methods=["GET"])
    def health_check():
        return {"status": "ok", "service": "world_server"}

    return app


def main():
    """Entry point."""
    log = logging.getLogger("werkzeug")
    log.setLevel(logging.ERROR)

    app = create_app()

    print("=" * 50)
    print("World Server")
    print("=" * 50)
    print(f"Address: http://{config.HOST}:{config.PORT}")
    print("\nCore API:")
    print("  POST /api/v1/world/machines                  - Register machine")
    print("  POST /api/v1/world/machines/<id>/actions      - Execute action")
    print("  POST /api/v1/world/state                      - Save world")
    print("  GET  /api/v1/world/machines/<id>/view         - Machine view")
    print("\nFrontend API:")
    print("  GET  /api/v1/world/view                       - Fog-of-war view")
    print("  GET  /api/v1/world/machines                   - List machines")
    print("  GET  /api/v1/world/obstacles                  - List obstacles")
    print("  GET  /api/v1/world/carried-resources          - Carried resources")
    print("\nDebug API:")
    print("  GET  /api/v1/world/debug/machines             - Raw machines")
    print("  GET  /api/v1/world/debug/obstacles            - Raw obstacles")
    print("  POST /api/v1/world/debug/reset                - Reset world")
    print("=" * 50)
    print("Service started\n")

    app.run(host=config.HOST, port=config.PORT, debug=config.DEBUG)


if __name__ == "__main__":
    main()
