from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime

class QuarantinedFileResponse(BaseModel):
    id: str
    filename: str
    virus_name: Optional[str]
    quarantine_reason: str
    upload_date: datetime
    scan_date: Optional[datetime]
    file_size: int
    appointment_name: Optional[str]
    user_name: Optional[str]
    scan_result: Optional[Dict[str, Any]]

    class Config:
        from_attributes = True

class VirusScanHealthResponse(BaseModel):
    status: str  # 'healthy', 'unhealthy', 'disabled'
    message: str
    scanner: str = 'ClamAV'
    enabled: bool