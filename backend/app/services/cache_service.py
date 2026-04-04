"""
Cache Service for GCP Quick Actions
====================================
Provides Redis-backed caching with in-memory fallback for the 4 quick actions:
1. List running VMs
2. Show VPC networks
3. Storage buckets
4. Billing summary

Redis is preferred for production (shared across instances).
Falls back to TTLCache (in-memory) if Redis is unavailable.
"""

import os
import json
import logging
from typing import Optional, Any, Callable
from functools import wraps
from datetime import timedelta

logger = logging.getLogger(__name__)

# ══════════════════════════════════════════════════════════════════════════════
# CACHE CONFIGURATION
# ══════════════════════════════════════════════════════════════════════════════

CACHE_TTL_SECONDS = int(os.getenv("CACHE_TTL_SECONDS", 300))  # 5 minutes default
REDIS_URL = os.getenv("REDIS_URL", None)  # e.g., redis://localhost:6379/0

# Cache keys for quick actions
CACHE_KEYS = {
    "vms": "gcp:quick:vms",
    "networks": "gcp:quick:networks", 
    "buckets": "gcp:quick:buckets",
    "billing": "gcp:quick:billing",
}

# ══════════════════════════════════════════════════════════════════════════════
# REDIS CLIENT (with fallback)
# ══════════════════════════════════════════════════════════════════════════════

_redis_client = None
_memory_cache = {}  # Fallback in-memory cache

def get_redis_client():
    """Get Redis client, creating one if needed. Returns None if unavailable."""
    global _redis_client
    
    if _redis_client is not None:
        return _redis_client
    
    if not REDIS_URL:
        logger.info("REDIS_URL not set, using in-memory cache fallback")
        return None
    
    try:
        import redis
        _redis_client = redis.from_url(
            REDIS_URL,
            decode_responses=True,
            socket_timeout=2,
            socket_connect_timeout=2
        )
        # Test connection
        _redis_client.ping()
        logger.info(f"Connected to Redis: {REDIS_URL}")
        return _redis_client
    except Exception as e:
        logger.warning(f"Redis unavailable ({e}), using in-memory cache fallback")
        _redis_client = None
        return None


# ══════════════════════════════════════════════════════════════════════════════
# IN-MEMORY CACHE (TTL-based fallback)
# ══════════════════════════════════════════════════════════════════════════════

import time

class TTLCache:
    """Simple TTL cache for when Redis is unavailable."""
    
    def __init__(self):
        self._cache = {}
        self._expiry = {}
    
    def get(self, key: str) -> Optional[str]:
        if key in self._cache:
            if time.time() < self._expiry.get(key, 0):
                return self._cache[key]
            else:
                # Expired - clean up
                del self._cache[key]
                del self._expiry[key]
        return None
    
    def set(self, key: str, value: str, ttl: int = CACHE_TTL_SECONDS):
        self._cache[key] = value
        self._expiry[key] = time.time() + ttl
    
    def delete(self, key: str):
        self._cache.pop(key, None)
        self._expiry.pop(key, None)
    
    def clear_pattern(self, pattern: str):
        """Clear all keys matching pattern (simple prefix matching)."""
        prefix = pattern.replace("*", "")
        to_delete = [k for k in self._cache.keys() if k.startswith(prefix)]
        for k in to_delete:
            self.delete(k)


_ttl_cache = TTLCache()


# ══════════════════════════════════════════════════════════════════════════════
# UNIFIED CACHE INTERFACE
# ══════════════════════════════════════════════════════════════════════════════

def cache_get(key: str) -> Optional[Any]:
    """Get value from cache (Redis or fallback)."""
    redis = get_redis_client()
    
    try:
        if redis:
            value = redis.get(key)
        else:
            value = _ttl_cache.get(key)
        
        if value:
            return json.loads(value)
        return None
    except Exception as e:
        logger.error(f"Cache get error for {key}: {e}")
        return None


def cache_set(key: str, value: Any, ttl: int = CACHE_TTL_SECONDS) -> bool:
    """Set value in cache (Redis or fallback)."""
    redis = get_redis_client()
    
    try:
        serialized = json.dumps(value, default=str)
        
        if redis:
            redis.setex(key, ttl, serialized)
        else:
            _ttl_cache.set(key, serialized, ttl)
        
        logger.debug(f"Cached {key} with TTL={ttl}s")
        return True
    except Exception as e:
        logger.error(f"Cache set error for {key}: {e}")
        return False


def cache_delete(key: str) -> bool:
    """Delete a key from cache."""
    redis = get_redis_client()
    
    try:
        if redis:
            redis.delete(key)
        else:
            _ttl_cache.delete(key)
        return True
    except Exception as e:
        logger.error(f"Cache delete error for {key}: {e}")
        return False


def cache_invalidate_all() -> bool:
    """Invalidate all GCP quick action caches."""
    redis = get_redis_client()
    
    try:
        if redis:
            for key in CACHE_KEYS.values():
                redis.delete(key)
        else:
            _ttl_cache.clear_pattern("gcp:quick:")
        
        logger.info("All GCP quick action caches invalidated")
        return True
    except Exception as e:
        logger.error(f"Cache invalidate error: {e}")
        return False


# ══════════════════════════════════════════════════════════════════════════════
# CACHED DATA FETCHERS (for quick actions)
# ══════════════════════════════════════════════════════════════════════════════

def get_cached_vms(project_id: str = None) -> dict:
    """Get VMs from cache or fetch fresh."""
    from app.gcp import vm
    
    cache_key = f"{CACHE_KEYS['vms']}:{project_id or 'default'}"
    cached = cache_get(cache_key)
    
    if cached is not None:
        logger.debug(f"Cache HIT: {cache_key}")
        return {"data": cached, "cached": True}
    
    logger.debug(f"Cache MISS: {cache_key}")
    data = vm.list_vms(project_id=project_id)
    cache_set(cache_key, data)
    return {"data": data, "cached": False}


def get_cached_networks(project_id: str = None) -> dict:
    """Get VPC networks from cache or fetch fresh."""
    from app.gcp import vpc
    
    cache_key = f"{CACHE_KEYS['networks']}:{project_id or 'default'}"
    cached = cache_get(cache_key)
    
    if cached is not None:
        logger.debug(f"Cache HIT: {cache_key}")
        return {"data": cached, "cached": True}
    
    logger.debug(f"Cache MISS: {cache_key}")
    data = vpc.list_networks(project_id=project_id)
    cache_set(cache_key, data)
    return {"data": data, "cached": False}


def get_cached_buckets(project_id: str = None) -> dict:
    """Get storage buckets from cache or fetch fresh."""
    from app.gcp import storage
    
    cache_key = f"{CACHE_KEYS['buckets']}:{project_id or 'default'}"
    cached = cache_get(cache_key)
    
    if cached is not None:
        logger.debug(f"Cache HIT: {cache_key}")
        return {"data": cached, "cached": True}
    
    logger.debug(f"Cache MISS: {cache_key}")
    data = storage.list_buckets(project_id=project_id)
    cache_set(cache_key, data)
    return {"data": data, "cached": False}


def get_cached_billing(project_id: str = None) -> dict:
    """Get billing summary from cache or fetch fresh."""
    from app.gcp import billing
    
    cache_key = f"{CACHE_KEYS['billing']}:{project_id or 'default'}"
    cached = cache_get(cache_key)
    
    if cached is not None:
        logger.debug(f"Cache HIT: {cache_key}")
        return {"data": cached, "cached": True}
    
    logger.debug(f"Cache MISS: {cache_key}")
    data = billing.get_billing_summary()
    cache_set(cache_key, data)
    return {"data": data, "cached": False}


# ══════════════════════════════════════════════════════════════════════════════
# DECORATOR FOR EASY CACHING
# ══════════════════════════════════════════════════════════════════════════════

def cached(cache_key_prefix: str, ttl: int = CACHE_TTL_SECONDS):
    """
    Decorator to cache function results.
    
    Usage:
        @cached("gcp:vms")
        def list_vms(project_id=None):
            ...
    """
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Build cache key from prefix + args
            key_parts = [cache_key_prefix]
            if args:
                key_parts.extend(str(a) for a in args)
            if kwargs:
                key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
            
            cache_key = ":".join(key_parts)
            
            # Try cache first
            cached_value = cache_get(cache_key)
            if cached_value is not None:
                return cached_value
            
            # Execute function and cache result
            result = func(*args, **kwargs)
            cache_set(cache_key, result, ttl)
            return result
        
        return wrapper
    return decorator


# ══════════════════════════════════════════════════════════════════════════════
# PRELOAD CACHE (for startup)
# ══════════════════════════════════════════════════════════════════════════════

async def preload_quick_action_cache(project_id: str = None):
    """
    Preload all 4 quick action caches on startup.
    Call this from main.py on app startup for instant responses.
    """
    import asyncio
    from concurrent.futures import ThreadPoolExecutor
    
    logger.info("Preloading quick action caches...")
    
    def _preload():
        try:
            get_cached_vms(project_id)
            logger.info("✓ VMs cache preloaded")
        except Exception as e:
            logger.warning(f"✗ VMs cache preload failed: {e}")
        
        try:
            get_cached_networks(project_id)
            logger.info("✓ Networks cache preloaded")
        except Exception as e:
            logger.warning(f"✗ Networks cache preload failed: {e}")
        
        try:
            get_cached_buckets(project_id)
            logger.info("✓ Buckets cache preloaded")
        except Exception as e:
            logger.warning(f"✗ Buckets cache preload failed: {e}")
        
        try:
            get_cached_billing(project_id)
            logger.info("✓ Billing cache preloaded")
        except Exception as e:
            logger.warning(f"✗ Billing cache preload failed: {e}")
    
    # Run in thread pool to not block startup
    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor() as pool:
        await loop.run_in_executor(pool, _preload)
    
    logger.info("Quick action cache preload complete")
