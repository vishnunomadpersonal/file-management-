"""
File Upload Task with Advanced RabbitMQ Features

Features:
- Automatic retries with exponential backoff
- Dead Letter Queue support (failed tasks go to DLQ)
- Priority support
- Task tracking and logging
"""

from . import celery, minioStorage, config, os
from minio import S3Error
from infrastructure.celery_config import get_retry_countdown
import logging

logger = logging.getLogger(__name__)


class FileUploadError(Exception):
    """Custom exception for file upload errors."""
    pass


class RetryableError(Exception):
    """Errors that should be retried (network issues, temporary failures)."""
    pass


class NonRetryableError(Exception):
    """Errors that should NOT be retried (invalid data, permanent failures)."""
    pass


@celery.task(
    bind=True,  # Access to self for retry
    name='tasks.file_upload_task.upload_file_task',
    max_retries=5,
    default_retry_delay=60,
    acks_late=True,  # ACK after completion (ensures no message loss)
    reject_on_worker_lost=True,  # Requeue if worker crashes
    autoretry_for=(RetryableError, ConnectionError, TimeoutError),  # Auto-retry these
    retry_backoff=True,  # Exponential backoff
    retry_backoff_max=600,  # Max 10 minutes between retries
    retry_jitter=True,  # Add randomness to prevent thundering herd
)
def upload_file_task(
    self,
    bucket: str,
    upload_id: str,
    total_chunks: int,
    filename: str,
    content_type: str | None = None,
    priority: int = 5  # 0-10, higher = more urgent
):
    """
    Upload file chunks to MinIO storage.
    
    Args:
        bucket: MinIO bucket name
        upload_id: Unique upload identifier
        total_chunks: Number of chunks to combine
        filename: Target filename in storage
        content_type: MIME type
        priority: Task priority (0=low, 10=high)
    
    Retry behavior:
        - Retries 5 times with exponential backoff
        - After all retries fail, task goes to Dead Letter Queue
    """
    task_id = self.request.id
    retry_count = self.request.retries
    
    logger.info(
        f"Upload task started: task_id={task_id}, "
        f"filename={filename}, retry={retry_count}/{self.max_retries}"
    )
    
    upload_dir = os.path.join(config.APP_UPLOAD_DIR, upload_id)
    final_file_path = os.path.join(upload_dir, "final_file")
    
    try:
        # Validate upload directory exists
        if not os.path.exists(upload_dir):
            raise NonRetryableError(f"Upload directory not found: {upload_dir}")
        
        # Combine chunks into final file
        logger.info(f"Combining {total_chunks} chunks for {filename}")
        with open(final_file_path, "wb") as final_file:
            for i in range(total_chunks):
                chunk_path = os.path.join(upload_dir, f"{i}.part")
                if not os.path.exists(chunk_path):
                    raise NonRetryableError(f"Missing chunk: {chunk_path}")
                    
                with open(chunk_path, "rb") as chunk_file:
                    content = chunk_file.read()
                    final_file.write(content)
        
        # Upload to MinIO
        logger.info(f"Uploading {filename} to MinIO bucket: {bucket}")
        with open(final_file_path, 'rb') as file:
            minioStorage.put_object(
                bucket,
                filename,
                file,
                length=-1,
                part_size=10 * 1024 * 1024,
                content_type=content_type or "application/octet-stream",
            )
        
        # Cleanup chunks
        logger.info(f"Cleaning up chunks for {filename}")
        for i in range(total_chunks):
            chunk_path = os.path.join(upload_dir, f"{i}.part")
            if os.path.exists(chunk_path):
                os.remove(chunk_path)
        
        if os.path.exists(final_file_path):
            os.remove(final_file_path)
        
        if os.path.exists(upload_dir):
            os.removedirs(upload_dir)
        
        logger.info(f"Upload completed successfully: {filename}")
        return {
            'status': 'success',
            'filename': filename,
            'bucket': bucket,
            'task_id': task_id
        }
        
    except S3Error as exc:
        # MinIO errors - usually retryable
        logger.error(f"MinIO error uploading {filename}: {exc}")
        countdown = get_retry_countdown(retry_count)
        
        raise self.retry(
            exc=RetryableError(f"MinIO error: {exc}"),
            countdown=countdown,
            max_retries=self.max_retries
        )
        
    except NonRetryableError as exc:
        # Don't retry - data is invalid
        logger.error(f"Non-retryable error for {filename}: {exc}")
        # This will go to Dead Letter Queue
        raise
        
    except RetryableError as exc:
        # Retry with backoff
        countdown = get_retry_countdown(retry_count)
        logger.warning(f"Retryable error for {filename}, retrying in {countdown}s: {exc}")
        raise self.retry(exc=exc, countdown=countdown)
        
    except Exception as exc:
        # Unexpected error - retry with backoff
        logger.error(f"Unexpected error uploading {filename}: {exc}")
        countdown = get_retry_countdown(retry_count)
        
        if retry_count < self.max_retries:
            raise self.retry(exc=exc, countdown=countdown)
        else:
            # All retries exhausted - will go to DLQ
            logger.error(f"All retries exhausted for {filename}, sending to DLQ")
            raise


@celery.task(
    bind=True,
    name='tasks.file_upload_task.cleanup_failed_upload',
    max_retries=3,
)
def cleanup_failed_upload(self, upload_id: str, filename: str):
    """
    Cleanup task for failed uploads.
    Called when upload fails permanently.
    """
    logger.info(f"Cleaning up failed upload: {upload_id}")
    
    upload_dir = os.path.join(config.APP_UPLOAD_DIR, upload_id)
    
    try:
        if os.path.exists(upload_dir):
            import shutil
            shutil.rmtree(upload_dir)
            logger.info(f"Cleaned up directory: {upload_dir}")
        return {'status': 'cleaned', 'upload_id': upload_id}
    except Exception as exc:
        logger.error(f"Cleanup failed: {exc}")
        raise self.retry(exc=exc, countdown=60)
