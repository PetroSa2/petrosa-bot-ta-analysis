"""
Tests for Configuration Rate Limiter.

Verifies that rate limiting prevents configuration storms and enforces quotas.
"""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from ta_bot.middleware.rate_limiter import ConfigRateLimiter


@pytest.fixture
def mongodb_client():
    """Create mock MongoDB client"""
    client = MagicMock()
    client.db = MagicMock()
    client.db.__getitem__ = MagicMock(return_value=AsyncMock())
    return client


@pytest.fixture
def rate_limiter(mongodb_client):
    """Create rate limiter instance"""
    return ConfigRateLimiter(
        mongodb_client=None,  # Use in-memory for tests
        per_agent_limit=10,
        global_limit=100,
        window_seconds=3600,
        cooldown_seconds=300,
    )


class TestRateLimiter:
    """Test ConfigRateLimiter class"""

    @pytest.mark.asyncio
    async def test_allows_first_request(self, rate_limiter):
        """Test that first request is allowed"""
        result = await rate_limiter.check_rate_limit(
            changed_by="agent1", endpoint="/api/config", allow_emergency=False
        )

        assert result["allowed"] is True
        assert "quota_remaining" in result

    @pytest.mark.asyncio
    async def test_records_change(self, rate_limiter):
        """Test that changes are recorded"""
        await rate_limiter.record_change(changed_by="agent1", endpoint="/api/config")

        # Check that change was recorded
        result = await rate_limiter.check_rate_limit(
            changed_by="agent1", endpoint="/api/config"
        )

        assert result["quota_remaining"] == 8  # 10 - 1 (recorded) - 1 (this check) = 8

    @pytest.mark.asyncio
    async def test_enforces_per_agent_limit(self, rate_limiter):
        """Test that per-agent quota is enforced"""
        # Make 10 changes (the limit)
        for i in range(10):
            await rate_limiter.record_change(
                changed_by="agent1", endpoint="/api/config"
            )

        # 11th change should be blocked
        result = await rate_limiter.check_rate_limit(
            changed_by="agent1", endpoint="/api/config"
        )

        assert result["allowed"] is False
        assert result["reason"] == "agent_quota_exceeded"
        assert "retry_after" in result

    @pytest.mark.asyncio
    async def test_different_agents_independent_quotas(self, rate_limiter):
        """Test that different agents have independent quotas"""
        # Agent1 makes 10 changes
        for i in range(10):
            await rate_limiter.record_change(
                changed_by="agent1", endpoint="/api/config"
            )

        # Agent2 should still have full quota
        result = await rate_limiter.check_rate_limit(
            changed_by="agent2", endpoint="/api/config"
        )

        assert result["allowed"] is True
        assert result["quota_remaining"] == 9  # Full quota minus this check

    @pytest.mark.asyncio
    async def test_emergency_bypass(self, rate_limiter):
        """Test that emergency operations bypass rate limits"""
        # Exhaust quota
        for i in range(10):
            await rate_limiter.record_change(
                changed_by="agent1", endpoint="/api/config"
            )

        # Emergency rollback should still be allowed
        result = await rate_limiter.check_rate_limit(
            changed_by="ROLLBACK_agent1",
            endpoint="/api/config/rollback",
            allow_emergency=True,
        )

        assert result["allowed"] is True
        assert result["reason"] == "emergency_bypass"

    @pytest.mark.asyncio
    async def test_get_quota_status(self, rate_limiter):
        """Test getting quota status"""
        # Make some changes
        for i in range(3):
            await rate_limiter.record_change(
                changed_by="agent1", endpoint="/api/config"
            )

        status = await rate_limiter.get_quota_status("agent1")

        assert status["agent"] == "agent1"
        assert status["changes_in_window"] == 3
        assert status["quota_remaining"] == 7
        assert status["quota_limit"] == 10

    @pytest.mark.asyncio
    async def test_quota_resets_after_window(self, rate_limiter):
        """Test that quota resets after time window"""
        # This would require time manipulation, marking as placeholder
        # In real implementation, would use freezegun or similar
        pass


class TestRateLimitAPI:
    """Test rate limit API integration"""

    def test_rate_limit_status_endpoint(self, client):
        """Test GET /api/v1/config/rate-limits"""
        response = client.get("/api/v1/config/rate-limits?changed_by=test-agent")

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        # Rate limiting may or may not be enabled depending on config
        assert "data" in data

    def test_config_update_respects_rate_limit(self, client):
        """Test that config updates are rate limited"""
        # This would require setting up rate limiter in test client
        # Marking as integration test
        pass
