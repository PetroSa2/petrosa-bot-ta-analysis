"""Acceptance tests for the TA observability contract (#348)."""

import json
import logging

from ta_bot.core.signal_engine import SignalEngine


def test_signal_metrics_use_catalog_names_and_bounded_labels():
    engine = SignalEngine()
    assert engine.signal_counter._name == "petrosa_ta_signals_total"
    assert engine.signal_latency._name == "petrosa_ta_cycle_duration_seconds"
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
        "event", "window_seconds", "service", "signals_by_outcome",
        "cycles", "latency_seconds",
    }
    assert "symbol" not in encoded
    assert "request_id" not in encoded
    assert not any(isinstance(value, (bytes, Exception)) for value in record.values())
    assert caplog.records == []


def test_summary_is_info_level(caplog):
    logger = logging.getLogger("ta_bot.services.nats_listener")
    with caplog.at_level(logging.INFO, logger=logger.name):
        logger.info(json.dumps({"event": "SUMMARY", "window_seconds": 300, "service": "petrosa-bot-ta-analysis"}))
    payload = json.loads(caplog.records[-1].message)
    assert payload["event"] == "SUMMARY"
    assert payload["window_seconds"] == 300
