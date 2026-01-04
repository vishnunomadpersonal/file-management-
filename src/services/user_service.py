from repositories.user_repository import UserRepo
from services.base_service import BaseService
from dto.user_dto import UserCreate, User
from typing import List
from infrastructure.minio import minioStorage
import logging

# Redis Caching
try:
    from infrastructure.redis_cache import redis_cache
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis_cache = None

logger = logging.getLogger(__name__)

# Cache TTL
CACHE_TTL_USERS = 300  # 5 minutes


def _serialize_user(user) -> dict:
    """Serialize a User entity for caching."""
    if user is None:
        return None
    return {
        'id': str(user.id),
        'name': user.name,
        'email': getattr(user, 'email', None),
        'role': getattr(user, 'role', None),
        'status': getattr(user, 'status', None),
        'is_active': getattr(user, 'is_active', None),
        'is_verified': getattr(user, 'is_verified', None),
        'organization_id': str(user.organization_id) if getattr(user, 'organization_id', None) else None,
        'approved_by': str(user.approved_by) if getattr(user, 'approved_by', None) else None,
        'approved_at': user.approved_at.isoformat() if hasattr(user, 'approved_at') and user.approved_at else None,
        'created_at': user.created_at.isoformat() if hasattr(user, 'created_at') and user.created_at else None,
        'updated_at': user.updated_at.isoformat() if hasattr(user, 'updated_at') and user.updated_at else None,
    }


class UserService(BaseService[UserRepo]):
    def __init__(self, repo: UserRepo):
        super().__init__(repo)

    def _invalidate_user_caches(self, user_id: str = None):
        """Invalidate user-related caches."""
        if not REDIS_AVAILABLE or not redis_cache:
            return
        try:
            redis_cache.delete("users:all")
            if user_id:
                redis_cache.delete(f"user:{user_id}")
            logger.info(f"Invalidated user caches")
        except Exception as e:
            logger.warning(f"Failed to invalidate user caches: {e}")

    def create_user(self, user: UserCreate) -> User:
        result = self.repo.create_user(user.name)
        self._invalidate_user_caches()
        return result

    def list_users(self) -> List[User]:
        """List all users with Redis caching."""
        cache_key = "users:all"
        
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
        users = self.repo.list_users()
        
        # Store in cache
        if REDIS_AVAILABLE and redis_cache and users:
            try:
                cache_data = [_serialize_user(u) for u in users]
                redis_cache.set(cache_key, cache_data, ttl=CACHE_TTL_USERS)
            except Exception as e:
                logger.warning(f"Redis cache write failed: {e}")
        
        return users

    def get_user(self, user_id: str):
        """Get a single user with caching."""
        cache_key = f"user:{user_id}"
        
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
        user = self.repo.get(id=user_id)
        
        # Store in cache
        if REDIS_AVAILABLE and redis_cache and user:
            try:
                redis_cache.set(cache_key, _serialize_user(user), ttl=CACHE_TTL_USERS)
            except Exception as e:
                logger.warning(f"Redis cache write failed: {e}")
        
        return user

    def delete_user(self, user_id: str) -> User:
        # Invalidate caches first
        self._invalidate_user_caches(user_id)
        
        # First get the user to access its appointments and files
        user = self.repo.get(id=user_id)
        if not user:
            return None
            
        # Delete all files associated with this user from MinIO
        for appointment in user.appointments:
            for file in appointment.files:
                try:
                    # Delete from MinIO
                    bucket_name = file.path.split("/")[0]
                    object_name = "/".join(file.path.split("/")[1:])
                    minioStorage.remove_object(bucket_name, object_name)
                    logger.info(f"Deleted file from MinIO: {bucket_name}/{object_name}")
                except Exception as e:
                    logger.error(f"Failed to delete file from MinIO: {str(e)}")
                    # Continue with deletion even if MinIO deletion fails
        
        # Also invalidate file caches for this user
        if REDIS_AVAILABLE and redis_cache:
            try:
                redis_cache.delete(f"files:user:{user_id}")
            except Exception:
                pass
        
        # Delete the user (cascade will delete associated appointments and files from DB)
        return self.repo.delete_user(user_id)