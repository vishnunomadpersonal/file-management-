"""
Event Bus - Publish/Subscribe Implementation

This is the core of the event-driven architecture.
- Publishers: Emit events when something happens
- Subscribers: React to events they care about
- RabbitMQ: Routes events to all interested subscribers
"""

import json
import logging
from typing import Callable, Dict, List, Any
from kombu import Connection, Exchange, Queue, Producer, Consumer
from kombu.mixins import ConsumerMixin
from core.config import config
from events.event_types import BaseEvent, EventType

logger = logging.getLogger(__name__)


# =============================================================================
# EXCHANGES - Topic-based routing for events
# =============================================================================

# Main event exchange - all events go through here
events_exchange = Exchange(
    'events',
    type='topic',  # Topic exchange for pattern-based routing
    durable=True
)

# Dead letter exchange for failed event processing
events_dlx = Exchange(
    'events.dlx',
    type='direct',
    durable=True
)


# =============================================================================
# QUEUES - Each consumer has its own queue
# =============================================================================

def create_event_queue(name: str, routing_keys: List[str]) -> Queue:
    """Create a queue that subscribes to specific event patterns."""
    return Queue(
        name,
        exchange=events_exchange,
        routing_key=routing_keys[0] if len(routing_keys) == 1 else None,
        durable=True,
        queue_arguments={
            'x-dead-letter-exchange': 'events.dlx',
            'x-dead-letter-routing-key': 'failed',
            'x-message-ttl': 86400000,  # 24 hours
        }
    )


# Pre-defined queues for each consumer
virus_scanner_queue = Queue(
    'events.virus_scanner',
    exchange=events_exchange,
    routing_key='file.upload.completed',  # Listens to upload completed events
    durable=True,
    queue_arguments={
        'x-dead-letter-exchange': 'events.dlx',
        'x-message-ttl': 7200000,  # 2 hours
    }
)

notification_queue = Queue(
    'events.notifications',
    exchange=events_exchange,
    routing_key='#',  # Listens to ALL events (wildcard)
    durable=True,
    queue_arguments={
        'x-dead-letter-exchange': 'events.dlx',
        'x-message-ttl': 3600000,  # 1 hour
    }
)

db_updater_queue = Queue(
    'events.db_updater',
    exchange=events_exchange,
    routing_key='virus.scan.*',  # Listens to all virus scan events
    durable=True,
    queue_arguments={
        'x-dead-letter-exchange': 'events.dlx',
        'x-message-ttl': 86400000,  # 24 hours
    }
)

audit_log_queue = Queue(
    'events.audit_log',
    exchange=events_exchange,
    routing_key='#',  # Listens to ALL events for audit
    durable=True,
    queue_arguments={
        'x-dead-letter-exchange': 'events.dlx',
        'x-message-ttl': 604800000,  # 7 days
    }
)

websocket_queue = Queue(
    'events.websocket',
    exchange=events_exchange,
    routing_key='file.*',  # Listens to all file events
    durable=True,
    queue_arguments={
        'x-dead-letter-exchange': 'events.dlx',
        'x-message-ttl': 60000,  # 1 minute (real-time)
    }
)


# =============================================================================
# EVENT PUBLISHER
# =============================================================================

class EventPublisher:
    """
    Publishes events to RabbitMQ.
    
    Usage:
        publisher = EventPublisher()
        publisher.publish(FileUploadCompletedEvent(
            file_id="123",
            filename="test.txt",
            ...
        ))
    """
    
    _instance = None
    _connection = None
    _producer = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def _get_connection(self):
        """Get or create RabbitMQ connection."""
        if self._connection is None or not self._connection.connected:
            self._connection = Connection(str(config.RABBITMQ_ENDPOINT))
            self._connection.connect()
            self._producer = Producer(
                self._connection.channel(),
                exchange=events_exchange,
                serializer='json'
            )
        return self._connection
    
    def publish(self, event: BaseEvent, routing_key: str = None) -> bool:
        """
        Publish an event to the event bus.
        
        Args:
            event: The event to publish
            routing_key: Optional routing key (defaults to event_type)
        
        Returns:
            True if published successfully
        """
        try:
            self._get_connection()
            
            # Use event type as routing key if not specified
            if routing_key is None:
                routing_key = event.event_type
            
            # Publish the event
            self._producer.publish(
                event.to_dict(),
                routing_key=routing_key,
                declare=[events_exchange],
                delivery_mode=2,  # Persistent
                content_type='application/json'
            )
            
            logger.info(f"Event published: {event.event_type} (id={event.event_id})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to publish event {event.event_type}: {e}")
            return False
    
    def close(self):
        """Close the connection."""
        if self._connection:
            self._connection.close()
            self._connection = None
            self._producer = None


# Global publisher instance
event_publisher = EventPublisher()


def publish_event(event: BaseEvent) -> bool:
    """Convenience function to publish an event."""
    return event_publisher.publish(event)


# =============================================================================
# EVENT CONSUMER BASE CLASS
# =============================================================================

class EventConsumer(ConsumerMixin):
    """
    Base class for event consumers.
    
    Usage:
        class MyConsumer(EventConsumer):
            def get_consumers(self, Consumer, channel):
                return [Consumer(
                    queues=[my_queue],
                    callbacks=[self.handle_event]
                )]
            
            def handle_event(self, body, message):
                # Process event
                message.ack()
    """
    
    def __init__(self, connection_url: str = None):
        self.connection = Connection(connection_url or str(config.RABBITMQ_ENDPOINT))
    
    def get_consumers(self, Consumer, channel):
        """Override in subclass to define which queues to consume."""
        raise NotImplementedError
    
    def on_consume_ready(self, connection, channel, consumers, **kwargs):
        """Called when consumer is ready."""
        logger.info(f"Consumer ready: {self.__class__.__name__}")
    
    def on_consume_end(self, connection, channel):
        """Called when consumer stops."""
        logger.info(f"Consumer stopped: {self.__class__.__name__}")


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_connection():
    """Get a new RabbitMQ connection."""
    return Connection(str(config.RABBITMQ_ENDPOINT))


def declare_event_infrastructure():
    """Declare all exchanges and queues (run on startup)."""
    with get_connection() as conn:
        channel = conn.channel()
        
        # Declare exchanges
        events_exchange.declare(channel=channel)
        events_dlx.declare(channel=channel)
        
        # Declare queues
        for queue in [
            virus_scanner_queue,
            notification_queue,
            db_updater_queue,
            audit_log_queue,
            websocket_queue
        ]:
            queue.declare(channel=channel)
        
        logger.info("Event infrastructure declared successfully")
