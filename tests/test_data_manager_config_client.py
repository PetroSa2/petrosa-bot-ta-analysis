"""
Tests for DataManagerConfigClient.
"""

from unittest.mock import AsyncMock, patch

import pytest

from ta_bot.services.data_manager_config_client import DataManagerConfigClient


class TestDataManagerConfigClient:
    """Test DataManagerConfigClient functionality."""

    def test_initialization(self):
        """Test client initialization."""
        client = DataManagerConfigClient()
        assert client.base_url == "http://petrosa-data-manager:8000"
        assert client.timeout == 30
        assert client.max_retries == 3
        assert client._session is None

    def test_initialization_with_custom_params(self):
        """Test client initialization with custom parameters."""
        client = DataManagerConfigClient(
            base_url="http://custom-url:9000", timeout=60, max_retries=5
        )
        assert client.base_url == "http://custom-url:9000"
        assert client.timeout == 60
        assert client.max_retries == 5

    @pytest.mark.asyncio
    async def test_connect_success(self):
        """Test successful connection."""
        client = DataManagerConfigClient()

        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_session = AsyncMock()
            mock_session_class.return_value = mock_session

            # Mock successful health check
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json.return_value = {"status": "alive"}
            mock_session.get.return_value.__aenter__.return_value = mock_response

            await client.connect()

            assert client._session is not None
            mock_session.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_connect_failure(self):
        """Test connection failure."""
        client = DataManagerConfigClient()

        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_session = AsyncMock()
            mock_session_class.return_value = mock_session

            # Mock failed health check
            mock_response = AsyncMock()
            mock_response.status = 500
            mock_session.get.return_value.__aenter__.return_value = mock_response

            with pytest.raises(ConnectionError):
                await client.connect()

    @pytest.mark.asyncio
    async def test_disconnect(self):
        """Test disconnection."""
        client = DataManagerConfigClient()
        client._session = AsyncMock()

        await client.disconnect()

        client._session.close.assert_called_once()
        assert client._session is None

    @pytest.mark.asyncio
    async def test_get_app_config_success(self):
        """Test successful app config retrieval."""
        client = DataManagerConfigClient()
        client._session = AsyncMock()

        # Mock successful response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = {
            "enabled_strategies": ["momentum_pulse"],
            "symbols": ["BTCUSDT"],
            "version": 1,
        }
        client._session.get.return_value.__aenter__.return_value = mock_response

        result = await client.get_app_config()

        assert result["enabled_strategies"] == ["momentum_pulse"]
        assert result["symbols"] == ["BTCUSDT"]
        assert result["version"] == 1

    @pytest.mark.asyncio
    async def test_get_app_config_failure(self):
        """Test app config retrieval failure."""
        client = DataManagerConfigClient()
        client._session = AsyncMock()

        # Mock failed response
        mock_response = AsyncMock()
        mock_response.status = 500
        client._session.get.return_value.__aenter__.return_value = mock_response

        result = await client.get_app_config()

        # Should return None when service fails
        assert result is None

    @pytest.mark.asyncio
    async def test_set_app_config_success(self):
        """Test successful app config update."""
        client = DataManagerConfigClient()
        client._session = AsyncMock()

        # Mock successful response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = {"success": True}
        client._session.post.return_value.__aenter__.return_value = mock_response

        config = {"enabled_strategies": ["momentum_pulse"], "symbols": ["BTCUSDT"]}

        result = await client.set_app_config(config, "test_user", "test reason")

        assert result is True
        client._session.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_set_app_config_failure(self):
        """Test app config update failure."""
        client = DataManagerConfigClient()
        client._session = AsyncMock()

        # Mock failed response
        mock_response = AsyncMock()
        mock_response.status = 500
        client._session.post.return_value.__aenter__.return_value = mock_response

        config = {"enabled_strategies": ["momentum_pulse"], "symbols": ["BTCUSDT"]}

        result = await client.set_app_config(config, "test_user", "test reason")

        assert result is False

    @pytest.mark.asyncio
    async def test_get_strategy_config_success(self):
        """Test successful strategy config retrieval."""
        client = DataManagerConfigClient()
        client._session = AsyncMock()

        # Mock successful response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = {
            "parameters": {"rsi_period": 14},
            "version": 1,
        }
        client._session.get.return_value.__aenter__.return_value = mock_response

        result = await client.get_strategy_config("momentum_pulse")

        assert result["parameters"]["rsi_period"] == 14
        assert result["version"] == 1

    @pytest.mark.asyncio
    async def test_get_strategy_config_with_symbol(self):
        """Test strategy config retrieval with symbol."""
        client = DataManagerConfigClient()
        client._session = AsyncMock()

        # Mock successful response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = {
            "parameters": {"rsi_period": 14},
            "version": 1,
        }
        client._session.get.return_value.__aenter__.return_value = mock_response

        await client.get_strategy_config("momentum_pulse", "BTCUSDT")

        # Check that the method was called
        client._session.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_strategy_configs_success(self):
        """Test successful strategy config listing."""
        client = DataManagerConfigClient()
        client._session = AsyncMock()

        # Mock successful response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = {
            "strategy_ids": ["momentum_pulse", "rsi_extreme_reversal"]
        }
        client._session.get.return_value.__aenter__.return_value = mock_response

        result = await client.list_strategy_configs()

        assert result == ["momentum_pulse", "rsi_extreme_reversal"]

    @pytest.mark.asyncio
    async def test_list_strategy_configs_failure(self):
        """Test strategy config listing failure."""
        client = DataManagerConfigClient()
        client._session = AsyncMock()

        # Mock failed response
        mock_response = AsyncMock()
        mock_response.status = 500
        client._session.get.return_value.__aenter__.return_value = mock_response

        result = await client.list_strategy_configs()

        assert result == []

    def test_get_default_config(self):
        """Test default configuration."""
        client = DataManagerConfigClient()
        result = client._get_default_config()

        assert result["enabled_strategies"] == []
        assert result["symbols"] == []
        assert result["candle_periods"] == []
        assert result["min_confidence"] == 0.6
        assert result["max_confidence"] == 0.95
        assert result["max_positions"] == 10
        assert result["position_sizes"] == [100, 200, 500, 1000]
        assert result["version"] == 0
        assert result["source"] == "default"

    def test_get_default_strategy_config(self):
        """Test default strategy configuration."""
        client = DataManagerConfigClient()
        result = client._get_default_strategy_config()

        assert result["parameters"] == {}
        assert result["version"] == 0
        assert result["source"] == "none"
        assert result["is_override"] is False
