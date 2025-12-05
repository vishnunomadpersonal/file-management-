from repositories.file_repository import FileRepo
from dto.file_dto import UploadFileDTO, UploadChunkDTO, RetryUploadFileDTO
from typing import Dict, Any, Optional
from entities.file import File
import os
import aiofiles
from fastapi.exceptions import RequestValidationError
from constants.errors import ValidatonErrors
from infrastructure.minio import minioStorage
from dto.file_dto import FileBaseDTO
from services.base_service import BaseService
from exceptions.http_exception import PermissionException, FileNotFoundException, FileUploadedException, FilePendingUploadException
from exceptions.virus_exception import VirusDetectedException, VirusScanException
from tasks.file_upload_task import upload_file_task
import uuid
from core.config import config
from celery.result import AsyncResult
from tasks import celery
from constants.upload_stauts import UploadStatus
from infrastructure.virus_scanner import virus_scanner
import logging
import traceback
from datetime import datetime
from urllib.parse import quote

logger = logging.getLogger(__name__)

class FileService(BaseService[FileRepo]):
    def __init__(self, repo: FileRepo) -> None:
        super().__init__(repo=repo)

    async def upload_initialize(self) -> str:
        upload_id = str(uuid.uuid4())
        os.makedirs(os.path.join(
            config.APP_UPLOAD_DIR, upload_id), exist_ok=True)
        return upload_id

    async def upload_chunk(self, payload: UploadChunkDTO) -> None:
        upload_dir = os.path.join(config.APP_UPLOAD_DIR, payload.upload_id)
        chunk_path = os.path.join(upload_dir, f"{payload.chunk_index}.part")
        async with aiofiles.open(chunk_path, "wb") as chunk_file:
            content = await payload.file.read()
            if len(content) > config.APP_MAX_CHUNK_SIZE:
                raise RequestValidationError(errors=[{
                    'loc': ('body', 'file'),
                    'msg': ValidatonErrors.LE_CHUNCK_SIZE,
                    'type': 'value_error'
                }],
                    body={"file": "invalid_size"})
            await chunk_file.write(content)

    async def _assemble_chunks_for_scanning(self, upload_path: str, total_chunks: int) -> str:
        """Assemble chunks into a single file for virus scanning"""
        assembled_file_path = os.path.join(upload_path, "assembled_for_scan")
        
        try:
            with open(assembled_file_path, "wb") as assembled_file:
                for i in range(total_chunks):
                    chunk_path = os.path.join(upload_path, f"{i}.part")
                    if not os.path.exists(chunk_path):
                        raise FileNotFoundError(f"Missing chunk {i} for upload")
                    
                    with open(chunk_path, "rb") as chunk_file:
                        assembled_file.write(chunk_file.read())
            
            logger.info(f"Assembled {total_chunks} chunks into {assembled_file_path}")
            return assembled_file_path
            
        except Exception as e:
            logger.error(f"Failed to assemble chunks: {str(e)}")
            # Clean up partial file if it exists
            if os.path.exists(assembled_file_path):
                os.remove(assembled_file_path)
            raise

    async def upload_complete(self, payload: UploadFileDTO) -> File:
        assembled_file_path = None
        try:
            logger.info(f"Starting upload_complete for upload_id: {payload.upload_id}")

            # First, check if a file record with this upload_id already exists (idempotency)
            existing_file = self.repo.db.query(File).filter(File.upload_id == payload.upload_id).first()
            if existing_file:
                logger.warning(f"File with upload_id {payload.upload_id} already exists. Returning existing file record.")
                return existing_file

            # Check if upload directory exists
            upload_path = os.path.join(config.APP_UPLOAD_DIR, payload.upload_id)
            if not os.path.exists(upload_path):
                logger.error(f"Upload directory not found: {upload_path}")
                raise FileNotFoundError(f"Upload directory not found for upload_id: {payload.upload_id}")

            # Assemble chunks for virus scanning
            assembled_file_path = await self._assemble_chunks_for_scanning(upload_path, payload.total_chunks)
            
            # VIRUS SCAN - Scan the assembled file
            scan_result = await virus_scanner.scan_file(assembled_file_path)
            logger.info(f"Virus scan result for {payload.upload_id}: {scan_result}")
            
            # Initialize virus scan fields
            virus_scan_status = 'clean'
            virus_scan_date = datetime.utcnow()
            is_quarantined = False
            quarantine_reason = None
            
            # Check if file is infected
            if scan_result.get('is_infected'):
                virus_scan_status = 'infected'
                is_quarantined = config.QUARANTINE_INFECTED_FILES
                quarantine_reason = f"Virus detected: {scan_result.get('virus_name', 'Unknown threat')}"
                
                logger.error(f"VIRUS DETECTED in upload {payload.upload_id}: {scan_result.get('virus_name')}")
                
                # Clean up assembled file immediately
                if assembled_file_path and os.path.exists(assembled_file_path):
                    os.remove(assembled_file_path)
                    assembled_file_path = None
                
                # Create quarantined file record
                file_dto = FileBaseDTO(
                    upload_id=payload.upload_id,
                    path="QUARANTINED" if config.QUARANTINE_INFECTED_FILES else "DELETED",
                    content_type=payload.content_type,
                    size=payload.total_size,
                    appointment_id=payload.appointment_id,
                    user_id=payload.user_id,
                    filename=payload.filename,
                    credential=payload.credential,
                    detail=payload.detail,
                    celery_task_id="",  # No Celery task for infected files
                    virus_scan_status=virus_scan_status,
                    virus_scan_result=scan_result,
                    virus_scan_date=virus_scan_date,
                    is_quarantined=is_quarantined,
                    quarantine_reason=quarantine_reason
                )
                
                file = self.repo.create_file(file_dto)
                
                # Raise exception to prevent further processing
                raise VirusDetectedException(
                    message=quarantine_reason,
                    virus_name=scan_result.get('virus_name'),
                    scan_result=scan_result
                )
            
            elif scan_result.get('scan_result') == 'SCAN_ERROR':
                # Handle scan errors
                virus_scan_status = 'error'
                quarantine_reason = f"Scan failed: {scan_result.get('error', 'Unknown error')}"
                logger.warning(f"Virus scan failed for {payload.upload_id}: {quarantine_reason}")
                
                # Depending on configuration, we might want to quarantine or allow
                if config.QUARANTINE_INFECTED_FILES:  # Use same setting for scan errors
                    is_quarantined = True
                    logger.warning(f"Quarantining file due to scan error: {payload.upload_id}")
            
            elif scan_result.get('scan_result') == 'SCAN_DISABLED':
                virus_scan_status = 'disabled'
                logger.info(f"Virus scanning disabled for {payload.upload_id}")
            
            # File is clean or scan was disabled - proceed with normal upload
            # Determine bucket
            if not payload.credential:
                bucket = minioStorage.public_bucket
            else:
                bucket = minioStorage.private_bucket

            filename = f"{payload.upload_id}.{payload.file_extension.value}"
            logger.info(f"Creating Celery task for bucket: {bucket}, filename: {filename}")

            # Create Celery task (only if not quarantined)
            celery_task_id = ""
            if not is_quarantined:
                celery_task = upload_file_task.delay(
                    bucket=bucket,
                    upload_id=payload.upload_id,
                    total_chunks=payload.total_chunks,
                    filename=filename,
                    content_type=payload.content_type,
                )
                celery_task_id = celery_task.id
                logger.info(f"Celery task created with ID: {celery_task.id}")

            # Create file record in database with scan results
            file_dto = FileBaseDTO(
                upload_id=payload.upload_id,
                path=f"{bucket}/{filename}" if not is_quarantined else "QUARANTINED",
                content_type=payload.content_type,
                detail=payload.detail,
                size=payload.total_size,
                credential=payload.credential,
                celery_task_id=celery_task_id,
                appointment_id=payload.appointment_id,
                user_id=payload.user_id,
                filename=payload.filename,
                virus_scan_status=virus_scan_status,
                virus_scan_result=scan_result,
                virus_scan_date=virus_scan_date,
                is_quarantined=is_quarantined,
                quarantine_reason=quarantine_reason
            )
            logger.info(f"Creating file record with DTO: {file_dto}")

            file = self.repo.create_file(file_dto)
            logger.info(f"File record created successfully with ID: {file.id}")
            
            return file

        except VirusDetectedException:
            # Re-raise virus exceptions
            raise
        except FileNotFoundError:
            # Re-raise FileNotFoundError as is
            raise
        except Exception as e:
            logger.error(f"Error in upload_complete: {str(e)}\n{traceback.format_exc()}")
            # Re-raise the original exception so it can be handled by the handler
            raise
        finally:
            # Clean up assembled file if it still exists
            if assembled_file_path and os.path.exists(assembled_file_path):
                try:
                    os.remove(assembled_file_path)
                    logger.info(f"Cleaned up assembled file: {assembled_file_path}")
                except Exception as e:
                    logger.warning(f"Failed to clean up assembled file {assembled_file_path}: {str(e)}")

    async def get_download_link(self, file: File) -> str:
        bucket_name = file.path.split("/")[0]
        object_name = "/".join(file.path.split("/")[1:])

        # Choose inline vs attachment based on content type
        disposition_type = self._should_display_inline(file.content_type)

        # Set filename via Content-Disposition for correct save-as name
        # Use both filename and RFC 5987 filename* for better compatibility
        safe_filename = file.filename or object_name
        disposition = f"{disposition_type}; filename=\"{safe_filename}\"; filename*=UTF-8''{quote(safe_filename)}"

        if not file.credential:
            # Prefer presigned URL (for filename headers). Fallback to direct HTTPS URL if signing fails.
            try:
                return minioStorage.get_presigned_url(
                    method="GET",
                    bucket_name=bucket_name,
                    object_name=object_name,
                    response_headers={"response-content-disposition": disposition},
                )
            except Exception as e:
                logger.error(f"Presign failed for public object {bucket_name}/{object_name}: {str(e)}")
                # Fallback to direct external URL (no Content-Disposition control)
                return f"https://{config.MINIO_EXTERNAL_ENDPOINT}/{bucket_name}/{object_name}"
        else:
            # Ensure credential values are strings for signing
            for key, value in file.credential.items():
                if not isinstance(value, str):
                    file.credential[key] = str(value)
            # For private files, presign is required; let exceptions bubble up to surface the error
            return minioStorage.get_presigned_url(
                method="GET",
                bucket_name=bucket_name,
                object_name=object_name,
                response_headers={"response-content-disposition": disposition},
                extra_query_params=file.credential,
            )

    def _should_display_inline(self, content_type: Optional[str]) -> str:
        """Return 'inline' for content types we want to display in-browser, else 'attachment'."""
        if not content_type:
            return "attachment"
        normalized = content_type.lower()
        # Display PDFs and images inline by default
        if normalized == "application/pdf" or normalized.startswith("image/"):
            return "inline"
        return "attachment"


    async def get_files_by_appointment(self, appointment_id: str) -> list[File]:
        # In a real app, you'd validate the appointment name here
        return self.repo.get_files_by_appointment(appointment_id)

    async def list_all_files(self, user_id: str) -> list[tuple]:
        return self.repo.list_all_files(user_id)

    async def delete_file(self, file_id: str):
        # First get the file record to extract MinIO path info
        file = self.repo.get_file(file_id)
        if file:
            # Delete from MinIO
            try:
                bucket_name = file.path.split("/")[0]
                object_name = "/".join(file.path.split("/")[1:])
                minioStorage.remove_object(bucket_name, object_name)
                logger.info(f"Deleted file from MinIO: {bucket_name}/{object_name}")
            except Exception as e:
                logger.error(f"Failed to delete file from MinIO: {str(e)}")
                # Continue with DB deletion even if MinIO deletion fails
            
            # Delete from database
            return self.repo.delete_file(file_id)
        return None
    async def get_file(self, id: id, credential=Dict[str, Any]) -> File:
        file = self.repo.get_file(id=id)
        if file == None:
            raise FileNotFoundException
        if file.credential and credential != file.credential:
            raise PermissionException()
        return file

    async def get_upload_status(self, file_id: str, credential=Dict[str, Any]) -> str:
        file = await self.get_file(id=file_id, credential=credential)
        result = AsyncResult(file.celery_task_id)
        return result.state

    async def retry_upload(self, payload: RetryUploadFileDTO):
        file = await self.get_file(id=payload.id, credential=payload.credential)
        result = AsyncResult(file.celery_task_id)
        if result.status == UploadStatus.SUCCESS.value:
            raise FileUploadedException()
        if result.status == UploadStatus.PENDING.value or result.status == UploadStatus.STARTED.value:
            raise FilePendingUploadException()
        meta = celery.backend.get_task_meta(file.celery_task_id)
        upload_file_task.apply_async(
            args=meta['args'], kwargs=meta['kwargs'], task_id=file.celery_task_id)
        return file
