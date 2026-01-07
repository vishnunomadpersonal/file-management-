"""
Infrastructure Module
=====================
Docker container monitoring, system metrics, and high-performance caching.
"""

from infrastructure.docker_monitor import docker_monitor, DockerMonitor

# FastCache: Two-level L1 (memory) + L2 (Redis) cache for <10ms response times
# Use this for new code that needs ultra-fast caching
try:
    from infrastructure.fast_cache import fast_cache, FastCache, get_fast_cache, cached_query
    FAST_CACHE_AVAILABLE = True
except ImportError:
    fast_cache = None
    FastCache = None
    get_fast_cache = lambda: None
    cached_query = None
    FAST_CACHE_AVAILABLE = False

__all__ = [
    'docker_monitor', 
    'DockerMonitor',
    'fast_cache',
    'FastCache', 
    'get_fast_cache',
    'cached_query',
    'FAST_CACHE_AVAILABLE'
]
