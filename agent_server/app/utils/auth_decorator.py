# -*- coding: utf-8 -*-
"""
认证装饰器 - 用于保护需要 API Key 验证的接口
"""

from functools import wraps
from flask import request, jsonify

from agent_server.app.services.auth_service import auth_service


def require_api_key(f):
    """
    装饰器：要求请求包含有效的 API Key

    使用方式:
        @agent_bp.route('/api/agent', methods=['POST'])
        @require_api_key
        def agent_create():
            ...
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        from app.logger import logger
        logger.info(f"🔐 API Key 验证: {request.method} {request.path}")

        # 从请求头或请求体中获取 API Key
        api_key = None

        # 优先从请求头获取 (推荐方式)
        api_key = request.headers.get('Authorization')
        if api_key:
            # 支持 "Bearer sk-xxx" 或 "sk-xxx" 格式
            if api_key.startswith('Bearer '):
                api_key = api_key[7:]
        else:
            # 从请求体获取 (兼容方式)
            data = request.get_json() or {}
            api_key = data.get('api_key')

        if not api_key:
            logger.warning("❌ API Key 缺失")
            return jsonify({
                'success': False,
                'error': 'API key is required. Please provide it in Authorization header or request body.'
            }), 401

        # 验证 API Key
        is_valid, user_id = auth_service.verify_api_key(api_key)
        if not is_valid:
            logger.warning(f"❌ API Key 验证失败")
            return jsonify({
                'success': False,
                'error': 'Invalid API key'
            }), 401

        logger.info(f"✅ API Key 验证成功: user_id={user_id}")
        # 将 user_id 添加到 kwargs，供视图函数使用
        kwargs['user_id'] = user_id
        return f(*args, **kwargs)

    return decorated_function

