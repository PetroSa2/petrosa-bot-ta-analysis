"""
Configuration Change Rate Limiter.

Prevents runaway configuration changes by enforcing quotas and cooldown periods.
"""

import logging
from datetime import datetime, timedelta
from typing import Any

logger = logging.getLogger(__name__)


class ConfigRateLimiter:
    """
    Rate limiter for configuration changes with per-agent quotas.

    Tracks configuration changes and enforces limits to prevent:
    - Configuration storms (too many changes too quickly)
    - MongoDB write exhaustion
    - Audit trail chaos
    - Service instability from rapid config changes
    """

    def __init__(
        self,
        mongodb_client=None,
        per_agent_limit: int = 10,  # 10 changes per hour per agent
        global_limit: int = 100,  # 100 total changes per hour
        window_seconds: int = 3600,  # 1 hour window
        cooldown_seconds: int = 300,  # 5 minute minimum between changes
    ):
        """
        Initialize rate limiter.

        Args:
            mongodb_client: MongoDB client for persistent quota tracking
            per_agent_limit: Max changes per agent per window
            global_limit: Max total changes per window
            window_seconds: Time window in seconds
            cooldown_seconds: Minimum seconds between changes
        """
        self.mongodb = mongodb_client
        self.per_agent_limit = per_agent_limit
        self.global_limit = global_limit
        self.window_seconds = window_seconds
        self.cooldown_seconds = cooldown_seconds

        # In-memory fallback if MongoDB unavailable
        self._memory_cache: dict[str, list[datetime]] = {}

    async def check_rate_limit(
        self, changed_by: str, endpoint: str, allow_emergency: bool = False
    ) -> dict[str, Any]:
        """
        Check if request is within rate limits.

        Args:
            changed_by: Agent/user making the change
            endpoint: API endpoint being called
            allow_emergency: Allow bypass for emergency operations

        Returns:
            Dict with allowed status, reason, retry_after, quota info
        """
        now = datetime.utcnow()
        window_start = now - timedelta(seconds=self.window_seconds)

        # Emergency bypass (e.g., for rollbacks)
        if allow_emergency and "ROLLBACK" in changed_by.upper():
            logger.info(f"Emergency bypass for {changed_by}")
            return {"allowed": True, "reason": "emergency_bypass"}

        try:
            # Use MongoDB if available
            if self.mongodb and hasattr(self.mongodb, "db"):
                agent_changes = await self._count_mongodb_changes(
                    changed_by, window_start
                )
                global_changes = await self._count_mongodb_global_changes(window_start)
                last_change_time = await self._get_last_change_time(changed_by)
            else:
                # Fallback to in-memory tracking
                agent_changes = self._count_memory_changes(changed_by, window_start)
                global_changes = sum(
                    len([t for t in times if t >= window_start])
                    for times in self._memory_cache.values()
                )
                last_change_time = self._get_last_memory_change(changed_by)

            # Check per-agent limit
            if agent_changes >= self.per_agent_limit:
                reset_at = window_start + timedelta(seconds=self.window_seconds)
                retry_after = int((reset_at - now).total_seconds())
                return {
                    "allowed": False,
                    "reason": "agent_quota_exceeded",
                    "retry_after": max(1, retry_after),
                    "quota_remaining": 0,
                    "quota_reset_at": reset_at.isoformat(),
                }

            # Check cooldown period
            if last_change_time:
                time_since_last = (now - last_change_time).total_seconds()
                if time_since_last < self.cooldown_seconds:
                    retry_after = int(self.cooldown_seconds - time_since_last)
                    return {
                        "allowed": False,
                        "reason": "cooldown_period",
                        "retry_after": max(1, retry_after),
                        "quota_remaining": self.per_agent_limit - agent_changes,
                    }

            # Check global limit
            if global_changes >= self.global_limit:
                retry_after = self.window_seconds
                return {
                    "allowed": False,
                    "reason": "global_quota_exceeded",
                    "retry_after": retry_after,
                    "quota_remaining": self.per_agent_limit - agent_changes,
                }

            # All checks passed
            return {
                "allowed": True,
                "quota_remaining": self.per_agent_limit - agent_changes - 1,
                "quota_reset_at": (
                    now + timedelta(seconds=self.window_seconds)
                ).isoformat(),
            }

        except Exception as e:
            logger.error(f"Rate limit check error: {e}")
            # Fail open - allow the request if rate limiter errors
            return {"allowed": True, "reason": "rate_limiter_error"}

    async def record_change(self, changed_by: str, endpoint: str) -> None:
        """Record a configuration change for rate limiting."""
        try:
            now = datetime.utcnow()

            if self.mongodb and hasattr(self.mongodb, "db"):
                # Store in MongoDB
                await self.mongodb.db["config_rate_limits"].insert_one(
                    {
                        "changed_by": changed_by,
                        "endpoint": endpoint,
                        "timestamp": now,
                    }
                )
            else:
                # Store in memory
                if changed_by not in self._memory_cache:
                    self._memory_cache[changed_by] = []
                self._memory_cache[changed_by].append(now)

                # Clean old entries
                self._cleanup_memory_cache()

        except Exception as e:
            logger.error(f"Failed to record rate limit change: {e}")

    async def get_quota_status(self, changed_by: str) -> dict[str, Any]:
        """Get current quota status for an agent."""
        now = datetime.utcnow()
        window_start = now - timedelta(seconds=self.window_seconds)

        try:
            if self.mongodb and hasattr(self.mongodb, "db"):
                agent_changes = await self._count_mongodb_changes(
                    changed_by, window_start
                )
            else:
                agent_changes = self._count_memory_changes(changed_by, window_start)

            return {
                "agent": changed_by,
                "changes_in_window": agent_changes,
                "quota_remaining": max(0, self.per_agent_limit - agent_changes),
                "quota_limit": self.per_agent_limit,
                "window_seconds": self.window_seconds,
                "cooldown_seconds": self.cooldown_seconds,
                "quota_reset_at": (
                    window_start + timedelta(seconds=self.window_seconds)
                ).isoformat(),
            }

        except Exception as e:
            logger.error(f"Failed to get quota status: {e}")
            return {
                "agent": changed_by,
                "error": str(e),
            }

    # MongoDB helpers
    async def _count_mongodb_changes(
        self, changed_by: str, window_start: datetime
    ) -> int:
        """Count changes in MongoDB"""
        count = await self.mongodb.db["config_rate_limits"].count_documents(
            {
                "changed_by": changed_by,
                "timestamp": {"$gte": window_start},
            }
        )
        return count

    async def _count_mongodb_global_changes(self, window_start: datetime) -> int:
        """Count all changes in MongoDB"""
        count = await self.mongodb.db["config_rate_limits"].count_documents(
            {"timestamp": {"$gte": window_start}}
        )
        return count

    async def _get_last_change_time(self, changed_by: str) -> datetime | None:
        """Get timestamp of last change from MongoDB"""
        doc = await self.mongodb.db["config_rate_limits"].find_one(
            {"changed_by": changed_by}, sort=[("timestamp", -1)]
        )
        return doc["timestamp"] if doc else None

    # In-memory fallback helpers
    def _count_memory_changes(self, changed_by: str, window_start: datetime) -> int:
        """Count changes in memory cache"""
        if changed_by not in self._memory_cache:
            return 0
        return len([t for t in self._memory_cache[changed_by] if t >= window_start])

    def _get_last_memory_change(self, changed_by: str) -> datetime | None:
        """Get last change time from memory"""
        if changed_by not in self._memory_cache or not self._memory_cache[changed_by]:
            return None
        return max(self._memory_cache[changed_by])

    def _cleanup_memory_cache(self) -> None:
        """Clean old entries from memory cache"""
        cutoff = datetime.utcnow() - timedelta(seconds=self.window_seconds * 2)
        for agent in list(self._memory_cache.keys()):
            self._memory_cache[agent] = [
                t for t in self._memory_cache[agent] if t >= cutoff
            ]
            if not self._memory_cache[agent]:
                del self._memory_cache[agent]
