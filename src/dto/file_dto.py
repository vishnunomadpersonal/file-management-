from pydantic import BaseModel
from typing import Any, Dict, Optional
from fastapi import UploadFile
from constants.file_extensions import FileExtension
from datetime import datetime

class UploadChunkDTO(BaseModel):
    chunk_size: int
    file: UploadFile
    upload_id: str
    chunk_index: int

class UploadFileDTO(BaseModel):
    upload_id: str
    total_chunks: int
    total_size: int
    file_extension: FileExtension
    content_type: str
    size: int
    detail: Optional[Dict[str, Any]]
    credential: Optional[Dict[str, Any]]
    appointment_id: str
    user_id: str
    filename: str

class FileBaseDTO(BaseModel):
    upload_id: str
    path: str
    credential: Optional[Dict[str, Any]]
    content_type: str
    size: int
    detail: Optional[Dict[str, Any]]
    celery_task_id: str
    appointment_id: str
    user_id: str
    filename: str
    
    # Virus scanning fields
    virus_scan_status: str = 'pending'
    virus_scan_result: Optional[Dict[str, Any]] = None
    virus_scan_date: Optional[datetime] = None
    is_quarantined: bool = False
    quarantine_reason: Optional[str] = None

class FileResponseDTO(BaseModel):
    id: str
    filename: str
    content_type: str
    size: int
    download_url: Optional[str] = None
    appointment_name: Optional[str] = None
    
    # Virus scanning fields
    virus_scan_status: str = 'pending'
    is_quarantined: bool = False
    quarantine_reason: Optional[str] = None

    class Config:
        from_attributes = True

class RetryUploadFileDTO(BaseModel):
    id: str
    credential: Optional[Dict[str, Any]]

