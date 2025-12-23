from fastapi import APIRouter, UploadFile, Form, Request, Depends, HTTPException, status
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy.orm import Session
from infrastructure.db.mysql import mysql as db
from repositories.file_repository import FileRepo
from services.file_service import FileService
from handlers.file_handler import FileHandler
from api.responses.file_response import FileResponse, UploadInitResponse, UploadChunkResponse, UploadStatusResponse
from typing import Optional
from api.responses.response import SuccessResponse, ErrorResponse
from core.config import config
from constants.file_extensions import FileExtension
from infrastructure.db.mysql import mysql
from dto.file_dto import FileResponseDTO
from api.responses.quarantine_response import VirusScanHealthResponse
from core.security import get_current_user, AuthenticatedUser
from infrastructure.minio import minioStorage
from urllib.parse import quote
import logging
import os

# Event-Driven Architecture
from events import publish_event, FileSharedEvent, FileDownloadedEvent, FilePreviewedEvent

EVENT_DRIVEN_ENABLED = os.environ.get('EVENT_DRIVEN_ENABLED', 'true').lower() == 'true'

logger = logging.getLogger(__name__)


router = APIRouter(
    prefix="/api/v1/file",
    tags=["file"]
)


def get_file_handler(db: Session = Depends(mysql.get_db)) -> FileHandler:
    repo = FileRepo(db=db)
    service = FileService(repo=repo)
    handler = FileHandler(service=service)
    return handler


@router.post("/upload/init/", response_model=SuccessResponse[UploadInitResponse])
async def endpoint(file_handler: FileHandler = Depends(get_file_handler)):
    return await file_handler.upload_initialize()


@router.post("/upload/chunk/", response_model=SuccessResponse[UploadChunkResponse], responses={
    422: {"model": ErrorResponse},
})
async def endpoint(chunk_size: int = Form(..., le=config.APP_MAX_CHUNK_SIZE),
                   upload_id: str = Form(...), chunk_index: int = Form(...), file: UploadFile = Form(...),
                   file_handler: FileHandler = Depends(get_file_handler)):
    return await file_handler.upload_chunk(chunk_size=chunk_size, upload_id=upload_id, chunk_index=chunk_index, file=file)


@router.post("/upload/complete/", response_model=SuccessResponse[FileResponse], responses={
    422: {"model": ErrorResponse},
})
async def endpoint(upload_id: str = Form(...), total_chunks: int = Form(...),
                   total_size: int = Form(...), credential: Optional[str] = Form(None),
                   file_extension: FileExtension = Form(...), content_type: str = Form(...),
                   appointment_id: Optional[str] = Form(None), user_id: str = Form(...),
                   filename: str = Form(...),
                   organization_id: Optional[str] = Form(None), folder_id: Optional[str] = Form(None),
                   detail: Optional[str] = Form(None), file_handler: FileHandler = Depends(get_file_handler)):
    return await file_handler.upload_complete(upload_id=upload_id, total_chunks=total_chunks, total_size=total_size,
                                              file_extension=file_extension, content_type=content_type,
                                              credential=credential, detail=detail, appointment_id=appointment_id,
                                              user_id=user_id, filename=filename,
                                              organization_id=organization_id, folder_id=folder_id)


@router.get('/get/{file_id}', response_model=SuccessResponse[FileResponse], responses={
    404: {"model": ErrorResponse},
    422: {"model": ErrorResponse},
    403: {"model": ErrorResponse}
})
async def endpoint(file_id: str, request: Request, file_handler: FileHandler = Depends(get_file_handler)) -> JSONResponse:
    credential = dict(request.query_params)
    return await file_handler.get_file(file_id=file_id, credential=credential)


@router.get("/appointment/{appointment_id}", response_model=SuccessResponse[list[FileResponseDTO]])
async def get_files_by_appointment(appointment_id: str, file_handler: FileHandler = Depends(get_file_handler)):
    return await file_handler.get_files_by_appointment(appointment_id)


@router.get("/all", response_model=SuccessResponse[list[FileResponseDTO]])
async def list_all_files(user_id: str, file_handler: FileHandler = Depends(get_file_handler)):
    return await file_handler.list_all_files(user_id)


@router.get("/platform/all", response_model=SuccessResponse[list[FileResponseDTO]])
async def list_all_platform_files(
    skip: int = 0,
    limit: int = 100,
    file_handler: FileHandler = Depends(get_file_handler)
):
    """List all files across all organizations (for platform admin)."""
    return await file_handler.list_all_platform_files(skip, limit)


@router.get("/organization/{organization_id}", response_model=SuccessResponse[list[FileResponseDTO]])
async def list_files_by_organization(
    organization_id: str, 
    folder_id: Optional[str] = None,
    file_handler: FileHandler = Depends(get_file_handler)
):
    """List all files for an organization, optionally filtered by folder."""
    return await file_handler.list_files_by_organization(organization_id, folder_id)


@router.delete("/{file_id}", response_model=SuccessResponse)
async def delete_file(file_id: str, file_handler: FileHandler = Depends(get_file_handler)):
    return await file_handler.delete_file(file_id)


@router.get('/status/{file_id}', response_model=SuccessResponse[UploadStatusResponse], responses={
    404: {"model": ErrorResponse},
    422: {"model": ErrorResponse},
    403: {"model": ErrorResponse}
})
async def endpoint(file_id: str, request: Request, file_handler: FileHandler = Depends(get_file_handler)) -> JSONResponse:
    credential = dict(request.query_params)
    return await file_handler.get_upload_status(file_id=file_id, credential=credential)


@router.post('/upload/retry', response_model=SuccessResponse[FileResponse], responses={
    404: {"model": ErrorResponse},
    422: {"model": ErrorResponse},
    403: {"model": ErrorResponse}
})
async def endpoint(file_id: str = Form(...), credential: Optional[str] = Form(None), file_handler: FileHandler = Depends(get_file_handler)) -> JSONResponse:
    return await file_handler.retry_upload(file_id=file_id, credential=credential)


@router.get('/virus-scanner/health', response_model=SuccessResponse[VirusScanHealthResponse], responses={
    503: {"model": ErrorResponse},
    500: {"model": ErrorResponse}
})
async def virus_scanner_health(file_handler: FileHandler = Depends(get_file_handler)) -> JSONResponse:
    """Check the health status of the virus scanner service"""
    return await file_handler.virus_scanner_health()


@router.get('/download/{file_id}', responses={
    401: {"model": ErrorResponse},
    403: {"model": ErrorResponse},
    404: {"model": ErrorResponse}
})
async def download_file(
    file_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
    file_handler: FileHandler = Depends(get_file_handler)
) -> StreamingResponse:
    """
    Download a file with authentication required.
    
    Unlike presigned URLs, this endpoint:
    - Requires valid authentication (JWT token or API key)
    - Validates user has access to the file
    - Streams the file directly from storage through the backend
    
    Similar to Google Cloud - if not logged in, download is denied.
    """
    # Get the file metadata from DB
    file = file_handler.service.repo.get_file(file_id)
    if not file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )
    
    # Check if file is quarantined
    if file.is_quarantined:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This file has been quarantined due to security concerns"
        )
    
    # Check access permissions
    # Super admin can access everything
    # Org admin/users can only access files in their organization
    if current_user.role.value != "super_admin":
        # Check organization access
        if file.organization_id and file.organization_id != current_user.organization_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have access to this file"
            )
        # Check if file belongs to user (for private files without org)
        if not file.organization_id and file.user_id != current_user.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have access to this file"
            )
    
    # Parse bucket and object from file path
    bucket_name = file.path.split("/")[0]
    object_name = "/".join(file.path.split("/")[1:])
    
    try:
        # Get file from MinIO
        response = minioStorage.get_object(bucket_name, object_name)
        
        # Determine content disposition (inline for viewable types, attachment for download)
        content_type = file.content_type or "application/octet-stream"
        filename = file.filename or object_name.split("/")[-1]
        
        # Use inline for images and PDFs, attachment for others
        is_preview = content_type.lower().startswith("image/") or content_type.lower() == "application/pdf"
        if is_preview:
            disposition = f'inline; filename="{filename}"; filename*=UTF-8\'\'{quote(filename)}'
        else:
            disposition = f'attachment; filename="{filename}"; filename*=UTF-8\'\'{quote(filename)}'
        
        # ========================================================
        # EVENT-DRIVEN: Publish preview or download event
        # ========================================================
        if EVENT_DRIVEN_ENABLED:
            try:
                if is_preview:
                    publish_event(FilePreviewedEvent(
                        file_id=file_id,
                        filename=file.filename,
                        content_type=content_type,
                        user_id=current_user.user_id,
                        organization_id=file.organization_id or "",
                        preview_type="inline"
                    ))
                    logger.info(f"Published file.previewed event for file {file_id}")
                else:
                    publish_event(FileDownloadedEvent(
                        file_id=file_id,
                        filename=file.filename,
                        user_id=current_user.user_id,
                        download_type="direct"
                    ))
                    logger.info(f"Published file.downloaded event for file {file_id}")
            except Exception as e:
                logger.error(f"Failed to publish preview/download event (non-fatal): {e}")
        
        # Stream the file to the client
        def iterfile():
            try:
                for chunk in response.stream(32 * 1024):  # 32KB chunks
                    yield chunk
            finally:
                response.close()
                response.release_conn()
        
        return StreamingResponse(
            iterfile(),
            media_type=content_type,
            headers={
                "Content-Disposition": disposition,
                "Content-Length": str(file.size) if file.size else "",
                "Cache-Control": "private, max-age=3600",  # Cache for 1 hour, but private
            }
        )
        
    except Exception as e:
        logger.error(f"Failed to download file {file_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve file from storage"
        )


@router.post('/share/{file_id}', responses={
    401: {"model": ErrorResponse},
    403: {"model": ErrorResponse},
    404: {"model": ErrorResponse}
})
async def generate_share_link(
    file_id: str,
    expires_in_hours: int = 24,
    current_user: AuthenticatedUser = Depends(get_current_user),
    file_handler: FileHandler = Depends(get_file_handler)
) -> JSONResponse:
    """
    Generate a shareable presigned URL for a file.
    
    This creates a time-limited URL that can be shared with anyone,
    even those without an account. The link will expire after the specified time.
    
    - expires_in_hours: How long the link should be valid (default 24 hours, max 168 hours/7 days)
    """
    # Validate expiry time (1 hour to 7 days)
    if expires_in_hours < 1:
        expires_in_hours = 1
    if expires_in_hours > 168:  # 7 days max
        expires_in_hours = 168
    
    # Get the file metadata from DB
    file = file_handler.service.repo.get_file(file_id)
    if not file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )
    
    # Check if file is quarantined
    if file.is_quarantined:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot share quarantined files"
        )
    
    # Check access permissions - user must have access to share
    if current_user.role.value != "super_admin":
        if file.organization_id and file.organization_id != current_user.organization_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to share this file"
            )
        if not file.organization_id and file.user_id != current_user.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to share this file"
            )
    
    # Parse bucket and object from file path
    bucket_name = file.path.split("/")[0]
    object_name = "/".join(file.path.split("/")[1:])
    
    try:
        from datetime import timedelta
        
        # Generate presigned URL with the specified expiry
        share_url = minioStorage.get_presigned_url(
            method="GET",
            bucket_name=bucket_name,
            object_name=object_name,
            expires=timedelta(hours=expires_in_hours),
            response_headers={
                "response-content-disposition": f'attachment; filename="{file.filename}"; filename*=UTF-8\'\'{quote(file.filename or object_name)}'
            }
        )
        
        # ========================================================
        # EVENT-DRIVEN: Publish file.shared event
        # ========================================================
        if EVENT_DRIVEN_ENABLED:
            try:
                publish_event(FileSharedEvent(
                    file_id=file_id,
                    filename=file.filename,
                    user_id=current_user.user_id,
                    share_url=share_url,
                    expires_in_hours=expires_in_hours
                ))
                logger.info(f"Published file.shared event for file {file_id}")
            except Exception as e:
                logger.error(f"Failed to publish share event (non-fatal): {e}")
        
        return JSONResponse(
            content={
                "success": True,
                "data": {
                    "share_url": share_url,
                    "expires_in_hours": expires_in_hours,
                    "filename": file.filename,
                    "file_id": file_id,
                    "generated_by": current_user.user_id,
                }
            }
        )
        
    except Exception as e:
        logger.error(f"Failed to generate share link for file {file_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate share link"
        )
