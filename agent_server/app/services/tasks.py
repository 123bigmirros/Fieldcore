# -*- coding: utf-8 -*-
"""
Celery 任务定义

简单的异步任务，直接复用 agent_service
"""

from celery import Celery
from ..config import config
from app.logger import logger

# 延迟导入避免循环依赖
def get_task_service():
    from .task_service import task_service
    return task_service

def get_agent_service():
    from .agent_service import agent_service
    return agent_service

# 创建 Celery 实例
celery_app = Celery(
    'agent_server',
    broker=config.CELERY_BROKER_URL,
    backend=config.CELERY_RESULT_BACKEND
)

# 配置
celery_app.conf.update(
    task_serializer='json',
    result_serializer='json',
    accept_content=['json'],
    timezone='UTC',
    enable_utc=True,
    task_acks_late=True,  # 任务完成后才确认，允许取消
    worker_prefetch_multiplier=1,  # 每次只预取一个任务
)


@celery_app.task(bind=True)
def execute_command(self, agent_id: str, command: str):
    """执行命令任务"""
    task_id = self.request.id

    # 延迟导入避免循环依赖
    task_service = get_task_service()
    agent_service = get_agent_service()
    
    # 检查是否是当前有效任务
    if task_service.get_agent_task_id(agent_id) != task_id:
        logger.warning(f"任务 {task_id} 已被新任务取代，取消执行")
        return {'success': False, 'error': '任务已被新任务取代', 'cancelled': True}

    try:
        logger.info(f"🔄 执行命令: agent_id={agent_id}, task_id={task_id}")
        success, result = agent_service.send_command(agent_id, command)
        task_service.clear_agent_task(agent_id)

        if success:
            logger.info(f"✅ 命令执行成功: agent_id={agent_id}")
            return {'success': True, 'result': result, 'error': None}
        else:
            logger.warning(f"⚠️ 命令执行失败: agent_id={agent_id}, error={result}")
            return {'success': False, 'result': None, 'error': result}

    except Exception as e:
        task_service.clear_agent_task(agent_id)
        logger.error(f"❌ 任务执行异常: agent_id={agent_id}, error={str(e)}")
        return {'success': False, 'error': f'任务执行异常: {str(e)}', 'cancelled': False}

