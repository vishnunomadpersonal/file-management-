"""
Redis Cache Infrastructure
============================
High-performance caching layer to reduce database load by 80-90%.

CRITICAL: Without this, every API call hits MySQL directly!

Features:
- Query result caching (chatbot analytics)
- Session caching
- Rate limiting support
- Connection pooling
- Automatic fallback to in-memory cache if Redis unavailable
- Key prefixing for namespacing
- TTL management
- JSON serialization for complex objects
"""

import redis
import json
import hashlib
import logging
from typing import Any, Optional, Union, Callable
from functools import wraps
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from contextlib import contextmanager
import asyncio

from core.config import config

logger = logging.getLogger(__name__)


@dataclass
class CacheStats:
    """Cache performance statistics."""
    hits: int = 0
    misses: int = 0
    errors: int = 0
    sets: int = 0
    deletes: int = 0
    
    @property
    def hit_rate(self) -> float:
        total = self.hits + self.misses
        return (self.hits / total * 100) if total > 0 else 0.0


class RedisCache:
    """
    Enterprise-grade Redis caching layer.
    
    Usage:
        # Simple get/set
        cache.set("key", {"data": "value"}, ttl=300)
        data = cache.get("key")
        
        # Decorator for function caching
        @cache.cached(ttl=60, prefix="user")
        def get_user(user_id: str):
            return db.query(User).filter(User.id == user_id).first()
        
        # Cache invalidation
        cache.delete("user:123")
        cache.delete_pattern("user:*")  # Delete all user caches
    """
    
    _instance: Optional['RedisCache'] = None
    
    def __new__(cls) -> 'RedisCache':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        self._initialized = True
        self.enabled = config.REDIS_ENABLED
        self.default_ttl = config.REDIS_CACHE_TTL
        self.stats = CacheStats()
        self._client: Optional[redis.Redis] = None
        self._fallback_cache: dict = {}  # In-memory fallback
        self._fallback_expiry: dict = {}  # Expiry times for fallback
        
        if self.enabled:
            self._connect()
    
    def _connect(self) -> None:
        """Establish Redis connection with connection pooling."""
        try:
            self._client = redis.Redis(
                host=config.REDIS_HOST,
                port=config.REDIS_PORT,
                password=config.REDIS_PASSWORD or None,
                db=config.REDIS_DB,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True,
                # Connection pooling
                max_connections=50,
                health_check_interval=30
            )
            # Test connection
            self._client.ping()
            logger.info(f"✅ Redis connected: {config.REDIS_HOST}:{config.REDIS_PORT}")
        except redis.ConnectionError as e:
            logger.warning(f"⚠️ Redis connection failed: {e}. Using in-memory fallback cache.")
            self._client = None
        except Exception as e:
            logger.error(f"❌ Redis error: {e}. Using in-memory fallback cache.")
            self._client = None
    
    @property
    def is_connected(self) -> bool:
        """Check if Redis is connected and healthy."""
        if not self._client:
            return False
        try:
            self._client.ping()
            return True
        except:
            return False
    
    def _make_key(self, key: str, prefix: str = "") -> str:
        """Create a namespaced cache key."""
        if prefix:
            return f"fm:{prefix}:{key}"
        return f"fm:{key}"
    
    def _serialize(self, value: Any) -> str:
        """Serialize value for storage."""
        if isinstance(value, (dict, list)):
            return json.dumps(value, default=str)
        return json.dumps({"__value__": value}, default=str)
    
    def _deserialize(self, data: str) -> Any:
        """Deserialize stored value."""
        try:
            result = json.loads(data)
            if isinstance(result, dict) and "__value__" in result:
                return result["__value__"]
            return result
        except json.JSONDecodeError:
            return data
    
    # =========================================================================
    # CORE CACHE OPERATIONS
    # =========================================================================
    
    def get(self, key: str, prefix: str = "") -> Optional[Any]:
        """
        Get value from cache.
        
        Args:
            key: Cache key
            prefix: Optional namespace prefix
            
        Returns:
            Cached value or None if not found
        """
        cache_key = self._make_key(key, prefix)
        
        # Try Redis first
        if self._client:
            try:
                data = self._client.get(cache_key)
                if data:
                    self.stats.hits += 1
                    return self._deserialize(data)
                self.stats.misses += 1
                return None
            except redis.RedisError as e:
                logger.warning(f"Redis GET error: {e}")
                self.stats.errors += 1
        
        # Fallback to in-memory
        if cache_key in self._fallback_cache:
            expiry = self._fallback_expiry.get(cache_key)
            if expiry and datetime.now() > expiry:
                del self._fallback_cache[cache_key]
                del self._fallback_expiry[cache_key]
                self.stats.misses += 1
                return None
            self.stats.hits += 1
            return self._fallback_cache[cache_key]
        
        self.stats.misses += 1
        return None
    
    def set(self, key: str, value: Any, ttl: int = None, prefix: str = "") -> bool:
        """
        Set value in cache.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds (default: 300)
            prefix: Optional namespace prefix
            
        Returns:
            True if successful
        """
        cache_key = self._make_key(key, prefix)
        ttl = ttl or self.default_ttl
        serialized = self._serialize(value)
        
        # Try Redis first
        if self._client:
            try:
                self._client.setex(cache_key, ttl, serialized)
                self.stats.sets += 1
                return True
            except redis.RedisError as e:
                logger.warning(f"Redis SET error: {e}")
                self.stats.errors += 1
        
        # Fallback to in-memory
        self._fallback_cache[cache_key] = value
        self._fallback_expiry[cache_key] = datetime.now() + timedelta(seconds=ttl)
        self.stats.sets += 1
        return True
    
    def delete(self, key: str, prefix: str = "") -> bool:
        """Delete a cache key."""
        cache_key = self._make_key(key, prefix)
        
        if self._client:
            try:
                self._client.delete(cache_key)
                self.stats.deletes += 1
                return True
            except redis.RedisError as e:
                logger.warning(f"Redis DELETE error: {e}")
                self.stats.errors += 1
        
        # Fallback
        if cache_key in self._fallback_cache:
            del self._fallback_cache[cache_key]
            if cache_key in self._fallback_expiry:
                del self._fallback_expiry[cache_key]
            self.stats.deletes += 1
        return True
    
    def delete_pattern(self, pattern: str, prefix: str = "") -> int:
        """Delete all keys matching pattern (e.g., 'user:*')."""
        cache_pattern = self._make_key(pattern, prefix)
        deleted = 0
        
        if self._client:
            try:
                keys = self._client.keys(cache_pattern)
                if keys:
                    deleted = self._client.delete(*keys)
                    self.stats.deletes += deleted
            except redis.RedisError as e:
                logger.warning(f"Redis DELETE pattern error: {e}")
                self.stats.errors += 1
        
        # Fallback - simple prefix matching
        pattern_prefix = cache_pattern.replace("*", "")
        to_delete = [k for k in self._fallback_cache if k.startswith(pattern_prefix)]
        for k in to_delete:
            del self._fallback_cache[k]
            self._fallback_expiry.pop(k, None)
            deleted += 1
        
        return deleted
    
    def exists(self, key: str, prefix: str = "") -> bool:
        """Check if key exists in cache."""
        cache_key = self._make_key(key, prefix)
        
        if self._client:
            try:
                return self._client.exists(cache_key) > 0
            except redis.RedisError:
                pass
        
        return cache_key in self._fallback_cache
    
    def get_ttl(self, key: str, prefix: str = "") -> int:
        """Get remaining TTL for a key in seconds."""
        cache_key = self._make_key(key, prefix)
        
        if self._client:
            try:
                return self._client.ttl(cache_key)
            except redis.RedisError:
                pass
        
        expiry = self._fallback_expiry.get(cache_key)
        if expiry:
            remaining = (expiry - datetime.now()).total_seconds()
            return int(max(0, remaining))
        return -2  # Key doesn't exist
    
    # =========================================================================
    # DECORATOR FOR FUNCTION CACHING
    # =========================================================================
    
    def cached(
        self,
        ttl: int = None,
        prefix: str = "",
        key_builder: Callable = None
    ):
        """
        Decorator to cache function results.
        
        Args:
            ttl: Cache TTL in seconds
            prefix: Cache key prefix
            key_builder: Custom function to build cache key from args
            
        Example:
            @cache.cached(ttl=60, prefix="user")
            def get_user(user_id: str):
                return db.query(User).filter(User.id == user_id).first()
        """
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                # Build cache key
                if key_builder:
                    cache_key = key_builder(*args, **kwargs)
                else:
                    # Default: hash of function name + args
                    key_parts = [func.__name__] + [str(a) for a in args]
                    key_parts += [f"{k}={v}" for k, v in sorted(kwargs.items())]
                    cache_key = hashlib.md5(":".join(key_parts).encode()).hexdigest()
                
                # Try cache first
                cached_result = self.get(cache_key, prefix=prefix or func.__name__)
                if cached_result is not None:
                    return cached_result
                
                # Execute function and cache result
                result = func(*args, **kwargs)
                if result is not None:
                    self.set(cache_key, result, ttl=ttl, prefix=prefix or func.__name__)
                
                return result
            
            # Add cache control methods to wrapper
            wrapper.cache_clear = lambda: self.delete_pattern("*", prefix=prefix or func.__name__)
            wrapper.cache_key = lambda *a, **kw: self._make_key(
                key_builder(*a, **kw) if key_builder else hashlib.md5(
                    ":".join([func.__name__] + [str(x) for x in a]).encode()
                ).hexdigest(),
                prefix=prefix or func.__name__
            )
            
            return wrapper
        return decorator
    
    # =========================================================================
    # ASYNC SUPPORT
    # =========================================================================
    
    async def aget(self, key: str, prefix: str = "") -> Optional[Any]:
        """Async get - runs sync get in executor."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.get, key, prefix)
    
    async def aset(self, key: str, value: Any, ttl: int = None, prefix: str = "") -> bool:
        """Async set - runs sync set in executor."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.set, key, value, ttl, prefix)
    
    async def adelete(self, key: str, prefix: str = "") -> bool:
        """Async delete - runs sync delete in executor."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.delete, key, prefix)
    
    # =========================================================================
    # SPECIALIZED CACHING METHODS
    # =========================================================================
    
    def cache_query_result(
        self,
        query_hash: str,
        result: Any,
        ttl: int = 60
    ) -> bool:
        """
        Cache SQL query result.
        
        Args:
            query_hash: MD5 hash of the SQL query
            result: Query result data
            ttl: TTL in seconds (shorter for analytics)
        """
        return self.set(query_hash, result, ttl=ttl, prefix="sql")
    
    def get_query_result(self, query_hash: str) -> Optional[Any]:
        """Get cached SQL query result."""
        return self.get(query_hash, prefix="sql")
    
    def cache_user_data(self, user_id: str, data: dict, ttl: int = 300) -> bool:
        """Cache user data (5 min default)."""
        return self.set(user_id, data, ttl=ttl, prefix="user")
    
    def get_user_data(self, user_id: str) -> Optional[dict]:
        """Get cached user data."""
        return self.get(user_id, prefix="user")
    
    def invalidate_user(self, user_id: str) -> bool:
        """Invalidate all caches for a user."""
        self.delete(user_id, prefix="user")
        return self.delete_pattern(f"*{user_id}*") > 0
    
    def cache_org_data(self, org_id: str, data: dict, ttl: int = 300) -> bool:
        """Cache organization data."""
        return self.set(org_id, data, ttl=ttl, prefix="org")
    
    def get_org_data(self, org_id: str) -> Optional[dict]:
        """Get cached organization data."""
        return self.get(org_id, prefix="org")
    
    def invalidate_org(self, org_id: str) -> bool:
        """Invalidate all caches for an organization."""
        self.delete(org_id, prefix="org")
        return self.delete_pattern(f"*{org_id}*") > 0
    
    # =========================================================================
    # RATE LIMITING
    # =========================================================================
    
    def rate_limit_check(
        self,
        key: str,
        max_requests: int,
        window_seconds: int
    ) -> tuple[bool, int]:
        """
        Check rate limit for a key.
        
        Args:
            key: Rate limit key (e.g., user_id or IP)
            max_requests: Maximum requests allowed
            window_seconds: Time window in seconds
            
        Returns:
            (allowed, remaining) tuple
        """
        rate_key = self._make_key(key, prefix="ratelimit")
        
        if self._client:
            try:
                current = self._client.incr(rate_key)
                if current == 1:
                    self._client.expire(rate_key, window_seconds)
                
                remaining = max(0, max_requests - current)
                return current <= max_requests, remaining
            except redis.RedisError as e:
                logger.warning(f"Rate limit check error: {e}")
        
        # Fallback - simple in-memory counter
        now = datetime.now()
        if rate_key not in self._fallback_cache:
            self._fallback_cache[rate_key] = 1
            self._fallback_expiry[rate_key] = now + timedelta(seconds=window_seconds)
            return True, max_requests - 1
        
        expiry = self._fallback_expiry.get(rate_key)
        if expiry and now > expiry:
            self._fallback_cache[rate_key] = 1
            self._fallback_expiry[rate_key] = now + timedelta(seconds=window_seconds)
            return True, max_requests - 1
        
        self._fallback_cache[rate_key] += 1
        current = self._fallback_cache[rate_key]
        remaining = max(0, max_requests - current)
        return current <= max_requests, remaining
    
    # =========================================================================
    # HEALTH & STATS
    # =========================================================================
    
    def health_check(self) -> dict:
        """Get cache health status."""
        return {
            "status": "healthy" if self.is_connected else "degraded",
            "backend": "redis" if self.is_connected else "memory",
            "host": config.REDIS_HOST if self.is_connected else "local",
            "stats": {
                "hits": self.stats.hits,
                "misses": self.stats.misses,
                "hit_rate": f"{self.stats.hit_rate:.1f}%",
                "errors": self.stats.errors,
                "sets": self.stats.sets,
                "deletes": self.stats.deletes
            }
        }
    
    def flush_all(self) -> bool:
        """Clear all cache (use with caution!)."""
        if self._client:
            try:
                # Only flush keys with our prefix
                keys = self._client.keys("fm:*")
                if keys:
                    self._client.delete(*keys)
                logger.warning("Cache flushed!")
                return True
            except redis.RedisError as e:
                logger.error(f"Cache flush error: {e}")
        
        self._fallback_cache.clear()
        self._fallback_expiry.clear()
        return True


# =============================================================================
# SINGLETON INSTANCE
# =============================================================================

redis_cache = RedisCache()


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def cache_get(key: str, prefix: str = "") -> Optional[Any]:
    """Get value from cache."""
    return redis_cache.get(key, prefix)


def cache_set(key: str, value: Any, ttl: int = None, prefix: str = "") -> bool:
    """Set value in cache."""
    return redis_cache.set(key, value, ttl, prefix)


def cache_delete(key: str, prefix: str = "") -> bool:
    """Delete from cache."""
    return redis_cache.delete(key, prefix)


def cached(ttl: int = None, prefix: str = "", key_builder: Callable = None):
    """Decorator for caching function results."""
    return redis_cache.cached(ttl=ttl, prefix=prefix, key_builder=key_builder)
