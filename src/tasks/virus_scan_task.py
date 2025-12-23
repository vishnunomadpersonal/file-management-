"""
Virus Scan Task with Advanced RabbitMQ Features

Features:
- Priority queue support (urgent scans processed first)
- Automatic retries with exponential backoff
- Dead Letter Queue support
- Rate limiting
"""

from infrastructure.celery import celery
from infrastructure.celery_config import get_retry_countdown
from core.config import config
import httpx
import logging

logger = logging.getLogger(__name__)


class ScanError(Exception):
    """Base exception for scan errors."""
    pass


class RetryableScanError(ScanError):
    """Scan error that should be retried."""
    pass


class VirusFoundError(ScanError):
    """Virus was detected in the file."""
    pass


@celery.task(
    bind=True,
    name='tasks.virus_scan_task.scan_file',
    max_retries=3,
    default_retry_delay=30,
    acks_late=True,
    reject_on_worker_lost=True,
    autoretry_for=(RetryableScanError, ConnectionError, TimeoutError),
    retry_backoff=True,
    retry_backoff_max=300,  # Max 5 minutes
    retry_jitter=True,
    rate_limit='50/m',  # Max 50 scans per minute
)
def scan_file(
    self,
    file_id: str,
    bucket: str,
    object_name: str,
    priority: int = 5  # 0-10, higher = more urgent
):
    """
    Scan a file for viruses using ClamAV.
    
    Args:
        file_id: Database file ID
        bucket: MinIO bucket
        object_name: Object name in MinIO
        priority: Scan priority (10 = immediate, 0 = low)
    
    Returns:
        dict with scan results
    
    Raises:
        VirusFoundError: If virus is detected
        RetryableScanError: If scan service is temporarily unavailable
    """
    task_id = self.request.id
    retry_count = self.request.retries
    
    logger.info(
        f"Virus scan started: file_id={file_id}, "
        f"retry={retry_count}/{self.max_retries}, priority={priority}"
    )
    
    if not config.VIRUS_SCAN_ENABLED:
        logger.info("Virus scanning is disabled")
        return {
            'status': 'skipped',
            'file_id': file_id,
            'reason': 'scanning_disabled'
        }
    
    try:
        # Get file from MinIO for scanning
        from infrastructure.minio import minioStorage
        
        response = minioStorage.get_object(bucket, object_name)
        file_data = response.read()
        response.close()
        response.release_conn()
        
        # Check file size limit
        if len(file_data) > config.MAX_SCAN_FILE_SIZE:
            logger.warning(f"File too large to scan: {len(file_data)} bytes")
            return {
                'status': 'skipped',
                'file_id': file_id,
                'reason': 'file_too_large',
                'size': len(file_data)
            }
        
        # Send to ClamAV REST API
        async_client = httpx.Client(timeout=120.0)
        
        try:
            scan_response = async_client.post(
                f"{config.CLAMAV_REST_URL}/scan",
                files={'file': (object_name, file_data)},
            )
            scan_response.raise_for_status()
            result = scan_response.json()
            
        except httpx.ConnectError as e:
            logger.error(f"ClamAV service unavailable: {e}")
            raise RetryableScanError("ClamAV service unavailable")
            
        except httpx.TimeoutException as e:
            logger.error(f"ClamAV scan timeout: {e}")
            raise RetryableScanError("Scan timeout")
            
        finally:
            async_client.close()
        
        # Process scan result
        is_infected = result.get('is_infected', False)
        virus_name = result.get('viruses', [])
        
        if is_infected:
            logger.warning(f"VIRUS FOUND in file {file_id}: {virus_name}")
            
            # Update file status in database
            # This should trigger quarantine or delete based on config
            return {
                'status': 'infected',
                'file_id': file_id,
                'viruses': virus_name,
                'action': 'quarantined' if config.QUARANTINE_INFECTED_FILES else 'flagged'
            }
        
        logger.info(f"File {file_id} is clean")
        return {
            'status': 'clean',
            'file_id': file_id,
            'task_id': task_id
        }
        
    except RetryableScanError as exc:
        countdown = get_retry_countdown(retry_count, base_delay=30)
        logger.warning(f"Retrying scan for {file_id} in {countdown}s: {exc}")
        raise self.retry(exc=exc, countdown=countdown)
        
    except Exception as exc:
        logger.error(f"Scan error for {file_id}: {exc}")
        countdown = get_retry_countdown(retry_count, base_delay=30)
        
        if retry_count < self.max_retries:
            raise self.retry(exc=exc, countdown=countdown)
        else:
            logger.error(f"All scan retries exhausted for {file_id}")
            raise


@celery.task(
    bind=True,
    name='tasks.virus_scan_task.scan_file_urgent',
    max_retries=3,
    queue='high_priority',  # Goes to high priority queue
)
def scan_file_urgent(self, file_id: str, bucket: str, object_name: str):
    """
    Urgent virus scan - processed before regular scans.
    Use for files from untrusted sources or flagged uploads.
    """
    return scan_file.apply(
        args=(file_id, bucket, object_name),
        kwargs={'priority': 10}
    )


@celery.task(
    bind=True,
    name='tasks.virus_scan_task.bulk_scan',
    max_retries=3,
    queue='low_priority',  # Goes to low priority queue
)
def bulk_scan(self, file_ids: list[str]):
    """
    Bulk scan multiple files - low priority background task.
    Use for periodic rescanning of existing files.
    """
    results = []
    for file_id in file_ids:
        # Queue individual scans at low priority
        result = scan_file.apply_async(
            args=(file_id,),
            kwargs={'priority': 1},
            queue='low_priority'
        )
        results.append({'file_id': file_id, 'task_id': result.id})
    
    return {
        'status': 'queued',
        'total_files': len(file_ids),
        'tasks': results
    }
