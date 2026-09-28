from unittest.mock import AsyncMock, MagicMock

import pandas as pd
import pytest

from ta_bot.services.nats_listener import NATSListener


def test_health_metrics_emit_new_and_deprecated_candle_keys():
    listener = NATSListener(
        nats_url="nats://localhost",
        signal_engine=MagicMock(),
        publisher=MagicMock(),
    )
    listener._candles_source_healthy = False

    metrics = listener.get_health_metrics()

    assert metrics["candles_source_healthy"] is False
    assert metrics["mysql_healthy"] is False


@pytest.mark.asyncio
async def test_start_connects_data_manager_gateway():
    listener = NATSListener(
        nats_url="nats://localhost",
        signal_engine=MagicMock(),
        publisher=MagicMock(),
    )
    listener.nc.connect = AsyncMock()
    listener.data_manager_gateway.connect = AsyncMock()
    listener.publisher.start = AsyncMock()
    listener._subscribe_to_candle_data = AsyncMock()

    await listener.start()

    listener.data_manager_gateway.connect.assert_awaited_once_with()


@pytest.mark.asyncio
async def test_failed_candle_fetch_marks_data_manager_health_degraded():
    listener = NATSListener(
        nats_url="nats://localhost",
        signal_engine=MagicMock(),
        publisher=MagicMock(),
    )
    listener.data_manager_gateway.fetch_candles = AsyncMock(
        side_effect=RuntimeError("data-manager unavailable")
    )

    await listener._process_symbol_extraction("BTCUSDT", "15m")

    assert listener.get_health_metrics()["candles_source_healthy"] is False


@pytest.mark.asyncio
async def test_successful_candle_fetch_persists_and_publishes_signals():
    signal = MagicMock()
    signal.to_dict.return_value = {"id": "signal-1"}
    listener = NATSListener(
        nats_url="nats://localhost",
        signal_engine=MagicMock(),
        publisher=MagicMock(),
    )
    listener.data_manager_gateway.fetch_candles = AsyncMock(
        return_value=pd.DataFrame({"close": [100.0]})
    )
    listener.data_manager_gateway.persist_signals_batch = AsyncMock(return_value=True)
    listener.signal_engine.analyze_candles.return_value = [signal]
    listener.publisher.publish_signals = AsyncMock()

    await listener._process_symbol_extraction("BTCUSDT", "15m")

    assert listener.get_health_metrics()["candles_source_healthy"] is True
    listener.data_manager_gateway.persist_signals_batch.assert_awaited_once_with(
        [{"id": "signal-1"}]
    )
    listener.publisher.publish_signals.assert_awaited_once_with([signal])
