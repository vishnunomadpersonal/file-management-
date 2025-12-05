from infrastructure.db.mysql import mysql as db
from sqlalchemy import Column, String, DateTime, VARCHAR, ForeignKey
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime


class Appointment(db.Base):
    __tablename__ = "appointments"
    id = Column(VARCHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    # Appointment name is not unique
    name = Column(String(255), nullable=False, index=True)
    date = Column(DateTime, nullable=False, default=datetime.utcnow)
    user_id = Column(VARCHAR(36), ForeignKey("users.id"), nullable=False)

    # Relationships
    files = relationship("File", back_populates="appointment", lazy="joined", cascade="all, delete-orphan")
    user = relationship("User", back_populates="appointments") 