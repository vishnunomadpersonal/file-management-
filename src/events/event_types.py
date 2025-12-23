"""
Event-Driven Architecture - Event Definitions

This module defines all events in the system. Events are published when
something happens, and multiple consumers can react to them independently.

Event Flow:
1. API publishes event (e.g., "file.uploaded")
2. RabbitMQ routes event to all interested consumers
3. Each consumer processes independently
4. Consumers can publish new events (chain reactions)
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional, Any
from enum import Enum
import json
import uuid


class EventType(str, Enum):
    """All event types in the system."""
    
    # File Events
    FILE_UPLOAD_STARTED = "file.upload.started"
    FILE_UPLOAD_COMPLETED = "file.upload.completed"
    FILE_UPLOAD_FAILED = "file.upload.failed"
    FILE_DELETED = "file.deleted"
    FILE_SHARED = "file.shared"
    FILE_DOWNLOADED = "file.downloaded"
    FILE_PREVIEWED = "file.previewed"
    
    # Virus Scan Events
    VIRUS_SCAN_REQUESTED = "virus.scan.requested"
    VIRUS_SCAN_COMPLETED = "virus.scan.completed"
    VIRUS_DETECTED = "virus.detected"
    
    # User Events
    USER_QUOTA_WARNING = "user.quota.warning"
    USER_QUOTA_EXCEEDED = "user.quota.exceeded"
    
    # System Events
    TASK_FAILED = "task.failed"
    TASK_RETRY = "task.retry"


@dataclass
class BaseEvent:
    """Base class for all events."""
    
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    event_type: str = ""
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    version: str = "1.0"
    source: str = "filemanager"
    correlation_id: Optional[str] = None  # For tracing related events
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    def to_json(self) -> str:
        return json.dumps(self.to_dict())
    
    @classmethod
    def from_dict(cls, data: dict) -> 'BaseEvent':
        return cls(**data)


@dataclass
class FileUploadStartedEvent(BaseEvent):
    """Published when a file upload begins."""
    
    event_type: str = EventType.FILE_UPLOAD_STARTED.value
    
    # Payload
    file_id: str = ""
    filename: str = ""
    content_type: str = ""
    size: int = 0
    user_id: str = ""
    organization_id: str = ""
    bucket: str = ""
    object_name: str = ""


@dataclass
class FileUploadCompletedEvent(BaseEvent):
    """Published when a file upload completes successfully."""
    
    event_type: str = EventType.FILE_UPLOAD_COMPLETED.value
    
    # Payload
    file_id: str = ""
    filename: str = ""
    content_type: str = ""
    size: int = 0
    user_id: str = ""
    organization_id: str = ""
    bucket: str = ""
    object_name: str = ""
    storage_path: str = ""


@dataclass
class FileUploadFailedEvent(BaseEvent):
    """Published when a file upload fails."""
    
    event_type: str = EventType.FILE_UPLOAD_FAILED.value
    
    # Payload
    file_id: str = ""
    filename: str = ""
    user_id: str = ""
    error: str = ""
    retry_count: int = 0


@dataclass
class VirusScanRequestedEvent(BaseEvent):
    """Published to request a virus scan."""
    
    event_type: str = EventType.VIRUS_SCAN_REQUESTED.value
    
    # Payload
    file_id: str = ""
    filename: str = ""
    bucket: str = ""
    object_name: str = ""
    user_id: str = ""
    priority: int = 5  # 1-10, higher = more urgent


@dataclass
class VirusScanCompletedEvent(BaseEvent):
    """Published when virus scan completes."""
    
    event_type: str = EventType.VIRUS_SCAN_COMPLETED.value
    
    # Payload
    file_id: str = ""
    filename: str = ""
    user_id: str = ""
    is_clean: bool = True
    scan_duration_ms: int = 0


@dataclass
class VirusDetectedEvent(BaseEvent):
    """Published when a virus is detected - HIGH PRIORITY."""
    
    event_type: str = EventType.VIRUS_DETECTED.value
    
    # Payload
    file_id: str = ""
    filename: str = ""
    user_id: str = ""
    organization_id: str = ""
    virus_name: str = ""
    action_taken: str = ""  # quarantined, deleted


@dataclass
class FileDeletedEvent(BaseEvent):
    """Published when a file is deleted."""
    
    event_type: str = EventType.FILE_DELETED.value
    
    # Payload
    file_id: str = ""
    filename: str = ""
    user_id: str = ""
    deleted_by: str = ""
    reason: str = ""


@dataclass
class FileSharedEvent(BaseEvent):
    """Published when a file share link is created."""
    
    event_type: str = EventType.FILE_SHARED.value
    
    # Payload
    file_id: str = ""
    filename: str = ""
    user_id: str = ""
    share_url: str = ""
    expires_in_hours: int = 24


@dataclass
class FileDownloadedEvent(BaseEvent):
    """Published when a file is downloaded."""
    
    event_type: str = EventType.FILE_DOWNLOADED.value
    
    # Payload
    file_id: str = ""
    filename: str = ""
    user_id: str = ""
    download_type: str = ""  # direct, share_link


@dataclass
class FilePreviewedEvent(BaseEvent):
    """Published when a file is previewed (viewed inline)."""
    
    event_type: str = EventType.FILE_PREVIEWED.value
    
    # Payload
    file_id: str = ""
    filename: str = ""
    content_type: str = ""
    user_id: str = ""
    organization_id: str = ""
    preview_type: str = ""  # inline, thumbnail


# Event Registry - maps event type to class
EVENT_REGISTRY = {
    EventType.FILE_UPLOAD_STARTED.value: FileUploadStartedEvent,
    EventType.FILE_UPLOAD_COMPLETED.value: FileUploadCompletedEvent,
    EventType.FILE_UPLOAD_FAILED.value: FileUploadFailedEvent,
    EventType.VIRUS_SCAN_REQUESTED.value: VirusScanRequestedEvent,
    EventType.VIRUS_SCAN_COMPLETED.value: VirusScanCompletedEvent,
    EventType.VIRUS_DETECTED.value: VirusDetectedEvent,
    EventType.FILE_DELETED.value: FileDeletedEvent,
    EventType.FILE_SHARED.value: FileSharedEvent,
    EventType.FILE_DOWNLOADED.value: FileDownloadedEvent,
    EventType.FILE_PREVIEWED.value: FilePreviewedEvent,
}


def parse_event(event_type: str, data: dict) -> BaseEvent:
    """Parse event data into appropriate event class."""
    event_class = EVENT_REGISTRY.get(event_type, BaseEvent)
    return event_class.from_dict(data)
