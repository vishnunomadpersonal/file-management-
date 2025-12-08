"""
Folder DTOs for request/response handling.
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class FolderCreateDTO(BaseModel):
    """DTO for creating a new folder."""
    name: str = Field(..., min_length=1, max_length=255, description="Folder name")
    parent_id: Optional[str] = Field(None, description="Parent folder ID (null for root)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "Documents",
                "parent_id": None
            }
        }


class FolderUpdateDTO(BaseModel):
    """DTO for updating a folder."""
    name: Optional[str] = Field(None, min_length=1, max_length=255, description="New folder name")
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "My Documents"
            }
        }


class FolderMoveDTO(BaseModel):
    """DTO for moving a folder to a new parent."""
    new_parent_id: Optional[str] = Field(None, description="New parent folder ID (null for root)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "new_parent_id": "uuid-of-parent-folder"
            }
        }


class FolderResponseDTO(BaseModel):
    """DTO for folder response."""
    id: str
    name: str
    parent_id: Optional[str] = None
    organization_id: Optional[str] = None
    created_by: Optional[str] = None
    path: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "name": "Documents",
                "parent_id": None,
                "organization_id": "org-uuid",
                "created_by": "user-uuid",
                "path": "/Documents",
                "created_at": "2024-01-15T10:30:00",
                "updated_at": "2024-01-15T10:30:00"
            }
        }


class FolderWithContentsDTO(BaseModel):
    """DTO for folder response with child folders and file count."""
    id: str
    name: str
    parent_id: Optional[str] = None
    organization_id: Optional[str] = None
    created_by: Optional[str] = None
    path: str
    created_at: datetime
    updated_at: datetime
    child_folders: List["FolderResponseDTO"] = []
    file_count: int = 0
    
    class Config:
        from_attributes = True


class FolderTreeNodeDTO(BaseModel):
    """DTO for folder tree structure."""
    id: str
    name: str
    path: str
    children: List["FolderTreeNodeDTO"] = []
    file_count: int = 0
    
    class Config:
        from_attributes = True


# Update forward references
FolderWithContentsDTO.model_rebuild()
FolderTreeNodeDTO.model_rebuild()
