"""
Notification Task with Advanced RabbitMQ Features

Features:
- Rate limiting (prevent notification spam)
- Priority support
- Automatic retries
- DLQ for failed notifications
"""

from infrastructure.celery import celery
from infrastructure.celery_config import get_retry_countdown
import logging
from enum import Enum
from typing import Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class NotificationType(str, Enum):
    FILE_UPLOADED = "file_uploaded"
    FILE_SCANNED = "file_scanned"
    VIRUS_DETECTED = "virus_detected"
    FILE_SHARED = "file_shared"
    FILE_DELETED = "file_deleted"
    UPLOAD_FAILED = "upload_failed"
    QUOTA_WARNING = "quota_warning"


class NotificationChannel(str, Enum):
    EMAIL = "email"
    WEBSOCKET = "websocket"
    WEBHOOK = "webhook"
    IN_APP = "in_app"


@celery.task(
    bind=True,
    name='tasks.notification.send_notification',
    max_retries=5,
    default_retry_delay=10,
    acks_late=True,
    rate_limit='200/m',  # Max 200 notifications per minute
    autoretry_for=(ConnectionError, TimeoutError),
    retry_backoff=True,
    retry_backoff_max=300,
    retry_jitter=True,
)
def send_notification(
    self,
    user_id: str,
    notification_type: str,
    title: str,
    message: str,
    channels: list[str] = None,
    metadata: dict = None,
    priority: int = 5
):
    """
    Send notification to user through specified channels.
    
    Args:
        user_id: Target user ID
        notification_type: Type of notification (see NotificationType)
        title: Notification title
        message: Notification message
        channels: List of channels to send through
        metadata: Additional data (file_id, etc.)
        priority: 0-10, higher = more urgent
    
    Returns:
        dict with delivery status for each channel
    """
    task_id = self.request.id
    retry_count = self.request.retries
    channels = channels or [NotificationChannel.IN_APP.value]
    metadata = metadata or {}
    
    logger.info(
        f"Sending notification: type={notification_type}, "
        f"user={user_id}, channels={channels}, retry={retry_count}"
    )
    
    results = {}
    
    for channel in channels:
        try:
            if channel == NotificationChannel.WEBSOCKET.value:
                # Send via WebSocket
                results[channel] = _send_websocket(user_id, title, message, metadata)
                
            elif channel == NotificationChannel.EMAIL.value:
                # Send via email
                results[channel] = _send_email(user_id, title, message, metadata)
                
            elif channel == NotificationChannel.WEBHOOK.value:
                # Send via webhook
                results[channel] = _send_webhook(user_id, notification_type, metadata)
                
            elif channel == NotificationChannel.IN_APP.value:
                # Store in-app notification
                results[channel] = _store_in_app(user_id, title, message, notification_type, metadata)
                
            else:
                results[channel] = {'status': 'skipped', 'reason': 'unknown_channel'}
                
        except Exception as e:
            logger.error(f"Failed to send via {channel}: {e}")
            results[channel] = {'status': 'failed', 'error': str(e)}
    
    # Check if any critical channels failed
    critical_failures = [
        ch for ch, res in results.items() 
        if res.get('status') == 'failed' and ch in [NotificationChannel.EMAIL.value]
    ]
    
    if critical_failures and retry_count < self.max_retries:
        countdown = get_retry_countdown(retry_count, base_delay=10)
        raise self.retry(
            exc=Exception(f"Critical channel failures: {critical_failures}"),
            countdown=countdown
        )
    
    return {
        'task_id': task_id,
        'user_id': user_id,
        'notification_type': notification_type,
        'channels': results,
        'timestamp': datetime.utcnow().isoformat()
    }


def _send_websocket(user_id: str, title: str, message: str, metadata: dict) -> dict:
    """Send notification via WebSocket."""
    # TODO: Implement WebSocket notification
    # This would integrate with your WebSocket server
    logger.info(f"WebSocket notification to {user_id}: {title}")
    return {'status': 'sent', 'channel': 'websocket'}


def _send_email(user_id: str, title: str, message: str, metadata: dict) -> dict:
    """Send notification via email."""
    # TODO: Implement email sending (SMTP, SendGrid, etc.)
    logger.info(f"Email notification to {user_id}: {title}")
    return {'status': 'sent', 'channel': 'email'}


def _send_webhook(user_id: str, notification_type: str, metadata: dict) -> dict:
    """Send notification via webhook."""
    # TODO: Implement webhook call
    logger.info(f"Webhook notification for {user_id}: {notification_type}")
    return {'status': 'sent', 'channel': 'webhook'}


def _store_in_app(user_id: str, title: str, message: str, notification_type: str, metadata: dict) -> dict:
    """Store in-app notification in database."""
    # TODO: Save to notifications table
    logger.info(f"In-app notification for {user_id}: {title}")
    return {'status': 'stored', 'channel': 'in_app'}


# =============================================================================
# CONVENIENCE FUNCTIONS - Pre-configured notification senders
# =============================================================================

@celery.task(
    bind=True,
    name='tasks.notification.notify_file_uploaded',
    max_retries=3,
)
def notify_file_uploaded(self, user_id: str, file_id: str, filename: str):
    """Notify user that file upload completed."""
    return send_notification.delay(
        user_id=user_id,
        notification_type=NotificationType.FILE_UPLOADED.value,
        title="File Uploaded",
        message=f"Your file '{filename}' has been uploaded successfully.",
        channels=[NotificationChannel.IN_APP.value, NotificationChannel.WEBSOCKET.value],
        metadata={'file_id': file_id, 'filename': filename},
        priority=5
    )


@celery.task(
    bind=True,
    name='tasks.notification.notify_virus_detected',
    max_retries=5,
    queue='high_priority',  # Urgent notification
)
def notify_virus_detected(self, user_id: str, file_id: str, filename: str, virus_name: str):
    """Notify user that virus was detected - HIGH PRIORITY."""
    return send_notification.delay(
        user_id=user_id,
        notification_type=NotificationType.VIRUS_DETECTED.value,
        title="⚠️ Security Alert",
        message=f"A virus ({virus_name}) was detected in '{filename}'. The file has been quarantined.",
        channels=[
            NotificationChannel.IN_APP.value,
            NotificationChannel.EMAIL.value,  # Email for security alerts
            NotificationChannel.WEBSOCKET.value
        ],
        metadata={'file_id': file_id, 'filename': filename, 'virus': virus_name},
        priority=10
    )


@celery.task(
    bind=True,
    name='tasks.notification.notify_upload_failed',
    max_retries=3,
)
def notify_upload_failed(self, user_id: str, filename: str, error: str):
    """Notify user that upload failed."""
    return send_notification.delay(
        user_id=user_id,
        notification_type=NotificationType.UPLOAD_FAILED.value,
        title="Upload Failed",
        message=f"Failed to upload '{filename}': {error}",
        channels=[NotificationChannel.IN_APP.value, NotificationChannel.WEBSOCKET.value],
        metadata={'filename': filename, 'error': error},
        priority=7
    )


@celery.task(
    bind=True,
    name='tasks.notification.notify_quota_warning',
    max_retries=3,
)
def notify_quota_warning(self, user_id: str, used_percent: float, org_name: str = None):
    """Notify user about storage quota warning."""
    return send_notification.delay(
        user_id=user_id,
        notification_type=NotificationType.QUOTA_WARNING.value,
        title="Storage Quota Warning",
        message=f"You've used {used_percent:.1f}% of your storage quota. Consider removing unused files.",
        channels=[NotificationChannel.IN_APP.value, NotificationChannel.EMAIL.value],
        metadata={'used_percent': used_percent, 'organization': org_name},
        priority=6
    )
