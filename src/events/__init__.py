"""
Events Package - Event-Driven Architecture

This package provides the event-driven infrastructure:
- event_types: Event definitions (what happened)
- event_bus: Publish/Subscribe mechanism (RabbitMQ)
- consumers: Event handlers (react to events)
"""

from .event_types import (
    EventType,
    BaseEvent,
    FileUploadStartedEvent,
    FileUploadCompletedEvent,
    FileUploadFailedEvent,
    VirusScanRequestedEvent,
    VirusScanCompletedEvent,
    VirusDetectedEvent,
    FileDeletedEvent,
    FileSharedEvent,
    FileDownloadedEvent,
    FilePreviewedEvent,
)

from .event_bus import (
    publish_event,
    event_publisher,
    EventPublisher,
    declare_event_infrastructure,
)

__all__ = [
    # Event Types
    'EventType',
    'BaseEvent',
    'FileUploadStartedEvent',
    'FileUploadCompletedEvent',
    'FileUploadFailedEvent',
    'VirusScanRequestedEvent',
    'VirusScanCompletedEvent',
    'VirusDetectedEvent',
    'FileDeletedEvent',
    'FileSharedEvent',
    'FileDownloadedEvent',
    'FilePreviewedEvent',
    
    # Event Bus
    'publish_event',
    'event_publisher',
    'EventPublisher',
    'declare_event_infrastructure',
]
