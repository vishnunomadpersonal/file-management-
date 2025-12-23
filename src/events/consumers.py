"""
Event Consumers - React to events from the Event Bus

Each consumer listens to specific events and processes them independently.
This is the core of event-driven architecture - decoupled services that
react to events rather than being called directly.
"""

import logging
from kombu import Connection, Consumer
from kombu.mixins import ConsumerMixin
from core.config import config
from events.event_bus import (
    virus_scanner_queue,
    notification_queue,
    db_updater_queue,
    audit_log_queue,
    websocket_queue,
    publish_event,
    get_connection
)
from events.event_types import (
    EventType,
    VirusScanCompletedEvent,
    VirusDetectedEvent,
    parse_event
)

logger = logging.getLogger(__name__)


# =============================================================================
# VIRUS SCANNER CONSUMER
# =============================================================================

class VirusScannerConsumer(ConsumerMixin):
    """
    Listens to: file.upload.completed
    Action: Triggers virus scan for uploaded files
    Publishes: virus.scan.completed or virus.detected
    """
    
    def __init__(self):
        self.connection = get_connection()
    
    def get_consumers(self, Consumer, channel):
        return [Consumer(
            queues=[virus_scanner_queue],
            callbacks=[self.on_file_uploaded],
            accept=['json']
        )]
    
    def on_file_uploaded(self, body, message):
        """Handle file.upload.completed event - trigger virus scan."""
        try:
            logger.info(f"VirusScanner received event: {body.get('event_type')}")
            
            file_id = body.get('file_id')
            filename = body.get('filename')
            bucket = body.get('bucket')
            object_name = body.get('object_name')
            user_id = body.get('user_id')
            correlation_id = body.get('event_id')  # Chain events
            
            # Perform virus scan
            is_clean, virus_name = self._scan_file(bucket, object_name)
            
            if is_clean:
                # Publish scan completed event
                publish_event(VirusScanCompletedEvent(
                    file_id=file_id,
                    filename=filename,
                    user_id=user_id,
                    is_clean=True,
                    correlation_id=correlation_id
                ))
            else:
                # Publish virus detected event (HIGH PRIORITY)
                publish_event(VirusDetectedEvent(
                    file_id=file_id,
                    filename=filename,
                    user_id=user_id,
                    virus_name=virus_name,
                    action_taken='quarantined',
                    correlation_id=correlation_id
                ))
            
            message.ack()
            
        except Exception as e:
            logger.error(f"Virus scan failed: {e}")
            message.reject(requeue=True)  # Retry
    
    def _scan_file(self, bucket: str, object_name: str) -> tuple[bool, str]:
        """Perform actual virus scan using ClamAV."""
        try:
            import httpx
            from infrastructure.minio import minioStorage
            
            # Get file from MinIO
            response = minioStorage.get_object(bucket, object_name)
            file_data = response.read()
            response.close()
            response.release_conn()
            
            # Send to ClamAV
            client = httpx.Client(timeout=120.0)
            scan_response = client.post(
                f"{config.CLAMAV_REST_URL}/scan",
                files={'file': (object_name, file_data)}
            )
            client.close()
            
            result = scan_response.json()
            is_infected = result.get('is_infected', False)
            viruses = result.get('viruses', [])
            
            return (not is_infected, viruses[0] if viruses else None)
            
        except Exception as e:
            logger.error(f"Scan error: {e}")
            return (True, None)  # Assume clean on error (configurable)


# =============================================================================
# DATABASE UPDATER CONSUMER
# =============================================================================

class DatabaseUpdaterConsumer(ConsumerMixin):
    """
    Listens to: virus.scan.* (all virus scan events)
    Action: Updates file status in database
    """
    
    def __init__(self):
        self.connection = get_connection()
    
    def get_consumers(self, Consumer, channel):
        return [Consumer(
            queues=[db_updater_queue],
            callbacks=[self.on_scan_event],
            accept=['json']
        )]
    
    def on_scan_event(self, body, message):
        """Handle virus scan events - update database."""
        try:
            event_type = body.get('event_type')
            file_id = body.get('file_id')
            
            logger.info(f"DBUpdater received: {event_type} for file {file_id}")
            
            if event_type == EventType.VIRUS_SCAN_COMPLETED.value:
                self._update_file_status(file_id, 'clean', False)
                
            elif event_type == EventType.VIRUS_DETECTED.value:
                virus_name = body.get('virus_name', 'unknown')
                self._update_file_status(file_id, 'infected', True, virus_name)
            
            message.ack()
            
        except Exception as e:
            logger.error(f"DB update failed: {e}")
            message.reject(requeue=True)
    
    def _update_file_status(self, file_id: str, status: str, quarantined: bool, reason: str = None):
        """Update file in database."""
        # TODO: Implement actual database update
        from infrastructure.database import SessionLocal
        from entities.file import File
        
        try:
            db = SessionLocal()
            file = db.query(File).filter(File.id == file_id).first()
            if file:
                file.virus_scan_status = status
                file.is_quarantined = quarantined
                if reason:
                    file.quarantine_reason = reason
                db.commit()
                logger.info(f"Updated file {file_id}: status={status}, quarantined={quarantined}")
            db.close()
        except Exception as e:
            logger.error(f"DB update error: {e}")


# =============================================================================
# NOTIFICATION CONSUMER
# =============================================================================

class NotificationConsumer(ConsumerMixin):
    """
    Listens to: # (ALL events)
    Action: Sends notifications to users based on event type
    """
    
    def __init__(self):
        self.connection = get_connection()
    
    def get_consumers(self, Consumer, channel):
        return [Consumer(
            queues=[notification_queue],
            callbacks=[self.on_event],
            accept=['json']
        )]
    
    def on_event(self, body, message):
        """Handle any event - decide if notification needed."""
        try:
            event_type = body.get('event_type')
            user_id = body.get('user_id')
            
            logger.info(f"NotificationConsumer received: {event_type}")
            
            # Decide which events need notifications
            if event_type == EventType.FILE_UPLOAD_COMPLETED.value:
                self._notify_upload_complete(body)
                
            elif event_type == EventType.VIRUS_DETECTED.value:
                self._notify_virus_detected(body)  # URGENT
                
            elif event_type == EventType.FILE_SHARED.value:
                self._notify_file_shared(body)
            
            message.ack()
            
        except Exception as e:
            logger.error(f"Notification failed: {e}")
            message.ack()  # Don't retry notifications
    
    def _notify_upload_complete(self, body):
        """Send notification for completed upload."""
        logger.info(f"📤 Notification: File '{body.get('filename')}' uploaded successfully")
        # TODO: WebSocket push, email, etc.
    
    def _notify_virus_detected(self, body):
        """Send URGENT notification for virus detection."""
        logger.warning(f"🚨 URGENT: Virus '{body.get('virus_name')}' detected in '{body.get('filename')}'")
        # TODO: Email, SMS, push notification
    
    def _notify_file_shared(self, body):
        """Send notification for shared file."""
        logger.info(f"🔗 Notification: File '{body.get('filename')}' shared")


# =============================================================================
# WEBSOCKET CONSUMER
# =============================================================================

class WebSocketConsumer(ConsumerMixin):
    """
    Listens to: file.* (all file events)
    Action: Pushes real-time updates to frontend via WebSocket
    """
    
    def __init__(self):
        self.connection = get_connection()
    
    def get_consumers(self, Consumer, channel):
        return [Consumer(
            queues=[websocket_queue],
            callbacks=[self.on_file_event],
            accept=['json']
        )]
    
    def on_file_event(self, body, message):
        """Push file events to frontend via WebSocket."""
        try:
            event_type = body.get('event_type')
            user_id = body.get('user_id')
            
            logger.info(f"WebSocket push: {event_type} to user {user_id}")
            
            # TODO: Push to WebSocket server
            # websocket_server.send_to_user(user_id, {
            #     'type': event_type,
            #     'data': body
            # })
            
            message.ack()
            
        except Exception as e:
            logger.error(f"WebSocket push failed: {e}")
            message.ack()


# =============================================================================
# AUDIT LOG CONSUMER
# =============================================================================

class AuditLogConsumer(ConsumerMixin):
    """
    Listens to: # (ALL events)
    Action: Logs everything for audit trail
    """
    
    def __init__(self):
        self.connection = get_connection()
    
    def get_consumers(self, Consumer, channel):
        return [Consumer(
            queues=[audit_log_queue],
            callbacks=[self.on_event],
            accept=['json']
        )]
    
    def on_event(self, body, message):
        """Log every event for audit."""
        try:
            event_type = body.get('event_type')
            event_id = body.get('event_id')
            user_id = body.get('user_id', 'system')
            timestamp = body.get('timestamp')
            
            # Log to audit system
            logger.info(
                f"AUDIT: {timestamp} | {event_type} | "
                f"user={user_id} | event_id={event_id}"
            )
            
            # TODO: Store in audit table
            # self._save_to_audit_table(body)
            
            message.ack()
            
        except Exception as e:
            logger.error(f"Audit log failed: {e}")
            message.ack()


# =============================================================================
# CONSUMER REGISTRY
# =============================================================================

CONSUMERS = {
    'virus_scanner': VirusScannerConsumer,
    'db_updater': DatabaseUpdaterConsumer,
    'notification': NotificationConsumer,
    'websocket': WebSocketConsumer,
    'audit_log': AuditLogConsumer,
}


def start_consumer(name: str):
    """Start a specific consumer."""
    if name not in CONSUMERS:
        raise ValueError(f"Unknown consumer: {name}")
    
    consumer = CONSUMERS[name]()
    logger.info(f"Starting consumer: {name}")
    consumer.run()


def start_all_consumers():
    """Start all consumers (for development/testing)."""
    import threading
    
    threads = []
    for name, consumer_class in CONSUMERS.items():
        consumer = consumer_class()
        thread = threading.Thread(target=consumer.run, name=name, daemon=True)
        thread.start()
        threads.append(thread)
        logger.info(f"Started consumer thread: {name}")
    
    return threads
