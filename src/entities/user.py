from infrastructure.db.mysql import mysql as db
from sqlalchemy import Column, String, DateTime, VARCHAR
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime


class User(db.Base):
    __tablename__ = "users"
    id = Column(VARCHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    # Name is not required to be unique globally
    name = Column(String(255), nullable=False, index=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    appointments = relationship("Appointment", back_populates="user", cascade="all, delete-orphan")
    files = relationship("File", back_populates="user", cascade="all, delete-orphan")