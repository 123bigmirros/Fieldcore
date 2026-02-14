# -*- coding: utf-8 -*-
"""
Proxy Controller — BFF layer so the frontend never hits World Server directly.

Proxies selected World Server endpoints through the Agent Server,
adding authentication.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

import requests
from flask import Blueprint, request as flask_request

from shared.response import success_response, error_response
from shared import error_codes as EC
from agent_server.app.utils.auth_decorator import require_api_key
from agent_server.app.config import config

proxy_bp = Blueprint("proxy", __name__, url_prefix="/api/v1/world")


@proxy_bp.route("/view", methods=["GET"])
@require_api_key
def proxy_view(user_id):
    """Proxy the fog-of-war view endpoint from World Server."""
    human_id = flask_request.args.get("human_id")
    if not human_id:
        return error_response(EC.VALIDATION_ERROR, "human_id query parameter is required")

    try:
        resp = requests.get(
            f"{config.WORLD_SERVER_URL}/api/v1/world/view",
            params={"human_id": human_id},
            timeout=5,
        )
        data = resp.json()
        # Forward the World Server response as-is (already in unified format)
        return data, resp.status_code
    except requests.exceptions.RequestException as e:
        return error_response(EC.INTERNAL_ERROR, f"World Server unreachable: {e}", 502)
