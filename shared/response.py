# -*- coding: utf-8 -*-
"""Unified API response helpers."""

from flask import jsonify


def success_response(data=None, status_code=200):
    """Return a successful JSON response."""
    return jsonify({"success": True, "data": data, "error": None}), status_code


def error_response(code, message, status_code=400):
    """Return an error JSON response."""
    return (
        jsonify(
            {
                "success": False,
                "data": None,
                "error": {"code": code, "message": message},
            }
        ),
        status_code,
    )
