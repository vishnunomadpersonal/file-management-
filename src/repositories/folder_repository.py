"""
Folder Repository - Database operations for folders.
"""

from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_
import logging

from repositories.base_repository import BaseRepo
from entities.folder import Folder

logger = logging.getLogger(__name__)


class FolderRepository(BaseRepo[Folder]):
    """Repository for folder database operations."""
    
    def __init__(self, db: Session):
        super().__init__(Folder, db)
    
    def get_by_id(self, folder_id: str) -> Optional[Folder]:
        """Get a folder by ID."""
        return self.db.query(Folder).filter(Folder.id == folder_id).first()
    
    def get_by_id_and_org(self, folder_id: str, organization_id: str) -> Optional[Folder]:
        """Get a folder by ID within a specific organization."""
        return self.db.query(Folder).filter(
            and_(
                Folder.id == folder_id,
                Folder.organization_id == organization_id
            )
        ).first()
    
    def list_by_organization(self, organization_id: str, parent_id: Optional[str] = None) -> List[Folder]:
        """
        List folders in an organization, optionally filtered by parent.
        
        Args:
            organization_id: Organization ID to filter by
            parent_id: Parent folder ID (None for root level folders)
        """
        query = self.db.query(Folder).filter(
            Folder.organization_id == organization_id
        )
        
        if parent_id is None:
            # Get root level folders (no parent)
            query = query.filter(Folder.parent_id.is_(None))
        else:
            # Get children of specific folder
            query = query.filter(Folder.parent_id == parent_id)
        
        return query.order_by(Folder.name).all()
    
    def list_all_by_organization(self, organization_id: str) -> List[Folder]:
        """List all folders in an organization (for tree view)."""
        return self.db.query(Folder).filter(
            Folder.organization_id == organization_id
        ).order_by(Folder.path).all()
    
    def get_by_path(self, organization_id: str, path: str) -> Optional[Folder]:
        """Get a folder by its full path within an organization."""
        return self.db.query(Folder).filter(
            and_(
                Folder.organization_id == organization_id,
                Folder.path == path
            )
        ).first()
    
    def get_children(self, folder_id: str) -> List[Folder]:
        """Get all direct children of a folder."""
        return self.db.query(Folder).filter(
            Folder.parent_id == folder_id
        ).order_by(Folder.name).all()
    
    def get_all_descendants(self, folder_id: str) -> List[Folder]:
        """Get all descendants (children, grandchildren, etc.) of a folder."""
        # Get the folder's path first
        folder = self.get_by_id(folder_id)
        if not folder:
            return []
        
        # Find all folders whose path starts with this folder's path
        return self.db.query(Folder).filter(
            and_(
                Folder.path.like(f"{folder.path}/%"),
                Folder.id != folder_id
            )
        ).all()
    
    def exists_with_name(self, organization_id: str, name: str, parent_id: Optional[str] = None, exclude_id: Optional[str] = None) -> bool:
        """Check if a folder with the given name already exists in the same location."""
        query = self.db.query(Folder).filter(
            and_(
                Folder.organization_id == organization_id,
                Folder.name == name
            )
        )
        
        if parent_id is None:
            query = query.filter(Folder.parent_id.is_(None))
        else:
            query = query.filter(Folder.parent_id == parent_id)
        
        if exclude_id:
            query = query.filter(Folder.id != exclude_id)
        
        return query.first() is not None
    
    def update(self, folder: Folder) -> Folder:
        """Update a folder."""
        self.db.commit()
        self.db.refresh(folder)
        return folder
    
    def delete(self, folder: Folder) -> None:
        """Delete a folder."""
        self.db.delete(folder)
        self.db.commit()
    
    def update_children_paths(self, old_path: str, new_path: str, organization_id: str) -> None:
        """Update paths for all descendants when a folder is moved/renamed."""
        descendants = self.db.query(Folder).filter(
            and_(
                Folder.organization_id == organization_id,
                Folder.path.like(f"{old_path}/%")
            )
        ).all()
        
        for desc in descendants:
            desc.path = desc.path.replace(old_path, new_path, 1)
        
        self.db.commit()
