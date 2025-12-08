"""
Folder API Routes - CRUD operations for folder management.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Optional
import logging

from infrastructure.db.mysql import mysql
from services.folder_service import FolderService
from dto.folder_dto import (
    FolderCreateDTO, 
    FolderUpdateDTO, 
    FolderMoveDTO,
    FolderResponseDTO,
    FolderWithContentsDTO
)
from core.security import get_current_user, AuthenticatedUser

logger = logging.getLogger(__name__)

folder_router = APIRouter(prefix="/folders", tags=["Folders"])


def get_folder_service(db: Session = Depends(mysql.get_db)) -> FolderService:
    """Folder service dependency."""
    return FolderService(db)


@folder_router.post("", response_model=FolderResponseDTO)
async def create_folder(
    dto: FolderCreateDTO,
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: FolderService = Depends(get_folder_service)
):
    """
    Create a new folder.
    
    - **name**: Folder name (required)
    - **parent_id**: Parent folder ID (optional, null for root level)
    """
    folder = service.create_folder(
        dto=dto,
        organization_id=current_user.organization_id,
        user_id=current_user.user_id
    )
    return FolderResponseDTO.model_validate(folder)


@folder_router.get("", response_model=List[FolderResponseDTO])
async def list_folders(
    parent_id: Optional[str] = Query(None, description="Parent folder ID (null for root)"),
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: FolderService = Depends(get_folder_service)
):
    """
    List folders in the current organization.
    
    - **parent_id**: Filter by parent folder (null for root level folders)
    """
    folders = service.list_folders(
        organization_id=current_user.organization_id,
        parent_id=parent_id
    )
    return [FolderResponseDTO.model_validate(f) for f in folders]


@folder_router.get("/tree", response_model=List[FolderResponseDTO])
async def get_folder_tree(
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: FolderService = Depends(get_folder_service)
):
    """
    Get all folders as a flat list (for building tree on frontend).
    """
    folders = service.get_folder_tree(current_user.organization_id)
    return [FolderResponseDTO.model_validate(f) for f in folders]


@folder_router.get("/contents", response_model=FolderWithContentsDTO)
async def get_folder_contents(
    folder_id: Optional[str] = Query(None, description="Folder ID (null for root)"),
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: FolderService = Depends(get_folder_service)
):
    """
    Get folder contents including subfolders and file count.
    
    - **folder_id**: Folder ID (null for root level)
    """
    return service.get_folder_contents(
        folder_id=folder_id,
        organization_id=current_user.organization_id
    )


@folder_router.get("/{folder_id}", response_model=FolderResponseDTO)
async def get_folder(
    folder_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: FolderService = Depends(get_folder_service)
):
    """
    Get a specific folder by ID.
    """
    folder = service.get_folder(folder_id, current_user.organization_id)
    return FolderResponseDTO.model_validate(folder)


@folder_router.patch("/{folder_id}", response_model=FolderResponseDTO)
async def update_folder(
    folder_id: str,
    dto: FolderUpdateDTO,
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: FolderService = Depends(get_folder_service)
):
    """
    Update a folder (rename).
    
    - **name**: New folder name
    """
    folder = service.update_folder(folder_id, dto, current_user.organization_id)
    return FolderResponseDTO.model_validate(folder)


@folder_router.post("/{folder_id}/move", response_model=FolderResponseDTO)
async def move_folder(
    folder_id: str,
    dto: FolderMoveDTO,
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: FolderService = Depends(get_folder_service)
):
    """
    Move a folder to a new parent.
    
    - **new_parent_id**: New parent folder ID (null to move to root)
    """
    folder = service.move_folder(folder_id, dto, current_user.organization_id)
    return FolderResponseDTO.model_validate(folder)


@folder_router.delete("/{folder_id}")
async def delete_folder(
    folder_id: str,
    force: bool = Query(False, description="Force delete even if folder has contents"),
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: FolderService = Depends(get_folder_service)
):
    """
    Delete a folder.
    
    - **force**: If true, delete even if folder contains files or subfolders
    """
    service.delete_folder(folder_id, current_user.organization_id, force)
    return {"message": "Folder deleted successfully"}
