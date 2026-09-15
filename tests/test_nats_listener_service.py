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

    async def test_handle_candle_message_persist_fails(
        self, nats_listener, mock_signal_engine, mock_publisher
    ):
        """Test that persist failure is logged and publishing still proceeds (line 268)."""
        mock_signal = MagicMock()
        mock_signal.to_dict.return_value = {"symbol": "BTCUSDT", "action": "buy"}
        mock_signal_engine.analyze_candles.return_value = [mock_signal]

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
                nats_listener.mysql_client,
                "persist_signals_batch",
                return_value=False,
            ):
                mock_msg = MagicMock()
                mock_msg.subject = "test.subject"
                mock_msg.data = b'{"symbol": "BTCUSDT", "period": "15m"}'

                await nats_listener._handle_candle_message(mock_msg)

                # Even on persist failure, publishing should still be attempted
                mock_publisher.publish_signals.assert_called_once()

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

    async def test_get_health_metrics(self, nats_listener):
        """get_health_metrics exposes the evaluator signal snapshot (#248)."""
        nats_listener.publisher.nats_client = MagicMock()
        nats_listener.publisher.nats_client.is_connected = True
        nats_listener.signals_emitted = 7
        nats_listener._mysql_healthy = True
        nats_listener._recent_analysis_latencies.extend([1.0, 3.0])

        metrics = nats_listener.get_health_metrics()

        assert metrics["nats_connected"] is True
        assert metrics["mysql_healthy"] is True
        assert metrics["signals_emitted"] == 7
        assert metrics["analysis_latency_s"] == 2.0

    async def test_get_health_metrics_no_nats(self, nats_listener):
        """get_health_metrics reports disconnected when no NATS client (#248)."""
        nats_listener.publisher.nats_client = None
        metrics = nats_listener.get_health_metrics()
        assert metrics["nats_connected"] is False
        assert metrics["analysis_latency_s"] == 0.0

    async def test_get_health_metrics_no_messages_yet(self, nats_listener):
        """#265: before start()/first message, proof-of-life fields are zero/None."""
        metrics = nats_listener.get_health_metrics()
        assert metrics["messages_received"] == 0
        assert metrics["seconds_since_start"] == 0.0
        assert metrics["seconds_since_last_message"] is None

    async def test_handle_candle_message_increments_messages_received(
        self, nats_listener
    ):
        """#265: every inbound message increments the proof-of-life counter,
        even when it's later dropped for an unsupported symbol/timeframe."""
        assert nats_listener.messages_received == 0

        mock_msg = MagicMock()
        mock_msg.subject = "test.subject"
        mock_msg.data = b'{"symbol": "UNSUPPORTED", "period": "15m"}'
        await nats_listener._handle_candle_message(mock_msg)

        assert nats_listener.messages_received == 1
        assert nats_listener.get_health_metrics()["messages_received"] == 1
        assert nats_listener.get_health_metrics()["seconds_since_last_message"] >= 0

    async def test_start_sets_started_at(self, nats_listener, mock_nats_client):
        """#265: start() records a monotonic start timestamp for staleness checks."""
        assert nats_listener._started_at is None
        with patch("nats.aio.client.Client.connect", new_callable=AsyncMock):
            with patch.object(
                nats_listener.mysql_client, "connect", new_callable=AsyncMock
            ):
                with patch.object(
                    nats_listener.publisher, "start", new_callable=AsyncMock
                ):
                    nats_listener.nc = mock_nats_client
                    await nats_listener.start()

        assert nats_listener._started_at is not None
        assert nats_listener.get_health_metrics()["seconds_since_start"] >= 0

    async def test_process_extraction_fetch_failure_sets_unhealthy(self, nats_listener):
        """A candle-fetch exception flips mysql_healthy to False (#248)."""
        nats_listener._mysql_healthy = True
        with patch.object(
            nats_listener.mysql_client,
            "fetch_candles",
            new_callable=AsyncMock,
            side_effect=RuntimeError("db down"),
        ):
            await nats_listener._process_symbol_extraction("BTCUSDT", "15m")

        assert nats_listener._mysql_healthy is False

    async def test_process_extraction_success_tracks_signals(self, nats_listener):
        """A successful extraction records latency and increments signals_emitted (#248)."""
        df = pd.DataFrame({"close": [1.0, 2.0, 3.0]})
        sig = MagicMock()
        sig.to_dict.return_value = {"strategy_id": "s", "action": "buy"}
        nats_listener.signal_engine.analyze_candles.return_value = [sig]
        nats_listener.publisher.publish_signals = AsyncMock()

        with patch.object(
            nats_listener.mysql_client,
            "fetch_candles",
            new_callable=AsyncMock,
            return_value=df,
        ):
            with patch.object(
                nats_listener.mysql_client,
                "persist_signals_batch",
                new_callable=AsyncMock,
                return_value=True,
            ):
                await nats_listener._process_symbol_extraction("BTCUSDT", "15m")

        assert nats_listener._mysql_healthy is True
        assert nats_listener.signals_emitted == 1
        assert len(nats_listener._recent_analysis_latencies) == 1


@pytest.mark.asyncio
class TestResolveStrategyConfigs:
    """Tests for `_resolve_strategy_configs` (#283): the async, pre-executor
    resolution step that feeds `SignalEngine.analyze_candles(strategy_configs=...)`."""

    async def test_returns_none_when_no_strategy_config_manager_wired(
        self, nats_listener
    ):
        """Default/production-today state: no StrategyConfigManager wired ->
        None, so SignalEngine falls back to defaults.py for every strategy."""
        assert nats_listener.strategy_config_manager is None
        result = await nats_listener._resolve_strategy_configs("BTCUSDT", None)
        assert result is None

    async def test_resolves_config_per_strategy_via_manager(
        self, mock_signal_engine, mock_publisher
    ):
        """With a manager wired, resolves one get_config() call per target
        strategy and returns a dict keyed by strategy_id."""
        mock_signal_engine.strategies = {"rsi_extreme_reversal": object()}
        mock_manager = AsyncMock()
        mock_manager.get_config.return_value = {
            "parameters": {"base_confidence": 0.9},
            "version": 1,
            "source": "mongodb",
            "is_override": True,
        }
        listener = NATSListener(
            nats_url="nats://test:4222",
            signal_engine=mock_signal_engine,
            publisher=mock_publisher,
            strategy_config_manager=mock_manager,
        )

        result = await listener._resolve_strategy_configs(
            "BTCUSDT", ["rsi_extreme_reversal"]
        )

        assert result == {
            "rsi_extreme_reversal": {
                "parameters": {"base_confidence": 0.9},
                "version": 1,
                "source": "mongodb",
                "is_override": True,
            }
        }
        mock_manager.get_config.assert_awaited_once_with(
            "rsi_extreme_reversal", "BTCUSDT"
        )

    async def test_defaults_to_all_signal_engine_strategies_when_unfiltered(
        self, mock_signal_engine, mock_publisher
    ):
        """When `enabled_strategies` is None (no runtime filter), every
        strategy SignalEngine knows about is resolved."""
        mock_signal_engine.strategies = {"strategy_a": object(), "strategy_b": object()}
        mock_manager = AsyncMock()
        mock_manager.get_config.return_value = {
            "parameters": {},
            "version": 1,
            "source": "default",
            "is_override": False,
        }
        listener = NATSListener(
            nats_url="nats://test:4222",
            signal_engine=mock_signal_engine,
            publisher=mock_publisher,
            strategy_config_manager=mock_manager,
        )

        result = await listener._resolve_strategy_configs("BTCUSDT", None)

        assert set(result.keys()) == {"strategy_a", "strategy_b"}
        assert mock_manager.get_config.await_count == 2

    async def test_one_strategy_failure_does_not_block_the_others(
        self, mock_signal_engine, mock_publisher
    ):
        """A single strategy's config resolution raising must not abort the
        others in the same cycle, and must not propagate -- that strategy
        simply falls back to defaults.py inside SignalEngine."""
        mock_signal_engine.strategies = {
            "good_strategy": object(),
            "bad_strategy": object(),
        }

        async def _get_config(strategy_id, symbol):
            if strategy_id == "bad_strategy":
                raise RuntimeError("mongo timeout")
            return {
                "parameters": {"base_confidence": 0.5},
                "version": 1,
                "source": "mongodb",
                "is_override": True,
            }

        mock_manager = AsyncMock()
        mock_manager.get_config.side_effect = _get_config
        listener = NATSListener(
            nats_url="nats://test:4222",
            signal_engine=mock_signal_engine,
            publisher=mock_publisher,
            strategy_config_manager=mock_manager,
        )

        result = await listener._resolve_strategy_configs("BTCUSDT", None)

        assert "good_strategy" in result
        assert "bad_strategy" not in result
