# -*- coding: utf-8 -*-
"""Pagination utilities for list endpoints."""

import math

from flask import request


def get_pagination_params(default_limit=50, max_limit=200):
    """Parse page & limit from query string."""
    try:
        page = max(1, int(request.args.get("page", 1)))
    except (TypeError, ValueError):
        page = 1
    try:
        limit = min(max_limit, max(1, int(request.args.get("limit", default_limit))))
    except (TypeError, ValueError):
        limit = default_limit
    return page, limit


def paginated_response(items, total, page, limit):
    """Build a pagination envelope dict (not a Flask response)."""
    return {
        "items": items,
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total,
            "pages": math.ceil(total / limit) if limit else 0,
        },
    }
