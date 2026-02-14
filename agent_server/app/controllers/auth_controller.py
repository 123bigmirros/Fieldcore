# -*- coding: utf-8 -*-
"""Auth Controller — user registration and API key verification."""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from flask import Blueprint, request

from shared.response import success_response, error_response
from shared import error_codes as EC
from shared.validation import RegisterRequest
from agent_server.app.services.auth_service import auth_service

auth_bp = Blueprint("auth", __name__, url_prefix="/api/v1/auth")


@auth_bp.route("/register", methods=["POST"])
def register():
    """Register a new user and return an API key."""
    data = request.get_json() or {}

    try:
        req = RegisterRequest(**data)
    except Exception as e:
        return error_response(EC.VALIDATION_ERROR, str(e))

    success, result = auth_service.register(metadata=req.metadata)

    if success:
        return success_response(result, 201)
    return error_response(EC.INTERNAL_ERROR, result.get("error", "Registration failed"))


@auth_bp.route("/verify", methods=["POST"])
def verify():
    """Verify an API key."""
    data = request.get_json() or {}
    api_key = data.get("api_key")

    if not api_key:
        return error_response(EC.VALIDATION_ERROR, "api_key is required")

    is_valid, user_id = auth_service.verify_api_key(api_key)

    if is_valid:
        return success_response({"valid": True, "user_id": user_id})
    return error_response(EC.API_KEY_INVALID, "Invalid API key", 401)
