"""
Tests for DataManagerConfigClient.
"""

from unittest.mock import AsyncMock, patch

import pytest
from aiohttp import ClientSession, ClientTimeout

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
        assert client._session is None

    @pytest.mark.asyncio
    async def test_connect_success(self):
        """Test successful connection."""
        client = DataManagerConfigClient()

        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_session = AsyncMock(spec=ClientSession)
            mock_session_class.return_value = mock_session

            # Mock successful health check response
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json.return_value = {"status": "alive"}

            # Create a proper async context manager mock
            mock_context = AsyncMock()
            mock_context.__aenter__.return_value = mock_response
            mock_session.get.return_value = mock_context

            await client.connect()

            assert client._session is mock_session
            mock_session.get.assert_called_once_with(
                f"{client.base_url}/health/liveness"
            )
            mock_session_class.assert_called_once_with(
                timeout=ClientTimeout(total=client.timeout)
            )

    @pytest.mark.asyncio
    async def test_connect_failure(self):
        """Test connection failure."""
        client = DataManagerConfigClient()

        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_session = AsyncMock(spec=ClientSession)
            mock_session_class.return_value = mock_session

            # Mock failed health check response
            mock_response = AsyncMock()
            mock_response.status = 500
            mock_response.json.return_value = {"status": "dead"}

            # Create a proper async context manager mock
            mock_context = AsyncMock()
            mock_context.__aenter__.return_value = mock_response
            mock_session.get.return_value = mock_context

            with pytest.raises(ConnectionError):
                await client.connect()

            mock_session.get.assert_called_once_with(
                f"{client.base_url}/health/liveness"
            )

    @pytest.mark.asyncio
    async def test_disconnect(self):
        """Test disconnection."""
        client = DataManagerConfigClient()
        mock_session = AsyncMock(spec=ClientSession)
        client._session = mock_session

        await client.disconnect()

        mock_session.close.assert_called_once()
        assert client._session is None

    @pytest.mark.asyncio
    async def test_get_app_config_success(self):
        """Test successful app config retrieval."""
        client = DataManagerConfigClient()
        client._session = AsyncMock(spec=ClientSession)

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = {
            "enabled_strategies": ["momentum_pulse"],
            "symbols": ["BTCUSDT"],
            "version": 1,
        }

        # Create a proper async context manager mock
        mock_context = AsyncMock()
        mock_context.__aenter__.return_value = mock_response
        client._session.get.return_value = mock_context

        result = await client.get_app_config()

        assert result == {
            "enabled_strategies": ["momentum_pulse"],
            "symbols": ["BTCUSDT"],
            "version": 1,
        }
        client._session.get.assert_called_once_with(
            f"{client.base_url}/config/application"
        )

    @pytest.mark.asyncio
    async def test_get_app_config_failure(self):
        """Test failed app config retrieval."""
        client = DataManagerConfigClient()
        client._session = AsyncMock(spec=ClientSession)

        # Use a simple exception instead of complex ClientConnectorError
        client._session.get.side_effect = Exception("Connection refused")

        result = await client.get_app_config()
        # Should return default config when service fails
        assert result["enabled_strategies"] == []
        assert result["source"] == "default"
        client._session.get.assert_called_once_with(
            f"{client.base_url}/config/application"
        )

    @pytest.mark.asyncio
    async def test_set_app_config_success(self):
        """Test successful app config update."""
        client = DataManagerConfigClient()
        client._session = AsyncMock(spec=ClientSession)

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = {"success": True}

        # Create a proper async context manager mock
        mock_context = AsyncMock()
        mock_context.__aenter__.return_value = mock_response
        client._session.post.return_value = mock_context

        config_data = {"min_confidence": 0.7}
        result = await client.set_app_config(config_data, "test_user", "test_reason")

        assert result is True
        client._session.post.assert_called_once_with(
            f"{client.base_url}/config/application",
            json={
                "enabled_strategies": [],
                "symbols": [],
                "candle_periods": [],
                "min_confidence": 0.7,
                "max_confidence": 0.95,
                "max_positions": 10,
                "position_sizes": [100, 200, 500, 1000],
                "changed_by": "test_user",
                "reason": "test_reason",
            },
        )

    @pytest.mark.asyncio
    async def test_set_app_config_failure(self):
        """Test failed app config update."""
        client = DataManagerConfigClient()
        client._session = AsyncMock(spec=ClientSession)

        # Use a simple exception instead of complex ClientConnectorError
        client._session.post.side_effect = Exception("Connection refused")

        config_data = {"min_confidence": 0.7}
        result = await client.set_app_config(config_data, "test_user", "test_reason")

        assert result is False
        client._session.post.assert_called_once_with(
            f"{client.base_url}/config/application",
            json={
                "enabled_strategies": [],
                "symbols": [],
                "candle_periods": [],
                "min_confidence": 0.7,
                "max_confidence": 0.95,
                "max_positions": 10,
                "position_sizes": [100, 200, 500, 1000],
                "changed_by": "test_user",
                "reason": "test_reason",
            },
        )

    @pytest.mark.asyncio
    async def test_get_strategy_config_success(self):
        """Test successful strategy config retrieval."""
        client = DataManagerConfigClient()
        client._session = AsyncMock(spec=ClientSession)

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = {
            "parameters": {"rsi_period": 14},
            "version": 1,
        }

        # Create a proper async context manager mock
        mock_context = AsyncMock()
        mock_context.__aenter__.return_value = mock_response
        client._session.get.return_value = mock_context

        result = await client.get_strategy_config("momentum_pulse")

        assert result == {
            "parameters": {"rsi_period": 14},
            "version": 1,
        }
        client._session.get.assert_called_once_with(
            f"{client.base_url}/config/strategies/momentum_pulse"
        )

    @pytest.mark.asyncio
    async def test_get_strategy_config_with_symbol(self):
        """Test successful strategy config retrieval with symbol."""
        client = DataManagerConfigClient()
        client._session = AsyncMock(spec=ClientSession)

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = {
            "parameters": {"rsi_period": 14},
            "version": 1,
        }

        # Create a proper async context manager mock
        mock_context = AsyncMock()
        mock_context.__aenter__.return_value = mock_response
        client._session.get.return_value = mock_context

        result = await client.get_strategy_config("momentum_pulse", "BTCUSDT")

        assert result == {
            "parameters": {"rsi_period": 14},
            "version": 1,
        }
        client._session.get.assert_called_once_with(
            f"{client.base_url}/config/strategies/momentum_pulse?symbol=BTCUSDT"
        )

    @pytest.mark.asyncio
    async def test_set_strategy_config_success(self):
        """Test successful strategy config update."""
        client = DataManagerConfigClient()
        client._session = AsyncMock(spec=ClientSession)

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = {"success": True}

        # Create a proper async context manager mock
        mock_context = AsyncMock()
        mock_context.__aenter__.return_value = mock_response
        client._session.post.return_value = mock_context

        parameters = {"rsi_period": 20}
        result = await client.set_strategy_config(
            "momentum_pulse", parameters, "test_user", "BTCUSDT", "test_reason"
        )

        assert result is True
        client._session.post.assert_called_once_with(
            f"{client.base_url}/config/strategies/momentum_pulse?symbol=BTCUSDT",
            json={
                "parameters": parameters,
                "changed_by": "test_user",
                "reason": "test_reason",
            },
        )

    @pytest.mark.asyncio
    async def test_set_strategy_config_failure(self):
        """Test failed strategy config update."""
        client = DataManagerConfigClient()
        client._session = AsyncMock(spec=ClientSession)

        # Use a simple exception instead of complex ClientConnectorError
        client._session.post.side_effect = Exception("Connection refused")

        parameters = {"rsi_period": 20}
        result = await client.set_strategy_config(
            "momentum_pulse", parameters, "test_user", "BTCUSDT", "test_reason"
        )

        assert result is False
        client._session.post.assert_called_once_with(
            f"{client.base_url}/config/strategies/momentum_pulse?symbol=BTCUSDT",
            json={
                "parameters": parameters,
                "changed_by": "test_user",
                "reason": "test_reason",
            },
        )

    @pytest.mark.asyncio
    async def test_list_strategy_configs_success(self):
        """Test successful strategy config listing."""
        client = DataManagerConfigClient()
        client._session = AsyncMock(spec=ClientSession)

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = {
            "strategy_ids": ["momentum_pulse", "rsi_extreme_reversal"]
        }

        # Create a proper async context manager mock
        mock_context = AsyncMock()
        mock_context.__aenter__.return_value = mock_response
        client._session.get.return_value = mock_context

        result = await client.list_strategy_configs()

        assert result == ["momentum_pulse", "rsi_extreme_reversal"]
        client._session.get.assert_called_once_with(
            f"{client.base_url}/config/strategies"
        )

    @pytest.mark.asyncio
    async def test_list_strategy_configs_failure(self):
        """Test failed strategy config listing."""
        client = DataManagerConfigClient()
        client._session = AsyncMock(spec=ClientSession)

        # Use a simple exception instead of complex ClientConnectorError
        client._session.get.side_effect = Exception("Connection refused")

        result = await client.list_strategy_configs()
        assert result == []
        client._session.get.assert_called_once_with(
            f"{client.base_url}/config/strategies"
        )

    @pytest.mark.asyncio
    async def test_delete_strategy_config_success(self):
        """Test successful strategy config deletion."""
        client = DataManagerConfigClient()
        client._session = AsyncMock(spec=ClientSession)

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = {"success": True}

        # Create a proper async context manager mock
        mock_context = AsyncMock()
        mock_context.__aenter__.return_value = mock_response
        client._session.delete.return_value = mock_context

        result = await client.delete_strategy_config("momentum_pulse")

        assert result is True
        client._session.delete.assert_called_once_with(
            f"{client.base_url}/config/strategies/momentum_pulse"
        )

    @pytest.mark.asyncio
    async def test_delete_strategy_config_with_symbol(self):
        """Test successful strategy config deletion with symbol."""
        client = DataManagerConfigClient()
        client._session = AsyncMock(spec=ClientSession)

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = {"success": True}

        # Create a proper async context manager mock
        mock_context = AsyncMock()
        mock_context.__aenter__.return_value = mock_response
        client._session.delete.return_value = mock_context

        result = await client.delete_strategy_config("momentum_pulse", "BTCUSDT")

        assert result is True
        client._session.delete.assert_called_once_with(
            f"{client.base_url}/config/strategies/momentum_pulse?symbol=BTCUSDT"
        )

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
