# -*- coding: utf-8 -*-
"""
认证控制器 - 提供用户注册和 API Key 验证接口
"""

from flask import Blueprint, request, jsonify

from agent_server.app.services.auth_service import auth_service

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')


@auth_bp.route('/register', methods=['POST'])
def register():
    """
    注册新用户

    Request:
        {
            "metadata": {...}  // 可选，用户元数据
        }

    Response:
        {
            "success": true,
            "user_id": "user_xxx",
            "api_key": "sk-xxx",
            "created_at": "2024-01-01T00:00:00",
            "metadata": {...}
        }
    """
    data = request.get_json() or {}
    metadata = data.get('metadata', {})

    success, result = auth_service.register(metadata=metadata)

    if success:
        return jsonify({'success': True, **result}), 201
    return jsonify({'success': False, **result}), 400


@auth_bp.route('/verify', methods=['POST'])
def verify():
    """
    验证 API Key

    Request:
        {
            "api_key": "sk-xxx"
        }

    Response:
        {
            "success": true,
            "user_id": "user_xxx",
            "valid": true
        }
    """
    data = request.get_json() or {}
    api_key = data.get('api_key')

    if not api_key:
        return jsonify({'success': False, 'error': 'api_key is required'}), 400

    is_valid, user_id = auth_service.verify_api_key(api_key)

    if is_valid:
        return jsonify({
            'success': True,
            'valid': True,
            'user_id': user_id
        })
    return jsonify({
        'success': False,
        'valid': False,
        'error': 'Invalid API key'
    }), 401

