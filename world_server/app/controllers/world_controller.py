# -*- coding: utf-8 -*-
"""
World Controller — core API for world state management.

Endpoints:
  POST /machines                     — register a machine
  POST /machines/<machine_id>/actions — execute an action
  POST /state                        — persist world state
  GET  /machines/<machine_id>/view   — get machine field-of-view
  GET  /view                         — get fog-of-war filtered view for a player
  GET  /machines                     — list machines (paginated)
  GET  /obstacles                    — list obstacles
  GET  /carried-resources            — list carried resources
  GET  /debug/*                      — debug helpers
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from flask import Blueprint, request

from shared.response import success_response, error_response
from shared.pagination import get_pagination_params, paginated_response
from shared import error_codes as EC
from shared.validation import MachineRegisterRequest, MachineActionRequest

from ..services.world_service import world_service

world_bp = Blueprint("world", __name__, url_prefix="/api/v1/world")


# --------------- core endpoints ---------------

@world_bp.route("/machines", methods=["POST"])
def machine_register():
    """Register a machine in the world."""
    data = request.get_json()
    if not data:
        return error_response(EC.VALIDATION_ERROR, "Request body is required")

    try:
        req = MachineRegisterRequest(**data)
    except Exception as e:
        return error_response(EC.VALIDATION_ERROR, str(e))

    success, error = world_service.register_machine(
        machine_id=req.machine_id,
        position=req.position,
        owner=req.owner,
        life_value=req.life_value,
        machine_type=req.machine_type,
        size=req.size,
        facing_direction=tuple(req.facing_direction),
        view_size=req.view_size,
    )
    if success:
        return success_response(
            {"machine_id": req.machine_id, "position": req.position}, 201
        )

    # Map service-level error strings to error codes
    code = EC.VALIDATION_ERROR
    if "already exists" in error:
        code = EC.MACHINE_ALREADY_EXISTS
    elif "collision" in error.lower():
        code = EC.POSITION_COLLISION
    return error_response(code, error)


@world_bp.route("/machines/<machine_id>/actions", methods=["POST"])
def machine_action(machine_id):
    """Enqueue an action for a machine."""
    data = request.get_json()
    if not data:
        return error_response(EC.VALIDATION_ERROR, "Request body is required")

    try:
        req = MachineActionRequest(**data)
    except Exception as e:
        return error_response(EC.VALIDATION_ERROR, str(e))

    result = world_service.enqueue_command(machine_id, req.action, req.params)

    if result.get("success"):
        return success_response({"message": "Command enqueued"})

    err = result.get("error", "Unknown error")
    code = EC.MACHINE_NOT_FOUND if "not found" in err.lower() else EC.COMMAND_QUEUE_FULL
    return error_response(code, err)


@world_bp.route("/state", methods=["POST"])
def save_world():
    """Persist world state to disk."""
    if world_service.save_world():
        return success_response({"message": "World saved"})
    return error_response(EC.INTERNAL_ERROR, "Failed to save world", 500)


@world_bp.route("/machines/<machine_id>/view", methods=["GET"])
def machine_view(machine_id):
    """Get a machine's field-of-view grid."""
    result = world_service.get_machine_view(machine_id)
    if result:
        return success_response(result)
    return error_response(EC.MACHINE_NOT_FOUND, f"Machine {machine_id} not found", 404)


@world_bp.route("/view", methods=["GET"])
def get_view():
    """Get fog-of-war filtered world data for a player."""
    human_id = request.args.get("human_id")
    if not human_id:
        return error_response(EC.VALIDATION_ERROR, "human_id query parameter is required")
    result = world_service.get_view_for_human(human_id)
    return success_response(result)


# --------------- frontend data endpoints ---------------
@world_bp.route("/machines", methods=["GET"])
def get_machines():
    """List all machines (paginated, frontend format)."""
    page, limit = get_pagination_params()
    all_machines = world_service.get_machines_for_frontend()
    total = len(all_machines)
    start = (page - 1) * limit
    items = all_machines[start : start + limit]
    return success_response(paginated_response(items, total, page, limit))


@world_bp.route("/obstacles", methods=["GET"])
def get_obstacles():
    """List all obstacles (frontend format)."""
    obstacles = world_service.get_obstacles_for_frontend()
    return success_response(obstacles)


@world_bp.route("/carried-resources", methods=["GET"])
def get_carried_resources():
    """List all carried resources (frontend format)."""
    resources = world_service.get_carried_resources_for_frontend()
    return success_response(resources)


# --------------- debug endpoints ---------------

@world_bp.route("/debug/machines", methods=["GET"])
def debug_get_machines():
    """Debug: get all machines in raw format."""
    return success_response(world_service.get_all_machines())


@world_bp.route("/debug/obstacles", methods=["GET"])
def debug_get_obstacles():
    """Debug: get all obstacles in raw format."""
    return success_response(world_service.get_all_obstacles())


@world_bp.route("/debug/reset", methods=["POST"])
def debug_reset():
    """Debug: reset the world."""
    result = world_service.reset_world()
    return success_response(result)
