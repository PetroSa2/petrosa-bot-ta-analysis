"""
Comprehensive tests for application configuration manager.
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ta_bot.models.app_config import AppConfig
from ta_bot.services.app_config_manager import AppConfigManager


@pytest.fixture
def mock_mongodb_client():
    """Create a mock MongoDB client."""
    client = AsyncMock()
    client.is_connected = True
    return client


@pytest.fixture
def mock_mysql_client():
    """Create a mock MySQL client."""
    return AsyncMock()


@pytest.fixture
def mock_data_manager_client():
    """Create a mock Data Manager client."""
    return AsyncMock()


@pytest.fixture
def config_manager(mock_mongodb_client, mock_mysql_client, mock_data_manager_client):
    """Create a config manager with mocked clients."""
    return AppConfigManager(
        mongodb_client=mock_mongodb_client,
        mysql_client=mock_mysql_client,
        data_manager_client=mock_data_manager_client,
        cache_ttl_seconds=60,
    )


@pytest.mark.asyncio
class TestAppConfigManager:
    """Test suite for AppConfigManager."""

    async def test_start(self, config_manager, mock_mongodb_client, mock_mysql_client):
        """Test starting the config manager."""
        await config_manager.start()

        mock_mongodb_client.connect.assert_called_once()
        mock_mysql_client.connect.assert_called_once()
        assert config_manager._running is True

    async def test_stop(self, config_manager, mock_mongodb_client, mock_mysql_client):
        """Test stopping the config manager."""
        await config_manager.start()
        await config_manager.stop()

        assert config_manager._running is False
        mock_mongodb_client.disconnect.assert_called_once()
        mock_mysql_client.disconnect.assert_called_once()

    async def test_get_config_from_cache(self, config_manager):
        """Test getting config from cache."""
        # Set cache
        cached_config = {
            "enabled_strategies": ["momentum_pulse"],
            "symbols": ["BTCUSDT"],
            "candle_periods": ["15m"],
            "min_confidence": 0.6,
            "max_confidence": 0.9,
            "max_positions": 10,
            "position_sizes": [100],
            "version": 1,
            "source": "test",
        }
        config_manager._set_cache(cached_config)

        # Get config
        result = await config_manager.get_config()

        assert result["cache_hit"] is True
        assert result["enabled_strategies"] == ["momentum_pulse"]

    async def test_get_config_from_data_manager(
        self, config_manager, mock_data_manager_client
    ):
        """Test getting config from Data Manager."""
        mock_config = {
            "enabled_strategies": ["momentum_pulse"],
            "symbols": ["BTCUSDT"],
            "candle_periods": ["15m"],
            "min_confidence": 0.6,
            "max_confidence": 0.9,
            "max_positions": 10,
            "position_sizes": [100],
            "version": 1,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }
        mock_data_manager_client.get_app_config.return_value = mock_config

        result = await config_manager.get_config()

        assert result["cache_hit"] is False
        assert result["source"] == "data_manager"
        mock_data_manager_client.get_app_config.assert_called_once()

    async def test_get_config_from_mongodb(
        self, config_manager, mock_mongodb_client, mock_data_manager_client
    ):
        """Test getting config from MongoDB when Data Manager fails."""
        # Data Manager returns None
        mock_data_manager_client.get_app_config.return_value = None

        mock_config = {
            "enabled_strategies": ["momentum_pulse"],
            "symbols": ["BTCUSDT"],
            "candle_periods": ["15m"],
            "min_confidence": 0.6,
            "max_confidence": 0.9,
            "max_positions": 10,
            "position_sizes": [100],
            "version": 1,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }
        mock_mongodb_client.get_app_config.return_value = mock_config

        result = await config_manager.get_config()

        assert result["source"] == "mongodb"
        mock_mongodb_client.get_app_config.assert_called_once()

    async def test_get_config_defaults(self, config_manager, mock_data_manager_client):
        """Test getting default config when no config exists."""
        mock_data_manager_client.get_app_config.return_value = None
        config_manager.mongodb_client = None
        config_manager.mysql_client = None

        result = await config_manager.get_config()

        assert result["source"] == "default"
        assert result["version"] == 0

    async def test_set_config_validation_only(self, config_manager):
        """Test validating config without saving."""
        config = {
            "enabled_strategies": ["momentum_pulse"],
            "symbols": ["BTCUSDT"],
            "candle_periods": ["15m"],
            "min_confidence": 0.6,
            "max_confidence": 0.9,
            "max_positions": 10,
            "position_sizes": [100],
        }

        success, app_config, errors = await config_manager.set_config(
            config, changed_by="test_user", validate_only=True
        )

        assert success is True
        assert app_config is None
        assert len(errors) == 0

    async def test_set_config_invalid(self, config_manager):
        """Test setting invalid config."""
        config = {
            "enabled_strategies": [],  # Empty - invalid
            "symbols": ["BTCUSDT"],
            "candle_periods": ["15m"],
        }

        success, app_config, errors = await config_manager.set_config(
            config, changed_by="test_user"
        )

        assert success is False
        assert app_config is None
        assert len(errors) > 0

    async def test_set_config_success(
        self, config_manager, mock_data_manager_client, mock_mongodb_client
    ):
        """Test successfully setting config."""
        # Mock get_config for audit trail
        config_manager._cache = None
        mock_data_manager_client.get_app_config.return_value = {
            "version": 0,
            "enabled_strategies": [],
        }

        config = {
            "enabled_strategies": ["momentum_pulse"],
            "symbols": ["BTCUSDT"],
            "candle_periods": ["15m"],
            "min_confidence": 0.6,
            "max_confidence": 0.9,
            "max_positions": 10,
            "position_sizes": [100],
        }

        mock_data_manager_client.set_app_config.return_value = True

        success, app_config, errors = await config_manager.set_config(
            config, changed_by="test_user", reason="Testing"
        )

        assert success is True
        assert app_config is not None
        assert isinstance(app_config, AppConfig)
        assert len(errors) == 0
        mock_data_manager_client.set_app_config.assert_called_once()

    async def test_refresh_cache(self, config_manager):
        """Test refreshing cache."""
        # Set cache
        config_manager._set_cache({"version": 1})
        assert config_manager._cache is not None

        # Refresh
        await config_manager.refresh_cache()

        assert config_manager._cache is None

    async def test_get_audit_trail(self, config_manager, mock_mongodb_client):
        """Test getting audit trail."""
        mock_records = [
            {
                "_id": "audit1",
                "config_id": "config1",
                "action": "CREATE",
                "new_config": {"enabled_strategies": ["momentum_pulse"]},
                "changed_by": "user1",
                "changed_at": datetime.utcnow(),
            }
        ]
        mock_mongodb_client.get_app_audit_trail.return_value = mock_records

        records = await config_manager.get_audit_trail(limit=10)

        assert len(records) == 1
        assert records[0].action == "CREATE"
        mock_mongodb_client.get_app_audit_trail.assert_called_once_with(10)

    async def test_cache_expiration(self, config_manager):
        """Test cache expiration."""
        import time

        # Set short TTL
        config_manager.cache_ttl_seconds = 1

        # Set cache
        cached_config = {"version": 1}
        config_manager._set_cache(cached_config)

        # Wait for expiration
        time.sleep(2)

        # Get from cache should return None
        result = config_manager._get_from_cache()
        assert result is None
