# -*- coding: utf-8 -*-
"""
Agent Controller — CRUD and command execution for agents.

Endpoints:
  POST   /                     — create agent
  GET    /                     — list agents (paginated)
  GET    /<agent_id>           — get agent info
  PUT    /<agent_id>           — update agent info
  POST   /<agent_id>/commands  — send command
  GET    /tasks/<task_id>      — get task status
  DELETE /<agent_id>           — delete agent
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from flask import Blueprint, request

from shared.response import success_response, error_response
from shared.pagination import get_pagination_params, paginated_response
from shared import error_codes as EC
from shared.validation import AgentCreateRequest, CommandRequest, AgentUpdateRequest

from agent_server.app.services.agent_service import agent_service
from agent_server.app.services.task_service import task_service
from agent_server.app.utils.auth_decorator import require_api_key

agent_bp = Blueprint("agent", __name__, url_prefix="/api/v1/agents")


@agent_bp.route("", methods=["POST"])
@require_api_key
def agent_create(user_id):
    """Create an agent (human or machine)."""
    data = request.get_json() or {}

    try:
        req = AgentCreateRequest(**data)
    except Exception as e:
        return error_response(EC.VALIDATION_ERROR, str(e))

    success, result = agent_service.create_agent(
        agent_type=req.agent_type,
        agent_id=req.agent_id,
        owner_id=req.owner_id,
        machine_count=req.machine_count,
        position=req.position,
        user_id=user_id,
    )

    if success:
        return success_response(result, 201)
    # Map error strings to codes
    err = result.get("error", "Unknown error")
    code = EC.INVALID_AGENT_TYPE if "Invalid agent_type" in err else EC.VALIDATION_ERROR
    if "not found" in err.lower():
        code = EC.OWNER_NOT_FOUND
    return error_response(code, err)


@agent_bp.route("/<agent_id>", methods=["GET"])
@require_api_key
def get_agent_info(agent_id, user_id):
    """Get agent information."""
    info = agent_service.get_agent_info(agent_id)
    if info:
        return success_response({"agent": info})
    return error_response(EC.AGENT_NOT_FOUND, f"Agent {agent_id} not found", 404)


@agent_bp.route("/<agent_id>", methods=["PUT"])
@require_api_key
def update_agent_info(agent_id, user_id):
    """Update agent information."""
    data = request.get_json() or {}

    try:
        req = AgentUpdateRequest(**data)
    except Exception as e:
        return error_response(EC.VALIDATION_ERROR, str(e))

    success, error = agent_service.update_agent_info(agent_id, req.model_dump(exclude_none=True))
    if success:
        return success_response(None)
    return error_response(EC.AGENT_NOT_FOUND, error, 400)


@agent_bp.route("/<agent_id>/commands", methods=["POST"])
@require_api_key
def send_cmd(agent_id, user_id):
    """Send a command to an agent (async execution)."""
    data = request.get_json() or {}

    try:
        req = CommandRequest(**data)
    except Exception as e:
        return error_response(EC.VALIDATION_ERROR, str(e))

    if not agent_service.get_agent_info(agent_id):
        return error_response(EC.AGENT_NOT_FOUND, f"Agent {agent_id} not found", 404)

    task_id = task_service.submit_command(agent_id, req.command)
    return success_response({"task_id": task_id})


@agent_bp.route("/tasks/<task_id>", methods=["GET"])
@require_api_key
def get_task_status(task_id, user_id):
    """Get async task status."""
    response = task_service.get_task_status(task_id)
    if response.get("status") == "UNKNOWN":
        return error_response(EC.TASK_NOT_FOUND, "Task not found", 404)
    return success_response(response)


@agent_bp.route("/<agent_id>", methods=["DELETE"])
@require_api_key
def delete_agent(agent_id, user_id):
    """Delete an agent."""
    success, error = agent_service.delete_agent(agent_id)
    if success:
        return success_response(None)
    return error_response(EC.AGENT_NOT_FOUND, error, 404)


@agent_bp.route("", methods=["GET"])
@require_api_key
def list_agents(user_id):
    """List all agents (paginated)."""
    from app.logger import logger

    logger.info(f"List agents request, user_id={user_id}")
    try:
        agents = agent_service.get_all_agents()
        all_agents = list(agents.values()) if isinstance(agents, dict) else agents
        total = len(all_agents)

        page, limit = get_pagination_params()
        start = (page - 1) * limit
        items = all_agents[start : start + limit]

        return success_response(paginated_response(items, total, page, limit))
    except Exception as e:
        logger.error(f"Failed to list agents: {e}", exc_info=True)
        return error_response(EC.INTERNAL_ERROR, str(e), 500)
