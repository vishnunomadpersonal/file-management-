from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import List
from .file_dto import FileResponseDTO

class AppointmentBase(BaseModel):
    name: str

class AppointmentCreate(AppointmentBase):
    user_id: str

class Appointment(AppointmentBase):
    id: str
    date: datetime
    files: List[FileResponseDTO] = []
    
    model_config = ConfigDict(from_attributes=True) 