# -*- coding: utf-8 -*-
"""
World Controller - 世界管理核心控制器

只提供 4 个核心 API:
1. machine_register - 注册机器人
2. machine_action - 处理移动、攻击等操作
3. save_world - 持久化世界状态
4. machine_view - 获取机器人视野
"""

from flask import Blueprint, request, jsonify
from ..services.world_service import world_service

world_bp = Blueprint('world', __name__, url_prefix='/api/world')


@world_bp.route('/machine_register', methods=['POST'])
def machine_register():
    """
    注册机器人到世界中

    Request:
        {
            "machine_id": "robot_01",
            "position": [0, 0, 0],
            "owner": "human_01",
            "life_value": 10,
            "machine_type": "worker"
        }

    Response:
        {
            "success": true,
            "machine_id": "robot_01",
            "position": [0, 0, 0]
        }
    """
    data = request.get_json()
    machine_id = data.get('machine_id')

    if not machine_id:
        return jsonify({'success': False, 'error': 'machine_id is required'}), 400

    position = data.get('position', [0, 0, 0])

    success, error = world_service.register_machine(
        machine_id=machine_id,
        position=position,
        owner=data.get('owner', ''),
        life_value=data.get('life_value', 10),
        machine_type=data.get('machine_type', 'worker'),
        size=data.get('size', 1.0),
        facing_direction=tuple(data.get('facing_direction', [1.0, 0.0])),
        view_size=data.get('view_size', 3)
    )

    if success:
        return jsonify({
            'success': True,
            'machine_id': machine_id,
            'position': position
        })
    return jsonify({'success': False, 'error': error}), 400


@world_bp.route('/machine_action', methods=['POST'])
def machine_action():
    """
    处理机器人动作（移动、攻击等）

    将命令添加到命令队列，由后台消费者线程执行

    Request:
        {
            "machine_id": "robot_01",
            "action": "move",  // move, attack, turn
            "params": {
                "direction": [1, 0, 0],
                "distance": 1
            }
        }

    Response:
        {
            "success": true,
            "message": "Command enqueued"
        }
    """
    data = request.get_json()
    machine_id = data.get('machine_id')
    action = data.get('action')
    params = data.get('params', {})

    if not machine_id or not action:
        return jsonify({'success': False, 'error': 'machine_id and action are required'}), 400

    # 将命令添加到队列
    result = world_service.enqueue_command(machine_id, action, params)

    if result.get('success'):
        return jsonify(result)
    return jsonify(result), 400


@world_bp.route('/save_world', methods=['POST'])
def save_world():
    """
    持久化世界状态

    Response:
        {
            "success": true,
            "message": "World saved"
        }
    """
    success = world_service.save_world()
    if success:
        return jsonify({'success': True, 'message': 'World saved'})
    return jsonify({'success': False, 'error': 'Failed to save world'}), 500


@world_bp.route('/machine_view/<machine_id>', methods=['GET'])
def machine_view(machine_id):
    """
    获取机器人视野

    Response:
        {
            "machine_id": "robot_01",
            "center": [0, 0],
            "view_size": 3,
            "cells": [[...], [...], ...]
        }
    """
    result = world_service.get_machine_view(machine_id)
    if result:
        return jsonify(result)
    return jsonify({'error': 'Machine not found'}), 404


# ==================== 前端数据接口 ====================

@world_bp.route('/machines', methods=['GET'])
def get_machines():
    """
    获取所有机器人数据（前端渲染用）

    Response:
        [
            {
                "machine_id": "robot_01",
                "position": [0, 0, 0],
                "life_value": 10,
                "machine_type": "worker",
                "owner": "human_01",
                "status": "active",
                "last_action": "",
                "size": 1.0,
                "facing_direction": [1.0, 0.0],
                "view_size": 3,
                "visibility_radius": 3
            },
            ...
        ]
    """
    machines = world_service.get_machines_for_frontend()
    return jsonify(machines)


@world_bp.route('/obstacles', methods=['GET'])
def get_obstacles():
    """
    获取所有障碍物数据（前端渲染用）

    Response:
        [
            {
                "obstacle_id": "obstacle_01",
                "position": [5, 5, 0],
                "size": 1.0,
                "obstacle_type": "static"
            },
            ...
        ]
    """
    obstacles = world_service.get_obstacles_for_frontend()
    return jsonify(obstacles)


# ==================== 内部调试接口（可选，生产环境可移除）====================

@world_bp.route('/debug/machines', methods=['GET'])
def debug_get_machines():
    """调试用：获取所有机器人（原始格式）"""
    return jsonify(world_service.get_all_machines())


@world_bp.route('/debug/obstacles', methods=['GET'])
def debug_get_obstacles():
    """调试用：获取所有障碍物（原始格式）"""
    return jsonify(world_service.get_all_obstacles())


@world_bp.route('/debug/reset', methods=['POST'])
def debug_reset():
    """调试用：重置世界"""
    result = world_service.reset_world()
    return jsonify({'success': True, 'stats': result})
