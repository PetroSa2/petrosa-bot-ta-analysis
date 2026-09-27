from unittest.mock import MagicMock

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
