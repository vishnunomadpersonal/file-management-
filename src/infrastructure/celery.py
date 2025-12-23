"""
Celery Application with Advanced RabbitMQ Features

Features:
- Dead Letter Queue (DLX)
- Automatic retries with exponential backoff
- Priority Queues
- Message Persistence
- Message TTL
- Rate Limiting
"""

from celery import Celery as CeleryBase
from celery.signals import task_failure, task_retry, task_success, task_prerun, task_postrun
from core.config import config
from typing import Self
import logging

logger = logging.getLogger(__name__)


class Celery:
    _instance: Self = None

    def __new__(cls: Self) -> Self:
        if cls._instance is None:
            cls._instance = CeleryBase(
                'tasks',
                broker=str(config.RABBITMQ_ENDPOINT),
                backend=str(config.CELERY_BACKEND_ENDPOINT)
            )
            
            # Load advanced configuration
            from infrastructure.celery_config import celery_config
            cls._instance.conf.update(celery_config)
            
        return cls._instance


celery = Celery()
celery.conf.database_engine_options = {'echo': True}
celery.conf.database_table_names = {'task': 'celery_tasks'}


# =============================================================================
# SIGNAL HANDLERS - Task Lifecycle Events
# =============================================================================

@task_prerun.connect
def task_prerun_handler(task_id, task, args, kwargs, **kw):
    """Called before a task is executed."""
    logger.info(f"Task STARTING: {task.name}[{task_id}]")


@task_postrun.connect
def task_postrun_handler(task_id, task, args, kwargs, retval, state, **kw):
    """Called after a task is executed."""
    logger.info(f"Task COMPLETED: {task.name}[{task_id}] state={state}")


@task_success.connect
def task_success_handler(sender, result, **kwargs):
    """Called when a task succeeds."""
    logger.info(f"Task SUCCESS: {sender.name} result={result}")


@task_retry.connect
def task_retry_handler(sender, reason, einfo, **kwargs):
    """Called when a task is being retried."""
    logger.warning(f"Task RETRY: {sender.name} reason={reason}")


@task_failure.connect
def task_failure_handler(task_id, exception, args, kwargs, traceback, einfo, **kw):
    """
    Called when a task fails permanently (after all retries exhausted).
    This is where we could:
    - Log to error tracking (Sentry, etc.)
    - Send alert notifications
    - Store in database for manual review
    """
    logger.error(f"Task FAILED PERMANENTLY: task_id={task_id} error={exception}")
    # TODO: Add notification to admin/monitoring system
