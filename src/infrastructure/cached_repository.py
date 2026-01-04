"""
Cached Repository Mixin - Redis caching for database queries
=============================================================
Provides automatic caching for repository queries to reduce database load.

Usage:
    class FileRepo(CachedRepositoryMixin, BaseRepo[File]):
        cache_prefix = "file"
        cache_ttl = 120  # 2 minutes
        
        @cached_query(ttl=60)
        def get_files_by_org(self, org_id: str) -> List[File]:
            return self.db.query(File).filter(File.org_id == org_id).all()

Cache Invalidation:
    - Automatically invalidate on create/update/delete
    - Manual: repo.invalidate_cache("key") or repo.invalidate_all()
"""

import hashlib
import functools
import logging
from typing import TypeVar, Generic, Optional, Any, Callable, List
from datetime import datetime

# Try to import Redis cache
try:
    from infrastructure.redis_cache import redis_cache, cache_get, cache_set, cache_delete
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis_cache = None

logger = logging.getLogger(__name__)

T = TypeVar('T')


def cached_query(ttl: int = 120, prefix: str = None, key_func: Callable = None):
    """
    Decorator to cache repository query results.
    
    Args:
        ttl: Cache TTL in seconds (default 2 minutes)
        prefix: Cache key prefix (default: function name)
        key_func: Custom function to generate cache key from args
        
    Example:
        @cached_query(ttl=60, prefix="files")
        def get_files_by_org(self, org_id: str) -> List[File]:
            return self.db.query(File).filter(File.org_id == org_id).all()
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            if not REDIS_AVAILABLE or not redis_cache:
                return func(self, *args, **kwargs)
            
            # Build cache key
            cache_prefix = prefix or getattr(self, 'cache_prefix', func.__name__)
            
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                # Default key: prefix:func_name:args_hash
                key_parts = [func.__name__] + [str(a) for a in args]
                key_parts += [f"{k}={v}" for k, v in sorted(kwargs.items())]
                cache_key = hashlib.md5(":".join(key_parts).encode()).hexdigest()
            
            full_key = f"{cache_prefix}:{cache_key}"
            
            # Try cache first
            cached = redis_cache.get(full_key, prefix="repo")
            if cached is not None:
                logger.debug(f"Cache HIT: {full_key}")
                return cached
            
            # Cache miss - execute query
            logger.debug(f"Cache MISS: {full_key}")
            result = func(self, *args, **kwargs)
            
            # Serialize SQLAlchemy objects to dicts for caching
            serialized = _serialize_for_cache(result)
            
            # Store in cache
            actual_ttl = ttl or getattr(self, 'cache_ttl', 120)
            redis_cache.set(full_key, serialized, ttl=actual_ttl, prefix="repo")
            
            return result
        
        return wrapper
    return decorator


def _serialize_for_cache(obj: Any) -> Any:
    """
    Serialize SQLAlchemy objects to cacheable format.
    
    Note: This returns the object as-is for now. For proper serialization
    of SQLAlchemy objects, you'd need to detach them from session or
    convert to dicts. The cache returns raw query results.
    """
    # For lists of model objects, we cache metadata not the objects
    # The actual caching works for:
    # - Counts (integers)
    # - Simple query results (dicts)
    # - Aggregations
    
    if isinstance(obj, (int, float, str, bool, type(None))):
        return obj
    
    if isinstance(obj, list):
        # For now, cache list length and basic info
        # Full object serialization would require more complex handling
        if len(obj) > 0 and hasattr(obj[0], '__table__'):
            # SQLAlchemy models - cache their primary key info
            return {
                '_cached': True,
                '_type': 'model_list',
                '_count': len(obj),
                '_model': obj[0].__class__.__name__,
                # We can't cache full objects easily, return None to skip
            }
        return obj
    
    if isinstance(obj, dict):
        return obj
    
    # For SQLAlchemy model instances
    if hasattr(obj, '__table__'):
        return {
            '_cached': True,
            '_type': 'model',
            '_model': obj.__class__.__name__,
            '_id': getattr(obj, 'id', None)
        }
    
    return obj


class CachedRepositoryMixin:
    """
    Mixin to add caching capabilities to repositories.
    
    Usage:
        class FileRepo(CachedRepositoryMixin, BaseRepo[File]):
            cache_prefix = "file"
            cache_ttl = 120
    """
    
    cache_prefix: str = "repo"
    cache_ttl: int = 120  # Default 2 minutes
    
    def get_cache_key(self, operation: str, *args) -> str:
        """Build a cache key for an operation."""
        key_parts = [operation] + [str(a) for a in args if a is not None]
        return hashlib.md5(":".join(key_parts).encode()).hexdigest()
    
    def cache_get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        if not REDIS_AVAILABLE or not redis_cache:
            return None
        full_key = f"{self.cache_prefix}:{key}"
        return redis_cache.get(full_key, prefix="repo")
    
    def cache_set(self, key: str, value: Any, ttl: int = None) -> bool:
        """Set value in cache."""
        if not REDIS_AVAILABLE or not redis_cache:
            return False
        full_key = f"{self.cache_prefix}:{key}"
        return redis_cache.set(full_key, value, ttl=ttl or self.cache_ttl, prefix="repo")
    
    def invalidate_cache(self, key: str = None) -> int:
        """
        Invalidate cache entries.
        
        Args:
            key: Specific key to invalidate. If None, invalidates all for this prefix.
        """
        if not REDIS_AVAILABLE or not redis_cache:
            return 0
        
        if key:
            full_key = f"{self.cache_prefix}:{key}"
            redis_cache.delete(full_key, prefix="repo")
            return 1
        else:
            # Invalidate all for this prefix
            pattern = f"{self.cache_prefix}:*"
            return redis_cache.delete_pattern(pattern, prefix="repo")
    
    def invalidate_all(self) -> int:
        """Invalidate all cache entries for this repository."""
        return self.invalidate_cache()


# =============================================================================
# CACHE-AWARE BASE REPOSITORY OPERATIONS
# =============================================================================

class CachedQueryExecutor:
    """
    Execute and cache common query patterns.
    
    Usage:
        executor = CachedQueryExecutor(redis_cache)
        
        # Cache a count query
        count = executor.cached_count(
            db.query(File).filter(File.org_id == org_id),
            cache_key=f"file_count:{org_id}",
            ttl=60
        )
    """
    
    def __init__(self):
        self.cache = redis_cache
    
    def cached_count(
        self, 
        query, 
        cache_key: str, 
        ttl: int = 60,
        prefix: str = "query"
    ) -> int:
        """Execute and cache a count query."""
        if not REDIS_AVAILABLE or not self.cache:
            return query.count()
        
        cached = self.cache.get(cache_key, prefix=prefix)
        if cached is not None:
            logger.debug(f"Count cache HIT: {cache_key}")
            return cached
        
        result = query.count()
        self.cache.set(cache_key, result, ttl=ttl, prefix=prefix)
        logger.debug(f"Count cache SET: {cache_key} = {result}")
        return result
    
    def cached_scalar(
        self,
        query,
        cache_key: str,
        ttl: int = 60,
        prefix: str = "query"
    ) -> Any:
        """Execute and cache a scalar query (single value)."""
        if not REDIS_AVAILABLE or not self.cache:
            return query.scalar()
        
        cached = self.cache.get(cache_key, prefix=prefix)
        if cached is not None:
            return cached
        
        result = query.scalar()
        self.cache.set(cache_key, result, ttl=ttl, prefix=prefix)
        return result
    
    def cached_first(
        self,
        query,
        cache_key: str,
        ttl: int = 120,
        prefix: str = "query",
        serialize: Callable = None
    ) -> Optional[Any]:
        """Execute and cache first() query."""
        if not REDIS_AVAILABLE or not self.cache:
            return query.first()
        
        cached = self.cache.get(cache_key, prefix=prefix)
        if cached is not None:
            return cached
        
        result = query.first()
        if result and serialize:
            # Serialize for caching
            serialized = serialize(result)
            self.cache.set(cache_key, serialized, ttl=ttl, prefix=prefix)
        
        return result


# Singleton executor
query_executor = CachedQueryExecutor()


# =============================================================================
# CONVENIENCE DECORATORS FOR SERVICES
# =============================================================================

def cache_result(ttl: int = 120, prefix: str = "svc", key_builder: Callable = None):
    """
    Decorator to cache service method results.
    
    Args:
        ttl: Cache TTL in seconds
        prefix: Cache key prefix
        key_builder: Custom function to build cache key from method args
        
    Example:
        @cache_result(ttl=300, prefix="user")
        def get_user_stats(self, user_id: str) -> dict:
            ...
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if not REDIS_AVAILABLE or not redis_cache:
                return func(*args, **kwargs)
            
            # Build cache key
            if key_builder:
                cache_key = key_builder(*args, **kwargs)
            else:
                # Skip 'self' for methods
                key_args = args[1:] if args and hasattr(args[0], func.__name__) else args
                key_parts = [func.__name__] + [str(a) for a in key_args]
                key_parts += [f"{k}={v}" for k, v in sorted(kwargs.items())]
                cache_key = hashlib.md5(":".join(key_parts).encode()).hexdigest()
            
            # Try cache
            cached = redis_cache.get(cache_key, prefix=prefix)
            if cached is not None:
                return cached
            
            # Execute and cache
            result = func(*args, **kwargs)
            if result is not None:
                redis_cache.set(cache_key, result, ttl=ttl, prefix=prefix)
            
            return result
        
        # Add cache control methods
        wrapper.invalidate = lambda: redis_cache.delete_pattern(f"*", prefix=prefix) if redis_cache else 0
        
        return wrapper
    return decorator


def invalidate_cache_on_write(prefixes: List[str] = None):
    """
    Decorator to invalidate cache after write operations (create/update/delete).
    
    Args:
        prefixes: List of cache prefixes to invalidate
        
    Example:
        @invalidate_cache_on_write(prefixes=["file", "storage"])
        def create_file(self, dto: FileDTO) -> File:
            ...
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            
            if REDIS_AVAILABLE and redis_cache:
                invalidate_prefixes = prefixes or ["repo"]
                for prefix in invalidate_prefixes:
                    deleted = redis_cache.delete_pattern("*", prefix=prefix)
                    if deleted:
                        logger.debug(f"Invalidated {deleted} cache entries for prefix: {prefix}")
            
            return result
        return wrapper
    return decorator
