"""
Advanced Celery Configuration with RabbitMQ Features

Features implemented:
- Dead Letter Queue (DLX) for failed tasks
- Automatic retries with exponential backoff
- Priority Queues (high, default, low)
- Message Persistence (durable queues)
- Message TTL (time-to-live)
- Task rate limiting
- Task result tracking
"""

from kombu import Exchange, Queue
from datetime import timedelta

# =============================================================================
# EXCHANGES
# =============================================================================

# Main exchange for task routing
default_exchange = Exchange('default', type='direct', durable=True)

# Dead Letter Exchange - receives failed/rejected messages
dlx_exchange = Exchange('dlx', type='direct', durable=True)

# Priority exchange for priority-based routing
priority_exchange = Exchange('priority', type='direct', durable=True)


# =============================================================================
# QUEUES WITH DLX CONFIGURATION
# =============================================================================

# Dead Letter Queue - stores failed tasks for analysis/retry
dead_letter_queue = Queue(
    'dead_letter',
    exchange=dlx_exchange,
    routing_key='dead_letter',
    durable=True,
    queue_arguments={
        'x-message-ttl': 7 * 24 * 60 * 60 * 1000,  # 7 days retention
    }
)

# Default queue with DLX support
default_queue = Queue(
    'default',
    exchange=default_exchange,
    routing_key='default',
    durable=True,
    queue_arguments={
        'x-dead-letter-exchange': 'dlx',
        'x-dead-letter-routing-key': 'dead_letter',
        'x-message-ttl': 24 * 60 * 60 * 1000,  # 24 hours
    }
)

# High priority queue - processed first
high_priority_queue = Queue(
    'high_priority',
    exchange=priority_exchange,
    routing_key='high',
    durable=True,
    queue_arguments={
        'x-dead-letter-exchange': 'dlx',
        'x-dead-letter-routing-key': 'dead_letter',
        'x-max-priority': 10,  # Enable priority (0-10)
        'x-message-ttl': 1 * 60 * 60 * 1000,  # 1 hour - high priority should be fast
    }
)

# Low priority queue - processed when resources available
low_priority_queue = Queue(
    'low_priority',
    exchange=priority_exchange,
    routing_key='low',
    durable=True,
    queue_arguments={
        'x-dead-letter-exchange': 'dlx',
        'x-dead-letter-routing-key': 'dead_letter',
        'x-message-ttl': 72 * 60 * 60 * 1000,  # 72 hours
    }
)

# File processing queue - for upload tasks
file_processing_queue = Queue(
    'file_processing',
    exchange=default_exchange,
    routing_key='file.process',
    durable=True,
    queue_arguments={
        'x-dead-letter-exchange': 'dlx',
        'x-dead-letter-routing-key': 'dead_letter',
        'x-message-ttl': 6 * 60 * 60 * 1000,  # 6 hours
    }
)

# Virus scan queue - for antivirus scanning
virus_scan_queue = Queue(
    'virus_scan',
    exchange=default_exchange,
    routing_key='file.scan',
    durable=True,
    queue_arguments={
        'x-dead-letter-exchange': 'dlx',
        'x-dead-letter-routing-key': 'dead_letter',
        'x-message-ttl': 2 * 60 * 60 * 1000,  # 2 hours
        'x-max-priority': 10,  # Priority support for urgent scans
    }
)

# Notification queue - for sending notifications
notification_queue = Queue(
    'notifications',
    exchange=default_exchange,
    routing_key='notification',
    durable=True,
    queue_arguments={
        'x-dead-letter-exchange': 'dlx',
        'x-dead-letter-routing-key': 'dead_letter',
        'x-message-ttl': 1 * 60 * 60 * 1000,  # 1 hour
    }
)

# Retry queue with delay (for exponential backoff)
retry_queue = Queue(
    'retry',
    exchange=default_exchange,
    routing_key='retry',
    durable=True,
    queue_arguments={
        'x-dead-letter-exchange': 'default',  # Route back to default after TTL
        'x-dead-letter-routing-key': 'default',
        'x-message-ttl': 60 * 1000,  # 1 minute default delay
    }
)


# =============================================================================
# CELERY CONFIGURATION
# =============================================================================

celery_config = {
    # ==========================================================================
    # BROKER SETTINGS (RabbitMQ)
    # ==========================================================================
    'broker_connection_retry_on_startup': True,
    'broker_heartbeat': 10,
    'broker_pool_limit': 10,
    
    # ==========================================================================
    # TASK SETTINGS
    # ==========================================================================
    'task_serializer': 'json',
    'task_compression': 'gzip',
    'task_track_started': True,
    'task_time_limit': 30 * 60,  # 30 minutes hard limit
    'task_soft_time_limit': 25 * 60,  # 25 minutes soft limit (raises exception)
    'task_acks_late': True,  # ACK after task completion (ensures no message loss)
    'task_reject_on_worker_lost': True,  # Requeue if worker dies
    'task_acks_on_failure_or_timeout': False,  # Don't ACK failed tasks
    
    # ==========================================================================
    # RESULT BACKEND SETTINGS
    # ==========================================================================
    'result_serializer': 'json',
    'result_extended': True,  # Store task args and kwargs in result
    'result_expires': timedelta(days=7),  # Keep results for 7 days
    
    # ==========================================================================
    # QUEUE SETTINGS
    # ==========================================================================
    'task_queues': (
        default_queue,
        dead_letter_queue,
        high_priority_queue,
        low_priority_queue,
        file_processing_queue,
        virus_scan_queue,
        notification_queue,
        retry_queue,
    ),
    'task_default_queue': 'default',
    'task_default_exchange': 'default',
    'task_default_routing_key': 'default',
    
    # ==========================================================================
    # ROUTING - Map tasks to specific queues
    # ==========================================================================
    'task_routes': {
        # File processing tasks
        'tasks.file_upload_task.*': {'queue': 'file_processing', 'routing_key': 'file.process'},
        'tasks.virus_scan_task.*': {'queue': 'virus_scan', 'routing_key': 'file.scan'},
        
        # Priority tasks
        'tasks.high_priority.*': {'queue': 'high_priority', 'routing_key': 'high'},
        'tasks.low_priority.*': {'queue': 'low_priority', 'routing_key': 'low'},
        
        # Notifications
        'tasks.notification.*': {'queue': 'notifications', 'routing_key': 'notification'},
    },
    
    # ==========================================================================
    # RETRY SETTINGS (Exponential Backoff)
    # ==========================================================================
    'task_default_retry_delay': 60,  # 1 minute base delay
    'task_max_retries': 5,
    
    # ==========================================================================
    # RATE LIMITING
    # ==========================================================================
    'task_annotations': {
        'tasks.file_upload_task.upload_file_task': {
            'rate_limit': '100/m',  # Max 100 uploads per minute
            'max_retries': 3,
            'default_retry_delay': 60,
        },
        'tasks.virus_scan_task.scan_file': {
            'rate_limit': '50/m',  # Max 50 scans per minute (CPU intensive)
            'max_retries': 3,
            'default_retry_delay': 30,
        },
        'tasks.notification.send_notification': {
            'rate_limit': '200/m',  # Max 200 notifications per minute
            'max_retries': 5,
            'default_retry_delay': 10,
        },
    },
    
    # ==========================================================================
    # WORKER SETTINGS
    # ==========================================================================
    'worker_prefetch_multiplier': 4,  # Fetch 4 tasks per worker at a time
    'worker_concurrency': 4,  # Number of concurrent workers
    'worker_max_tasks_per_child': 100,  # Restart worker after 100 tasks (memory leak prevention)
    'worker_max_memory_per_child': 200000,  # 200MB max memory per worker
    
    # ==========================================================================
    # PERSISTENCE SETTINGS
    # ==========================================================================
    'task_publish_retry': True,
    'task_publish_retry_policy': {
        'max_retries': 3,
        'interval_start': 0,
        'interval_step': 0.2,
        'interval_max': 0.5,
    },
}


# =============================================================================
# TASK ROUTING HELPER
# =============================================================================

def get_queue_for_priority(priority: str = 'default') -> str:
    """Get queue name based on priority level."""
    priority_map = {
        'high': 'high_priority',
        'default': 'default',
        'low': 'low_priority',
        'file': 'file_processing',
        'scan': 'virus_scan',
        'notification': 'notifications',
    }
    return priority_map.get(priority, 'default')


def get_retry_countdown(retry_count: int, base_delay: int = 60) -> int:
    """
    Calculate exponential backoff delay.
    
    retry_count=0: 60s
    retry_count=1: 120s
    retry_count=2: 240s
    retry_count=3: 480s
    retry_count=4: 960s (max)
    """
    max_delay = 15 * 60  # 15 minutes max
    delay = base_delay * (2 ** retry_count)
    return min(delay, max_delay)
