"""
Comprehensive tests for NATS listener service.
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pandas as pd
import pytest

from ta_bot.services.nats_listener import NATSListener


@pytest.fixture
def mock_signal_engine():
    """Create a mock signal engine."""
    engine = MagicMock()
    engine.analyze_candles.return_value = []
    return engine


@pytest.fixture
def mock_publisher():
    """Create a mock publisher."""
    publisher = AsyncMock()
    return publisher


@pytest.fixture
def mock_nats_client():
    """Create a mock NATS client."""
    client = AsyncMock()
    client.is_connected = True
    return client


@pytest.fixture
def nats_listener(mock_signal_engine, mock_publisher):
    """Create a NATS listener with mocked dependencies."""
    return NATSListener(
        nats_url="nats://test:4222",
        signal_engine=mock_signal_engine,
        publisher=mock_publisher,
        supported_symbols=["BTCUSDT", "ETHUSDT"],
        supported_timeframes=["15m", "1h"],
    )


@pytest.mark.asyncio
class TestNATSListener:
    """Test suite for NATSListener."""

    async def test_initialization(self, nats_listener):
        """Test NATS listener initialization."""
        assert nats_listener.nats_url == "nats://test:4222"
        assert "BTCUSDT" in nats_listener.supported_symbols
        assert "15m" in nats_listener.supported_timeframes

    async def test_start(self, nats_listener, mock_nats_client):
        """Test starting NATS listener."""
        with patch(
            "nats.aio.client.Client.connect", new_callable=AsyncMock
        ) as mock_connect:
            with patch.object(
                nats_listener.mysql_client, "connect", new_callable=AsyncMock
            ):
                with patch.object(
                    nats_listener.publisher, "start", new_callable=AsyncMock
                ):
                    mock_connect.return_value = None
                    nats_listener.nc = mock_nats_client

                    await nats_listener.start()

                    nats_listener.publisher.start.assert_called_once()

    async def test_subscribe_to_candle_data(self, nats_listener, mock_nats_client):
        """Test subscribing to candle data subjects."""
        nats_listener.nc = mock_nats_client

        await nats_listener._subscribe_to_candle_data()

        assert mock_nats_client.subscribe.call_count == 2

    async def test_handle_candle_message_not_leader(self, nats_listener):
        """Test handling message when not the leader."""
        nats_listener.leader_election = MagicMock()
        nats_listener.leader_election.is_current_leader.return_value = False

        mock_msg = MagicMock()
        mock_msg.subject = "binance.extraction.klines.BTCUSDT.15m"
        mock_msg.data = b'{"symbol": "BTCUSDT", "period": "15m"}'

        await nats_listener._handle_candle_message(mock_msg)

        # Should skip processing
        nats_listener.signal_engine.analyze_candles.assert_not_called()

    async def test_handle_candle_message_invalid_format(self, nats_listener):
        """Test handling message with invalid format."""
        nats_listener.leader_election = MagicMock()
        nats_listener.leader_election.is_current_leader.return_value = True

        mock_msg = MagicMock()
        mock_msg.subject = "test.subject"
        mock_msg.data = b'{"invalid": "data"}'  # Missing symbol and period

        await nats_listener._handle_candle_message(mock_msg)

        # Should log warning but not crash
        nats_listener.signal_engine.analyze_candles.assert_not_called()

    async def test_handle_candle_message_unsupported_symbol(self, nats_listener):
        """Test handling message with unsupported symbol."""
        nats_listener.leader_election = MagicMock()
        nats_listener.leader_election.is_current_leader.return_value = True

        mock_msg = MagicMock()
        mock_msg.subject = "test.subject"
        mock_msg.data = b'{"symbol": "UNSUPPORTED", "period": "15m"}'

        await nats_listener._handle_candle_message(mock_msg)

        nats_listener.signal_engine.analyze_candles.assert_not_called()

    async def test_handle_candle_message_unsupported_timeframe(self, nats_listener):
        """Test handling message with unsupported timeframe."""
        nats_listener.leader_election = MagicMock()
        nats_listener.leader_election.is_current_leader.return_value = True

        mock_msg = MagicMock()
        mock_msg.subject = "test.subject"
        mock_msg.data = b'{"symbol": "BTCUSDT", "period": "5m"}'

        await nats_listener._handle_candle_message(mock_msg)

        nats_listener.signal_engine.analyze_candles.assert_not_called()

    async def test_handle_candle_message_no_candle_data(self, nats_listener):
        """Test handling message when no candle data available."""
        nats_listener.leader_election = MagicMock()
        nats_listener.leader_election.is_current_leader.return_value = True

        with patch.object(
            nats_listener.mysql_client,
            "fetch_candles",
            return_value=pd.DataFrame(),
        ):
            mock_msg = MagicMock()
            mock_msg.subject = "test.subject"
            mock_msg.data = b'{"symbol": "BTCUSDT", "period": "15m"}'

            await nats_listener._handle_candle_message(mock_msg)

            nats_listener.signal_engine.analyze_candles.assert_not_called()

    async def test_handle_candle_message_with_signals(
        self, nats_listener, mock_signal_engine, mock_publisher
    ):
        """Test handling message and generating signals."""
        nats_listener.leader_election = MagicMock()
        nats_listener.leader_election.is_current_leader.return_value = True

        # Mock signal
        mock_signal = MagicMock()
        mock_signal.to_dict.return_value = {"symbol": "BTCUSDT", "action": "buy"}
        mock_signal_engine.analyze_candles.return_value = [mock_signal]

        # Mock candle data
        mock_df = pd.DataFrame(
            {
                "timestamp": ["2025-10-24T00:00:00Z"],
                "open": [50000.0],
                "high": [51000.0],
                "low": [49000.0],
                "close": [50500.0],
                "volume": [100.5],
            }
        )

        with patch.object(
            nats_listener.mysql_client, "fetch_candles", return_value=mock_df
        ):
            with patch.object(
                nats_listener.mysql_client, "persist_signals_batch", return_value=True
            ):
                mock_msg = MagicMock()
                mock_msg.subject = "test.subject"
                mock_msg.data = b'{"symbol": "BTCUSDT", "period": "15m"}'

                await nats_listener._handle_candle_message(mock_msg)

                mock_signal_engine.analyze_candles.assert_called_once()
                mock_publisher.publish_signals.assert_called_once()

    async def test_handle_candle_message_with_runtime_config(
        self, nats_listener, mock_signal_engine
    ):
        """Test handling message with runtime configuration."""
        nats_listener.leader_election = MagicMock()
        nats_listener.leader_election.is_current_leader.return_value = True

        # Mock app config manager
        mock_config_manager = AsyncMock()
        mock_config_manager.get_config.return_value = {
            "symbols": ["BTCUSDT"],
            "candle_periods": ["15m"],
            "enabled_strategies": ["momentum_pulse"],
            "min_confidence": 0.7,
            "max_confidence": 0.9,
            "version": 1,
        }
        nats_listener.app_config_manager = mock_config_manager

        mock_df = pd.DataFrame(
            {
                "timestamp": ["2025-10-24T00:00:00Z"],
                "open": [50000.0],
                "high": [51000.0],
                "low": [49000.0],
                "close": [50500.0],
                "volume": [100.5],
            }
        )

        with patch.object(
            nats_listener.mysql_client, "fetch_candles", return_value=mock_df
        ):
            mock_msg = MagicMock()
            mock_msg.subject = "test.subject"
            mock_msg.data = b'{"symbol": "BTCUSDT", "period": "15m"}'

            await nats_listener._handle_candle_message(mock_msg)

            # Verify runtime config was used
            call_kwargs = mock_signal_engine.analyze_candles.call_args[1]
            assert call_kwargs["enabled_strategies"] == ["momentum_pulse"]
            assert call_kwargs["min_confidence"] == 0.7

    async def test_stop(self, nats_listener, mock_nats_client):
        """Test stopping NATS listener."""
        nats_listener.nc = mock_nats_client

        with patch.object(nats_listener.publisher, "stop", new_callable=AsyncMock):
            with patch.object(
                nats_listener.mysql_client, "disconnect", new_callable=AsyncMock
            ):
                await nats_listener.stop()

                nats_listener.publisher.stop.assert_called_once()
                mock_nats_client.close.assert_called_once()
