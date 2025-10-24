"""
Comprehensive tests for health check endpoints.
"""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from ta_bot.health import (
    app,
    get_health_status,
    get_liveness_status,
    get_readiness_status,
    get_uptime,
)


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


class TestHealthEndpoints:
    """Test suite for health check endpoints."""

    def test_health_check_healthy(self, client):
        """Test health check returns healthy status."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] in ["healthy", "degraded"]
        assert "version" in data
        assert "build_info" in data
        assert "components" in data
        assert "uptime" in data
        assert "timestamp" in data

    def test_health_check_with_nats_publisher(self, client):
        """Test health check with NATS publisher connected."""
        # Mock the publisher in app state
        mock_publisher = MagicMock()
        mock_publisher.nats_client = MagicMock()  # Connected
        app.state.publisher = mock_publisher

        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["components"]["nats_publisher"] == "connected"

    def test_health_check_with_disconnected_nats(self, client):
        """Test health check with NATS publisher disconnected."""
        mock_publisher = MagicMock()
        mock_publisher.nats_client = None  # Disconnected
        app.state.publisher = mock_publisher

        with patch.dict("os.environ", {"NATS_ENABLED": "true"}):
            response = client.get("/health")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "degraded"
            assert data["components"]["nats_publisher"] == "disconnected"

    def test_readiness_check(self, client):
        """Test readiness endpoint."""
        response = client.get("/ready")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"
        assert "checks" in data
        assert "uptime" in data
        assert "timestamp" in data

    def test_liveness_check(self, client):
        """Test liveness endpoint."""
        response = client.get("/live")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "alive"
        assert "uptime" in data
        assert "timestamp" in data

    def test_metrics_endpoint(self, client):
        """Test Prometheus metrics endpoint."""
        response = client.get("/metrics")
        assert response.status_code == 200
        assert "text/plain" in response.headers["content-type"]
        # Check for some expected metrics
        content = response.text
        assert "service_uptime_seconds" in content

    def test_root_endpoint(self, client):
        """Test root endpoint."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "TA Bot Health API"
        assert "version" in data
        assert data["status"] == "running"
        assert "uptime" in data

    def test_get_uptime_formatting(self):
        """Test uptime formatting function."""
        with patch("ta_bot.health.start_time", 0):
            with patch("time.time", return_value=3661):  # 1h 1m 1s
                uptime = get_uptime()
                assert "1h" in uptime
                assert "1m" in uptime
                assert "1s" in uptime

            with patch("time.time", return_value=61):  # 1m 1s
                uptime = get_uptime()
                assert "h" not in uptime
                assert "1m" in uptime
                assert "1s" in uptime

            with patch("time.time", return_value=5):  # 5s
                uptime = get_uptime()
                assert "h" not in uptime
                assert "m" not in uptime
                assert "5s" in uptime

    def test_get_health_status_legacy(self):
        """Test legacy get_health_status function."""
        status = get_health_status()
        assert status["status"] == "healthy"
        assert "version" in status
        assert "build_info" in status
        assert "components" in status

    def test_get_readiness_status_legacy(self):
        """Test legacy get_readiness_status function."""
        status = get_readiness_status()
        assert status["status"] == "ready"
        assert "checks" in status

    def test_get_liveness_status_legacy(self):
        """Test legacy get_liveness_status function."""
        status = get_liveness_status()
        assert status["status"] == "alive"
        assert "uptime" in status

    def test_health_with_environment_variables(self, client):
        """Test health check with custom environment variables."""
        with patch.dict(
            "os.environ",
            {
                "VERSION": "2.0.0",
                "COMMIT_SHA": "abc123",
                "BUILD_DATE": "2025-10-24",
            },
        ):
            response = client.get("/health")
            assert response.status_code == 200
            data = response.json()
            assert data["version"] == "2.0.0"
            assert data["build_info"]["commit_sha"] == "abc123"
            assert data["build_info"]["build_date"] == "2025-10-24"

    def test_health_with_nats_disabled(self, client):
        """Test health check with NATS disabled."""
        with patch.dict("os.environ", {"NATS_ENABLED": "false"}):
            response = client.get("/health")
            assert response.status_code == 200
            data = response.json()
            assert data["components"]["nats_listener"] == "disabled"

    def test_readiness_with_nats_disabled(self, client):
        """Test readiness check with NATS disabled."""
        with patch.dict("os.environ", {"NATS_ENABLED": "false"}):
            response = client.get("/ready")
            assert response.status_code == 200
            data = response.json()
            assert data["checks"]["nats_connection"] == "disabled"
