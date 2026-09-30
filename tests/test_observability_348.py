"""Acceptance tests for the TA observability contract (#348)."""

import json
import logging
from unittest.mock import AsyncMock

import pytest

from ta_bot.core.signal_engine import SignalEngine


def test_signal_metrics_use_catalog_names_and_bounded_labels():
    engine = SignalEngine()
    assert engine.signal_counter._name == "petrosa_ta_signals_total"
    assert engine.signal_latency._name == "petrosa_ta_cycle_duration_seconds"


def test_summary_shape_has_300_second_window_and_no_unbounded_fields(caplog):
    engine = SignalEngine()
    summary = engine.metrics_summary()
    record = {
        "event": "SUMMARY",
        "window_seconds": 300,
        "service": "petrosa-bot-ta-analysis",
        **summary,
    }
    encoded = json.dumps(record)
    assert record["window_seconds"] == 300
    assert set(record) == {
        "event",
        "window_seconds",
        "service",
        "signals_by_strategy_outcome",
        "signals_by_outcome",
        "cycles",
        "latency_seconds",
    }
    assert "symbol" not in encoded
    assert "request_id" not in encoded
    assert not any(isinstance(value, (bytes, Exception)) for value in record.values())
    assert caplog.records == []


def test_summary_is_info_level(caplog):
    logger = logging.getLogger("ta_bot.services.nats_listener")
    with caplog.at_level(logging.INFO, logger=logger.name):
        logger.info(
            json.dumps(
                {
                    "event": "SUMMARY",
                    "window_seconds": 300,
                    "service": "petrosa-bot-ta-analysis",
                }
            )
        )
    payload = json.loads(caplog.records[-1].message)
    assert payload["event"] == "SUMMARY"
    assert payload["window_seconds"] == 300


@pytest.mark.parametrize("kwargs", [{"min_confidence": 0.5}, {"max_confidence": 0.5}])
def test_expected_confidence_filter_is_debug(kwargs, monkeypatch, caplog):
    from types import SimpleNamespace

    import pandas as pd

    engine = SignalEngine()
    engine.strategies = {"demo": object()}
    engine._calculate_indicators = lambda df: {}
    engine._run_strategy = lambda *args, **args_kwargs: SimpleNamespace(
        confidence=0.1 if "min_confidence" in kwargs else 0.9
    )
    with caplog.at_level(logging.DEBUG, logger="ta_bot.core.signal_engine"):
        result = engine.analyze_candles(
            pd.DataFrame({"close": [1.0]}), "BTCUSDT", "15m", **kwargs
        )
    assert result == []
    assert any(record.levelno == logging.DEBUG for record in caplog.records)


def test_empty_input_is_expected_debug_skip():
    import pandas as pd

    engine = SignalEngine()
    assert engine.analyze_candles(pd.DataFrame(), "BTCUSDT", "15m") == []
    assert engine.metrics_summary()["signals_by_outcome"]["no_data"] == 1


@pytest.mark.asyncio
async def test_listener_skips_expected_inputs_and_emits_summary(caplog):
    from unittest.mock import MagicMock

    import pandas as pd

    from ta_bot.services.nats_listener import NATSListener

    engine = MagicMock()
    engine.metrics_summary.return_value = {
        "signals_by_outcome": {},
        "signals_by_strategy_outcome": {},
        "cycles": 0,
        "latency_seconds": {"p50": 0, "p95": 0},
    }
    listener = NATSListener("nats://localhost", engine, MagicMock())
    with caplog.at_level(logging.DEBUG, logger="ta_bot.services.nats_listener"):
        await listener._process_symbol_extraction("UNKNOWN", "15m")
        await listener._process_symbol_extraction("BTCUSDT", "unknown")
        listener.data_manager_gateway.fetch_candles = AsyncMock(
            return_value=pd.DataFrame()
        )
        await listener._process_symbol_extraction("BTCUSDT", "15m")
        listener._emit_summary_if_due(force=True)
    assert any("SUMMARY" in record.message for record in caplog.records)
    assert any("Skipping unsupported" in record.message for record in caplog.records)
