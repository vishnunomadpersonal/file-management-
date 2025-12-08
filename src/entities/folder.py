from infrastructure.db.mysql import mysql as db
from sqlalchemy import Column, String, VARCHAR, ForeignKey, DateTime, func
from sqlalchemy.orm import relationship
import uuid


class Folder(db.Base):
    __tablename__ = "folders"
    
    id = Column(VARCHAR(36), nullable=False, primary_key=True, unique=True,
                index=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    # Parent folder for nested structure (NULL = root level)
    parent_id = Column(VARCHAR(36), ForeignKey("folders.id", ondelete="CASCADE"), nullable=True)
    # Organization that owns this folder (NULL for super_admin folders)
    organization_id = Column(VARCHAR(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True)
    # User who created the folder
    created_by = Column(VARCHAR(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    # Full path for easy querying (e.g., "/documents/reports/2024")
    path = Column(String(500), nullable=False, index=True)
    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    parent = relationship("Folder", remote_side=[id], backref="children")
    organization = relationship("Organization", back_populates="folders")
    creator = relationship("User", back_populates="folders")
    files = relationship("File", back_populates="folder")
