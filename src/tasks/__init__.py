"""
Celery Tasks with Advanced RabbitMQ Features

Available task modules:
- file_upload_task: File upload processing with retries
- virus_scan_task: Virus scanning with priority support
- notification_task: User notifications with rate limiting
- dlq_processor: Dead Letter Queue handling
"""

from infrastructure.celery import celery
from infrastructure.minio import minioStorage
from core.config import config
import os

# Import all task modules to register them with Celery
from . import file_upload_task
from . import virus_scan_task
from . import notification_task
from . import dlq_processor

# Export commonly used tasks for convenience
from .file_upload_task import upload_file_task, cleanup_failed_upload
from .virus_scan_task import scan_file, scan_file_urgent, bulk_scan
from .notification_task import (
    send_notification,
    notify_file_uploaded,
    notify_virus_detected,
    notify_upload_failed,
    notify_quota_warning
)
from .dlq_processor import process_dead_letter_task, generate_dlq_report

__all__ = [
    # Core
    'celery',
    'minioStorage',
    'config',
    
    # File tasks
    'upload_file_task',
    'cleanup_failed_upload',
    
    # Scan tasks
    'scan_file',
    'scan_file_urgent',
    'bulk_scan',
    
    # Notification tasks
    'send_notification',
    'notify_file_uploaded',
    'notify_virus_detected',
    'notify_upload_failed',
    'notify_quota_warning',
    
    # DLQ tasks
    'process_dead_letter_task',
    'generate_dlq_report',
]
