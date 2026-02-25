"""
Integration tests for application configuration rollback API endpoints.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from ta_bot.api.config_routes import router, set_app_config_manager
from ta_bot.models.app_config import AppConfig


@pytest.fixture
def client():
    # We need a clean router/app for each test
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    return TestClient(app)


@pytest.fixture
def mock_manager():
    manager = MagicMock()
    manager.rollback_config = AsyncMock()
    set_app_config_manager(manager)
    return manager


@pytest.mark.parametrize(
    "endpoint",
    ["/api/v1/config/application/rollback", "/api/v1/config/application/restore"],
)
def test_rollback_api_success(client, mock_manager, endpoint):
    """Test successful rollback/restore via API."""
    # 1. Setup mock return value
    mock_config = MagicMock(spec=AppConfig)
    mock_config.enabled_strategies = ["s1"]
    mock_config.symbols = ["BTCUSDT"]
    mock_config.candle_periods = ["1m"]
    mock_config.min_confidence = 0.6
    mock_config.max_confidence = 0.9
    mock_config.max_positions = 5
    mock_config.position_sizes = [100]
    mock_config.version = 2

    mock_manager.rollback_config.return_value = (True, mock_config, [])

    # 2. Execute request
    payload = {
        "changed_by": "admin",
        "reason": "Testing API",
        "target_version": 1,
        "rollback_id": "audit_123",
    }
    response = client.post(endpoint, json=payload)

    # 3. Verify
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["version"] == 2

    # Verify manager call
    mock_manager.rollback_config.assert_called_once_with(
        changed_by="admin",
        target_version=1,
        rollback_id="audit_123",
        reason="Testing API",
    )


@pytest.mark.parametrize(
    "endpoint",
    ["/api/v1/config/application/rollback", "/api/v1/config/application/restore"],
)
def test_rollback_api_failure(client, mock_manager, endpoint):
    """Test failed rollback via API."""
    # 1. Setup mock failure
    mock_manager.rollback_config.return_value = (False, None, ["Version not found"])

    # 2. Execute request
    response = client.post(endpoint, json={"changed_by": "admin"})

    # 3. Verify
    assert response.status_code == 200  # API returns 200 even on logical failure
    data = response.json()
    assert data["success"] is False
    assert data["error"]["code"] == "ROLLBACK_FAILED"
    assert "Version not found" in data["error"]["details"]["errors"]


def test_rollback_api_invalid_request(client):
    """Test validation error for missing required fields."""
    # Missing changed_by
    response = client.post(
        "/api/v1/config/application/rollback", json={"reason": "no user"}
    )
    assert response.status_code == 422  # Unprocessable Entity
