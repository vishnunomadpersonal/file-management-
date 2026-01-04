"""
Folder Service - Business logic for folder management.
"""

from typing import List, Optional
from sqlalchemy.orm import Session
import logging
import re

from entities.folder import Folder
from repositories.folder_repository import FolderRepository
from dto.folder_dto import FolderCreateDTO, FolderUpdateDTO, FolderMoveDTO, FolderResponseDTO, FolderWithContentsDTO
from fastapi import HTTPException
from infrastructure.minio import MinioStorage

# Redis Caching
try:
    from infrastructure.redis_cache import redis_cache
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis_cache = None

logger = logging.getLogger(__name__)

# Cache TTL
CACHE_TTL_FOLDERS = 300  # 5 minutes


def _serialize_folder(folder: Folder) -> dict:
    """Serialize a Folder entity for caching."""
    if folder is None:
        return None
    return {
        'id': str(folder.id),
        'name': folder.name,
        'path': folder.path,
        'parent_id': str(folder.parent_id) if folder.parent_id else None,
        'organization_id': str(folder.organization_id) if folder.organization_id else None,
        'created_by': str(folder.created_by) if folder.created_by else None,
        'created_at': folder.created_at.isoformat() if hasattr(folder, 'created_at') and folder.created_at else None,
        'updated_at': folder.updated_at.isoformat() if hasattr(folder, 'updated_at') and folder.updated_at else None,
    }


class FolderService:
    """Service for folder operations."""
    
    def __init__(self, db: Session):
        self.db = db
        self.repository = FolderRepository(db)
        self.minio = MinioStorage()
    
    def _invalidate_folder_caches(self, organization_id: str = None, folder_id: str = None):
        """Invalidate folder-related caches."""
        if not REDIS_AVAILABLE or not redis_cache:
            return
        try:
            if organization_id:
                redis_cache.delete_pattern(f"folders:org:{organization_id}:*")
            if folder_id:
                redis_cache.delete(f"folder:{folder_id}")
            logger.debug(f"Invalidated folder caches")
        except Exception as e:
            logger.warning(f"Failed to invalidate folder caches: {e}")
    
    def _sanitize_folder_name(self, name: str) -> str:
        """Sanitize folder name for use in paths."""
        # Remove or replace invalid characters
        sanitized = re.sub(r'[<>:"/\\|?*]', '_', name)
        sanitized = sanitized.strip()
        if not sanitized:
            raise HTTPException(status_code=400, detail="Invalid folder name")
        return sanitized
    
    def _build_path(self, name: str, parent: Optional[Folder]) -> str:
        """Build the full path for a folder."""
        sanitized_name = self._sanitize_folder_name(name)
        if parent:
            return f"{parent.path}/{sanitized_name}"
        return f"/{sanitized_name}"
    
    def _ensure_org_bucket(self, organization_id: Optional[str]) -> Optional[str]:
        """Ensure organization bucket exists in MinIO and return bucket name."""
        if not organization_id:
            # For users without organization (e.g., super_admin), use default bucket
            bucket_name = "default-files"
        else:
            bucket_name = f"org-{organization_id.lower()}"
        
        if not self.minio.bucket_exists(bucket_name):
            logger.info(f"Creating bucket: {bucket_name}")
            self.minio.create_bucket(bucket_name)
        
        return bucket_name
    
    def create_folder(
        self, 
        dto: FolderCreateDTO, 
        organization_id: str, 
        user_id: str
    ) -> Folder:
        """
        Create a new folder.
        
        Args:
            dto: Folder creation data
            organization_id: Organization this folder belongs to
            user_id: User creating the folder
            
        Returns:
            Created folder
        """
        # Validate parent folder if specified
        parent = None
        if dto.parent_id:
            parent = self.repository.get_by_id_and_org(dto.parent_id, organization_id)
            if not parent:
                raise HTTPException(status_code=404, detail="Parent folder not found")
        
        # Check for duplicate name in same location
        if self.repository.exists_with_name(organization_id, dto.name, dto.parent_id):
            raise HTTPException(
                status_code=409, 
                detail=f"A folder named '{dto.name}' already exists in this location"
            )
        
        # Build path
        path = self._build_path(dto.name, parent)
        
        # Ensure organization bucket exists
        self._ensure_org_bucket(organization_id)
        
        # Create folder entity
        folder = Folder(
            name=dto.name,
            parent_id=dto.parent_id,
            organization_id=organization_id,
            created_by=user_id,
            path=path
        )
        
        created_folder = self.repository.create(folder)
        logger.info(f"Created folder: {created_folder.id} at path: {path}")
        
        # Invalidate folder caches
        self._invalidate_folder_caches(organization_id=organization_id)
        
        return created_folder
    
    def get_folder(self, folder_id: str, organization_id: str) -> Folder:
        """Get a folder by ID with caching."""
        cache_key = f"folder:{folder_id}"
        
        # Try cache first
        if REDIS_AVAILABLE and redis_cache:
            try:
                cached = redis_cache.get(cache_key)
                if cached:
                    logger.debug(f"Cache HIT: {cache_key}")
                    return cached
            except Exception as e:
                logger.warning(f"Redis cache read failed: {e}")
        
        # Cache miss
        logger.debug(f"Cache MISS: {cache_key}")
        folder = self.repository.get_by_id_and_org(folder_id, organization_id)
        if not folder:
            raise HTTPException(status_code=404, detail="Folder not found")
        
        # Store in cache
        if REDIS_AVAILABLE and redis_cache:
            try:
                redis_cache.set(cache_key, _serialize_folder(folder), ttl=CACHE_TTL_FOLDERS)
            except Exception as e:
                logger.warning(f"Redis cache write failed: {e}")
        
        return folder
    
    def list_folders(
        self, 
        organization_id: str, 
        parent_id: Optional[str] = None
    ) -> List[Folder]:
        """
        List folders in an organization with caching.
        
        Args:
            organization_id: Organization to list folders for
            parent_id: Parent folder ID (None for root level)
            
        Returns:
            List of folders
        """
        cache_key = f"folders:org:{organization_id}:parent:{parent_id or 'root'}"
        
        # Try cache first
        if REDIS_AVAILABLE and redis_cache:
            try:
                cached = redis_cache.get(cache_key)
                if cached:
                    logger.debug(f"Cache HIT: {cache_key}")
                    return cached
            except Exception as e:
                logger.warning(f"Redis cache read failed: {e}")
        
        # Cache miss
        logger.debug(f"Cache MISS: {cache_key}")
        
        # Ensure org bucket exists
        self._ensure_org_bucket(organization_id)
        
        folders = self.repository.list_by_organization(organization_id, parent_id)
        
        # Store in cache
        if REDIS_AVAILABLE and redis_cache:
            try:
                cache_data = [_serialize_folder(f) for f in folders]
                redis_cache.set(cache_key, cache_data, ttl=CACHE_TTL_FOLDERS)
            except Exception as e:
                logger.warning(f"Redis cache write failed: {e}")
        
        return folders
    
    def get_folder_tree(self, organization_id: str) -> List[Folder]:
        """Get all folders as a flat list with caching."""
        cache_key = f"folders:org:{organization_id}:tree"
        
        # Try cache first
        if REDIS_AVAILABLE and redis_cache:
            try:
                cached = redis_cache.get(cache_key)
                if cached:
                    logger.debug(f"Cache HIT: {cache_key}")
                    return cached
            except Exception as e:
                logger.warning(f"Redis cache read failed: {e}")
        
        # Cache miss
        logger.debug(f"Cache MISS: {cache_key}")
        folders = self.repository.list_all_by_organization(organization_id)
        
        # Store in cache
        if REDIS_AVAILABLE and redis_cache:
            try:
                cache_data = [_serialize_folder(f) for f in folders]
                redis_cache.set(cache_key, cache_data, ttl=CACHE_TTL_FOLDERS)
            except Exception as e:
                logger.warning(f"Redis cache write failed: {e}")
        
        return folders
    
    def update_folder(
        self, 
        folder_id: str, 
        dto: FolderUpdateDTO, 
        organization_id: str
    ) -> Folder:
        """
        Update a folder (rename).
        
        Args:
            folder_id: Folder to update
            dto: Update data
            organization_id: Organization the folder belongs to
            
        Returns:
            Updated folder
        """
        folder = self.repository.get_by_id_and_org(folder_id, organization_id)
        if not folder:
            raise HTTPException(status_code=404, detail="Folder not found")
        
        if dto.name:
            # Check for duplicate name
            if self.repository.exists_with_name(
                organization_id, dto.name, folder.parent_id, exclude_id=folder_id
            ):
                raise HTTPException(
                    status_code=409, 
                    detail=f"A folder named '{dto.name}' already exists in this location"
                )
            
            # Update path for this folder and all descendants
            old_path = folder.path
            parent = self.repository.get_by_id(folder.parent_id) if folder.parent_id else None
            new_path = self._build_path(dto.name, parent)
            
            folder.name = dto.name
            folder.path = new_path
            
            # Update paths for all descendants
            self.repository.update_children_paths(old_path, new_path, organization_id)
        
        updated = self.repository.update(folder)
        
        # Invalidate caches after update
        self._invalidate_folder_caches(organization_id=organization_id, folder_id=folder_id)
        
        return updated
    
    def move_folder(
        self, 
        folder_id: str, 
        dto: FolderMoveDTO, 
        organization_id: str
    ) -> Folder:
        """
        Move a folder to a new parent.
        
        Args:
            folder_id: Folder to move
            dto: Move data with new parent ID
            organization_id: Organization the folder belongs to
            
        Returns:
            Moved folder
        """
        folder = self.repository.get_by_id_and_org(folder_id, organization_id)
        if not folder:
            raise HTTPException(status_code=404, detail="Folder not found")
        
        # Validate new parent
        new_parent = None
        if dto.new_parent_id:
            new_parent = self.repository.get_by_id_and_org(dto.new_parent_id, organization_id)
            if not new_parent:
                raise HTTPException(status_code=404, detail="Target folder not found")
            
            # Prevent moving folder into itself or its descendants
            if dto.new_parent_id == folder_id:
                raise HTTPException(status_code=400, detail="Cannot move folder into itself")
            
            descendants = self.repository.get_all_descendants(folder_id)
            descendant_ids = [d.id for d in descendants]
            if dto.new_parent_id in descendant_ids:
                raise HTTPException(status_code=400, detail="Cannot move folder into its own descendant")
        
        # Check for name conflict in new location
        if self.repository.exists_with_name(
            organization_id, folder.name, dto.new_parent_id, exclude_id=folder_id
        ):
            raise HTTPException(
                status_code=409, 
                detail=f"A folder named '{folder.name}' already exists in the target location"
            )
        
        # Update paths
        old_path = folder.path
        new_path = self._build_path(folder.name, new_parent)
        
        folder.parent_id = dto.new_parent_id
        folder.path = new_path
        
        # Update descendant paths
        self.repository.update_children_paths(old_path, new_path, organization_id)
        
        moved = self.repository.update(folder)
        
        # Invalidate caches after move
        self._invalidate_folder_caches(organization_id=organization_id, folder_id=folder_id)
        
        return moved
    
    def delete_folder(
        self, 
        folder_id: str, 
        organization_id: str,
        force: bool = False
    ) -> None:
        """
        Delete a folder.
        
        Args:
            folder_id: Folder to delete
            organization_id: Organization the folder belongs to
            force: If True, delete even if folder has contents (files/subfolders)
        """
        folder = self.repository.get_by_id_and_org(folder_id, organization_id)
        if not folder:
            raise HTTPException(status_code=404, detail="Folder not found")
        
        # Check for child folders
        children = self.repository.get_children(folder_id)
        if children and not force:
            raise HTTPException(
                status_code=400, 
                detail="Cannot delete folder with subfolders. Use force=true to delete recursively."
            )
        
        # Check for files in folder (simple check via relationship)
        if folder.files and not force:
            raise HTTPException(
                status_code=400, 
                detail="Cannot delete folder with files. Use force=true to delete recursively."
            )
        
        if force:
            # Delete all descendant folders
            descendants = self.repository.get_all_descendants(folder_id)
            for desc in descendants:
                self.repository.delete(desc)
            
            # Note: Files should be handled separately (moved or deleted)
            # For now, we don't delete files - they should be moved first
        
        self.repository.delete(folder)
        logger.info(f"Deleted folder: {folder_id}")
        
        # Invalidate caches after delete
        self._invalidate_folder_caches(organization_id=organization_id, folder_id=folder_id)
    
    def get_folder_contents(
        self, 
        folder_id: Optional[str], 
        organization_id: str
    ) -> FolderWithContentsDTO:
        """
        Get folder contents (subfolders and file count).
        
        Args:
            folder_id: Folder ID (None for root)
            organization_id: Organization ID
            
        Returns:
            Folder with contents info
        """
        folder = None
        if folder_id:
            folder = self.repository.get_by_id_and_org(folder_id, organization_id)
            if not folder:
                raise HTTPException(status_code=404, detail="Folder not found")
        
        # Get child folders
        child_folders = self.repository.list_by_organization(organization_id, folder_id)
        
        # Get file count from folder relationship
        file_count = len(folder.files) if folder and folder.files else 0
        
        if folder_id and folder:
            return FolderWithContentsDTO(
                id=folder.id,
                name=folder.name,
                parent_id=folder.parent_id,
                organization_id=folder.organization_id,
                created_by=folder.created_by,
                path=folder.path,
                created_at=folder.created_at,
                updated_at=folder.updated_at,
                child_folders=[FolderResponseDTO.model_validate(f) for f in child_folders],
                file_count=file_count
            )
        
        # Root level - return a virtual "root" folder
        from datetime import datetime
        return FolderWithContentsDTO(
            id="root",
            name="Root",
            parent_id=None,
            organization_id=organization_id,
            created_by="",
            path="/",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            child_folders=[FolderResponseDTO.model_validate(f) for f in child_folders],
            file_count=0
        )
