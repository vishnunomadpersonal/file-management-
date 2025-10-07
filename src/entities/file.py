from infrastructure.db.mysql import mysql as db
from sqlalchemy import Column, String, JSON, Integer, VARCHAR, ForeignKey, Boolean, DateTime
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime


class File(db.Base):
    __tablename__ = "files"
    id = Column(VARCHAR(36), nullable=False, primary_key=True, unique=True,
                index=True, default=lambda: str(uuid.uuid4()))
    upload_id = Column(String(36), nullable=False, unique=True, index=True)
    filename = Column(String(255), nullable=False)
    appointment_id = Column(VARCHAR(36), ForeignKey("appointments.id"), nullable=False)
    user_id = Column(VARCHAR(36), ForeignKey("users.id"), nullable=False)
    credential = Column(JSON(none_as_null=True))
    # Path must be globally unique per stored object
    path = Column(VARCHAR(255), nullable=False, unique=True, index=True)
    content_type = Column(String(32), nullable=False)
    size = Column(Integer)
    detail = Column(JSON(none_as_null=True))
    # Reference Celery task by its unique task_id
    celery_task_id = Column(String(255))
    
    # Virus scanning fields
    virus_scan_status = Column(String(20), default='pending')  # 'pending', 'clean', 'infected', 'error', 'disabled'
    virus_scan_result = Column(JSON(none_as_null=True))        # Full scan results
    virus_scan_date = Column(DateTime)                         # When scan was performed
    is_quarantined = Column(Boolean, default=False)           # If file is quarantined
    quarantine_reason = Column(String(500))                   # Why file was quarantined

    # Relationships
    appointment = relationship("Appointment", back_populates="files")
    user = relationship("User", back_populates="files")
    # Relationship to CeleryTask is optional and no longer enforced via FK