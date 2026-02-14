# -*- coding: utf-8 -*-
"""Authentication decorator — protects endpoints requiring a valid API key."""

import sys
import os
from functools import wraps

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from flask import request

from shared.response import error_response
from shared import error_codes as EC
from agent_server.app.services.auth_service import auth_service


def require_api_key(f):
    """Decorator: require a valid Bearer API key in the Authorization header."""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        from app.logger import logger

        logger.info(f"API key auth: {request.method} {request.path}")

        auth_header = request.headers.get("Authorization")

        if not auth_header:
            logger.warning("API key missing")
            return error_response(EC.API_KEY_MISSING, "Authorization header is required", 401)

        if not auth_header.startswith("Bearer "):
            logger.warning("Bearer prefix missing")
            return error_response(
                EC.BEARER_PREFIX_REQUIRED,
                "Authorization header must use 'Bearer <key>' format",
                401,
            )

        api_key = auth_header[7:]

        is_valid, user_id = auth_service.verify_api_key(api_key)
        if not is_valid:
            logger.warning("API key invalid")
            return error_response(EC.API_KEY_INVALID, "Invalid API key", 401)

        logger.info(f"API key verified: user_id={user_id}")
        kwargs["user_id"] = user_id
        return f(*args, **kwargs)

    return decorated_function
