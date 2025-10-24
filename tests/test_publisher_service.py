"""
Comprehensive tests for signal publisher service.
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ta_bot.models.signal import Signal
from ta_bot.services.publisher import SignalPublisher


@pytest.fixture
def mock_signal():
    """Create a mock signal."""
    return Signal(
        symbol="BTCUSDT",
        timeframe="15m",
        action="buy",
        confidence=0.85,
        strategy_id="momentum_pulse",
        current_price=50000.0,
        price=50000.0,
        stop_loss=49000.0,
        take_profit=52000.0,
        timestamp="2025-10-24T00:00:00Z",
        metadata={"test": "value"},
    )


@pytest.fixture
def publisher():
    """Create a signal publisher."""
    return SignalPublisher(
        api_endpoint="http://test-api:8000/signals",
        nats_url="nats://test-nats:4222",
        enable_rest_publishing=False,
    )


@pytest.mark.asyncio
class TestSignalPublisher:
    """Test suite for SignalPublisher."""

    async def test_start_without_rest(self):
        """Test starting publisher without REST API."""
        publisher = SignalPublisher(
            api_endpoint="http://test:8000",
            nats_url="nats://test:4222",
            enable_rest_publishing=False,
        )

        with patch("nats.connect", new_callable=AsyncMock) as mock_connect:
            mock_connect.return_value = AsyncMock()
            await publisher.start()

            assert publisher.session is None
            mock_connect.assert_called_once_with("nats://test:4222")

    async def test_start_with_rest(self):
        """Test starting publisher with REST API enabled."""
        publisher = SignalPublisher(
            api_endpoint="http://test:8000",
            nats_url="nats://test:4222",
            enable_rest_publishing=True,
        )

        with patch("nats.connect", new_callable=AsyncMock) as mock_connect:
            mock_connect.return_value = AsyncMock()
            await publisher.start()

            assert publisher.session is not None
            mock_connect.assert_called_once()

    async def test_start_nats_connection_failure(self):
        """Test handling NATS connection failure."""
        publisher = SignalPublisher(
            api_endpoint="http://test:8000",
            nats_url="nats://test:4222",
            enable_rest_publishing=False,
        )

        with patch("nats.connect", side_effect=Exception("Connection failed")):
            await publisher.start()
            assert publisher.nats_client is None

    async def test_stop(self):
        """Test stopping publisher."""
        publisher = SignalPublisher(
            api_endpoint="http://test:8000",
            nats_url="nats://test:4222",
            enable_rest_publishing=True,
        )

        with patch("nats.connect", new_callable=AsyncMock) as mock_connect:
            mock_nats = AsyncMock()
            mock_connect.return_value = mock_nats
            await publisher.start()

            await publisher.stop()

            if publisher.session:
                assert publisher.session.closed
            mock_nats.close.assert_called_once()

    async def test_publish_signals_empty(self, publisher):
        """Test publishing empty signal list."""
        await publisher.publish_signals([])
        # Should not raise any errors

    async def test_publish_signals_via_nats(self, publisher, mock_signal):
        """Test publishing signals via NATS only."""
        with patch("nats.connect", new_callable=AsyncMock) as mock_connect:
            mock_nats = AsyncMock()
            mock_connect.return_value = mock_nats
            await publisher.start()

            await publisher.publish_signals([mock_signal])

            mock_nats.publish.assert_called_once()
            call_args = mock_nats.publish.call_args
            assert call_args[0][0] == "signals.trading"

    async def test_publish_signals_nats_not_connected(self, publisher, mock_signal):
        """Test publishing signals when NATS is not connected."""
        publisher.nats_client = None

        # Should log error but not raise exception
        await publisher.publish_signals([mock_signal])

    async def test_publish_via_rest_session_not_started(self, mock_signal):
        """Test publishing via REST when session not started."""
        publisher = SignalPublisher(
            api_endpoint="http://test:8000",
            nats_url=None,
            enable_rest_publishing=True,
        )

        # Should log warning but not raise exception
        await publisher._publish_via_rest([mock_signal])

    async def test_publish_via_rest_success(self, mock_signal):
        """Test successful REST API publishing."""
        publisher = SignalPublisher(
            api_endpoint="http://test:8000/signals",
            nats_url=None,
            enable_rest_publishing=True,
        )

        with patch("aiohttp.ClientSession.post") as mock_post:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.__aenter__.return_value = mock_response
            mock_response.__aexit__.return_value = None
            mock_post.return_value = mock_response

            await publisher.start()
            await publisher._publish_via_rest([mock_signal])

            mock_post.assert_called_once()

    async def test_publish_via_rest_failure(self, mock_signal):
        """Test REST API publishing failure."""
        publisher = SignalPublisher(
            api_endpoint="http://test:8000/signals",
            nats_url=None,
            enable_rest_publishing=True,
        )

        with patch("aiohttp.ClientSession.post") as mock_post:
            mock_response = AsyncMock()
            mock_response.status = 500
            mock_response.text = AsyncMock(return_value="Internal Server Error")
            mock_response.__aenter__.return_value = mock_response
            mock_response.__aexit__.return_value = None
            mock_post.return_value = mock_response

            await publisher.start()
            await publisher._publish_via_rest([mock_signal])

            mock_post.assert_called_once()

    async def test_publish_via_nats_error(self, publisher, mock_signal):
        """Test NATS publishing with error."""
        with patch("nats.connect", new_callable=AsyncMock) as mock_connect:
            mock_nats = AsyncMock()
            mock_nats.publish.side_effect = Exception("NATS error")
            mock_connect.return_value = mock_nats
            await publisher.start()

            # Should log error but not raise exception
            await publisher._publish_via_nats([mock_signal])

    async def test_publish_batch(self, publisher, mock_signal):
        """Test publishing signal batch."""
        with patch("nats.connect", new_callable=AsyncMock) as mock_connect:
            mock_nats = AsyncMock()
            mock_connect.return_value = mock_nats
            await publisher.start()

            signals = [mock_signal, mock_signal]
            await publisher.publish_batch(signals)

            assert mock_nats.publish.call_count == 2

    async def test_publish_batch_empty(self, publisher):
        """Test publishing empty batch."""
        await publisher.publish_batch([])
        # Should not raise any errors

    async def test_signal_to_dict_conversion(self, publisher, mock_signal):
        """Test signal conversion to dict for publishing."""
        with patch("nats.connect", new_callable=AsyncMock) as mock_connect:
            mock_nats = AsyncMock()
            mock_connect.return_value = mock_nats
            await publisher.start()

            await publisher.publish_signals([mock_signal])

            # Verify the signal was converted to dict and published
            call_args = mock_nats.publish.call_args
            message = call_args[0][1]
            data = json.loads(message.decode())

            assert data["symbol"] == "BTCUSDT"
            assert data["action"] == "buy"
            assert data["confidence"] == 0.85
