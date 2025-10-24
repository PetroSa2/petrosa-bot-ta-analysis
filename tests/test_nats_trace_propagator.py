"""
Unit tests for NATS trace context propagation helper.

Tests the injection and extraction of OpenTelemetry trace context into/from NATS messages.
"""

import pytest
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from ta_bot.utils.nats_trace_propagator import NATSTracePropagator


@pytest.fixture
def setup_tracing():
    """Set up OpenTelemetry tracing with in-memory exporter for testing."""
    # Create in-memory exporter to capture spans
    exporter = InMemorySpanExporter()

    # Create test-specific tracer provider
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))

    # Get tracer directly from test provider (don't set as global)
    tracer = provider.get_tracer(__name__)

    yield tracer, exporter

    # Cleanup
    exporter.clear()


class TestNATSTracePropagatorBasic:
    """Basic functionality tests for NATSTracePropagator."""

    def test_inject_context_adds_trace_headers_field(self, setup_tracing):
        """Test that inject_context adds _otel_trace_headers field to message."""
        tracer, _ = setup_tracing

        # Create a span to establish trace context
        with tracer.start_as_current_span("test_span"):
            message = {"symbol": "BTCUSDT", "action": "BUY"}
            result = NATSTracePropagator.inject_context(message)

            # Verify trace headers field was added
            assert NATSTracePropagator.TRACE_HEADERS_FIELD in result
            assert isinstance(result[NATSTracePropagator.TRACE_HEADERS_FIELD], dict)

            # Verify original fields are preserved
            assert result["symbol"] == "BTCUSDT"
            assert result["action"] == "BUY"

    def test_inject_context_contains_traceparent(self, setup_tracing):
        """Test that injected context contains W3C traceparent header."""
        tracer, _ = setup_tracing

        with tracer.start_as_current_span("test_span"):
            message = {"symbol": "BTCUSDT"}
            result = NATSTracePropagator.inject_context(message)

            trace_headers = result[NATSTracePropagator.TRACE_HEADERS_FIELD]

            # Verify traceparent header is present
            assert "traceparent" in trace_headers

            # Verify traceparent format (00-{trace_id}-{span_id}-{flags})
            traceparent = trace_headers["traceparent"]
            parts = traceparent.split("-")
            assert len(parts) == 4
            assert parts[0] == "00"  # version
            assert len(parts[1]) == 32  # trace_id (128 bits = 32 hex chars)
            assert len(parts[2]) == 16  # span_id (64 bits = 16 hex chars)
            assert parts[3] in ["00", "01"]  # trace-flags

    def test_inject_context_modifies_in_place(self, setup_tracing):
        """Test that inject_context modifies the message dict in place."""
        tracer, _ = setup_tracing

        with tracer.start_as_current_span("test_span"):
            message = {"symbol": "BTCUSDT"}
            result = NATSTracePropagator.inject_context(message)

            # Verify same object reference
            assert result is message
            assert NATSTracePropagator.TRACE_HEADERS_FIELD in message

    def test_extract_context_from_injected_message(self, setup_tracing):
        """Test that extract_context successfully retrieves injected context."""
        tracer, _ = setup_tracing

        # Inject context
        with tracer.start_as_current_span("parent_span") as parent_span:
            parent_trace_id = parent_span.get_span_context().trace_id

            message = {"symbol": "BTCUSDT"}
            NATSTracePropagator.inject_context(message)

        # Extract context
        extracted_ctx = NATSTracePropagator.extract_context(message)

        # Create child span using extracted context
        with tracer.start_as_current_span(
            "child_span", context=extracted_ctx
        ) as child_span:
            child_trace_id = child_span.get_span_context().trace_id

            # Verify trace IDs match (same distributed trace)
            assert child_trace_id == parent_trace_id

    def test_extract_context_from_empty_message(self, setup_tracing):
        """Test that extract_context returns empty context when no trace headers present."""
        message = {"symbol": "BTCUSDT"}

        # Extract from message without trace context
        ctx = NATSTracePropagator.extract_context(message)

        # Verify it returns a valid context (but empty/invalid)
        assert ctx is not None

        # Span created from empty context should have new trace ID
        tracer, _ = setup_tracing
        with tracer.start_as_current_span("new_span", context=ctx) as span:
            # This is a root span (no parent)
            assert span.get_span_context().span_id != 0

    def test_has_trace_context_returns_true_after_injection(self, setup_tracing):
        """Test that has_trace_context returns True after injecting context."""
        tracer, _ = setup_tracing

        with tracer.start_as_current_span("test_span"):
            message = {"symbol": "BTCUSDT"}

            # Before injection
            assert NATSTracePropagator.has_trace_context(message) is False

            # After injection
            NATSTracePropagator.inject_context(message)
            assert NATSTracePropagator.has_trace_context(message) is True

    def test_has_trace_context_returns_false_for_empty_message(self):
        """Test that has_trace_context returns False for message without trace headers."""
        message = {"symbol": "BTCUSDT"}
        assert NATSTracePropagator.has_trace_context(message) is False

    def test_remove_trace_context_removes_headers(self, setup_tracing):
        """Test that remove_trace_context removes trace headers field."""
        tracer, _ = setup_tracing

        with tracer.start_as_current_span("test_span"):
            message = {"symbol": "BTCUSDT"}
            NATSTracePropagator.inject_context(message)

            # Verify trace context exists
            assert NATSTracePropagator.has_trace_context(message) is True

            # Remove trace context
            result = NATSTracePropagator.remove_trace_context(message)

            # Verify trace context is gone
            assert NATSTracePropagator.has_trace_context(result) is False
            assert NATSTracePropagator.TRACE_HEADERS_FIELD not in result

            # Verify other fields preserved
            assert result["symbol"] == "BTCUSDT"


class TestNATSTracePropagatorEdgeCases:
    """Edge case and error handling tests."""

    def test_inject_context_with_existing_trace_headers(self, setup_tracing):
        """Test that inject_context overwrites existing trace headers."""
        tracer, _ = setup_tracing

        # Message with fake trace headers
        message = {
            "symbol": "BTCUSDT",
            "_otel_trace_headers": {"traceparent": "fake-trace-id"},
        }

        with tracer.start_as_current_span("test_span"):
            NATSTracePropagator.inject_context(message)

            # Verify headers were overwritten with valid ones
            trace_headers = message[NATSTracePropagator.TRACE_HEADERS_FIELD]
            assert "traceparent" in trace_headers
            assert trace_headers["traceparent"] != "fake-trace-id"

    def test_extract_context_with_malformed_headers(self):
        """Test that extract_context handles malformed trace headers gracefully."""
        message = {
            "symbol": "BTCUSDT",
            "_otel_trace_headers": {"traceparent": "invalid-format"},
        }

        # Should not raise exception
        ctx = NATSTracePropagator.extract_context(message)
        assert ctx is not None

    def test_has_trace_context_with_empty_headers_dict(self):
        """Test that has_trace_context returns False for empty headers dict."""
        message = {"symbol": "BTCUSDT", "_otel_trace_headers": {}}

        # Empty headers dict should return False
        assert NATSTracePropagator.has_trace_context(message) is False

    def test_remove_trace_context_on_message_without_headers(self):
        """Test that remove_trace_context handles message without headers."""
        message = {"symbol": "BTCUSDT"}

        # Should not raise exception
        result = NATSTracePropagator.remove_trace_context(message)

        assert result is message
        assert "symbol" in result


class TestNATSTracePropagatorIntegration:
    """Integration tests simulating real message flow."""

    def test_end_to_end_trace_propagation(self, setup_tracing):
        """Test complete flow: inject on publisher, extract on consumer."""
        tracer, exporter = setup_tracing

        # Simulate publisher side
        with tracer.start_as_current_span("publish_signal") as publish_span:
            publisher_trace_id = publish_span.get_span_context().trace_id

            # Create signal message
            signal_message = {
                "symbol": "BTCUSDT",
                "action": "BUY",
                "strategy": "RSI_EXTREME",
                "timestamp": "2024-10-24T18:00:00Z",
            }

            # Inject trace context (publisher side)
            NATSTracePropagator.inject_context(signal_message)

        # Simulate NATS transmission (message is serialized/deserialized)
        # In real scenario: json.dumps() -> NATS -> json.loads()
        import json

        serialized = json.dumps(signal_message)
        received_message = json.loads(serialized)

        # Simulate consumer side
        extracted_ctx = NATSTracePropagator.extract_context(received_message)

        with tracer.start_as_current_span(
            "consume_signal", context=extracted_ctx
        ) as consume_span:
            consumer_trace_id = consume_span.get_span_context().trace_id

            # Verify trace IDs match (distributed trace maintained)
            assert consumer_trace_id == publisher_trace_id

        # Verify spans were exported (check after spans are finished)
        spans = exporter.get_finished_spans()
        assert len(spans) >= 1  # At least one span captured

        # Verify all spans have same trace ID
        trace_ids = {span.context.trace_id for span in spans}
        assert len(trace_ids) == 1  # All spans share same trace ID
        assert publisher_trace_id in trace_ids  # Verify our trace ID is present

    def test_multi_service_trace_propagation(self, setup_tracing):
        """Test trace propagation across multiple service hops."""
        tracer, exporter = setup_tracing

        trace_ids = []

        # Service 1: socket-client (data ingestion)
        with tracer.start_as_current_span("socket_client_receive") as span1:
            trace_ids.append(span1.get_span_context().trace_id)

            message = {"symbol": "BTCUSDT", "price": 50000}
            NATSTracePropagator.inject_context(message)

        # Service 2: ta-bot (signal generation)
        ctx2 = NATSTracePropagator.extract_context(message)
        with tracer.start_as_current_span("ta_bot_analyze", context=ctx2) as span2:
            trace_ids.append(span2.get_span_context().trace_id)

            signal = {"symbol": "BTCUSDT", "action": "BUY"}
            NATSTracePropagator.inject_context(signal)

        # Service 3: tradeengine (order execution)
        ctx3 = NATSTracePropagator.extract_context(signal)
        with tracer.start_as_current_span("tradeengine_execute", context=ctx3) as span3:
            trace_ids.append(span3.get_span_context().trace_id)

        # Verify all services share same trace ID
        assert len(set(trace_ids)) == 1  # All same trace ID

        # Verify span hierarchy
        spans = exporter.get_finished_spans()
        assert len(spans) == 3

    def test_message_without_trace_creates_new_trace(self, setup_tracing):
        """Test that consuming message without trace context creates new trace."""
        tracer, _ = setup_tracing

        # Message without trace context (e.g., from external source)
        message = {"symbol": "BTCUSDT", "price": 50000}

        # Consumer tries to extract context
        ctx = NATSTracePropagator.extract_context(message)

        # Create span with extracted context (should be new trace)
        with tracer.start_as_current_span("process_external", context=ctx) as span1:
            trace_id_1 = span1.get_span_context().trace_id

        # Compare with a separately created span
        with tracer.start_as_current_span("another_span") as span2:
            trace_id_2 = span2.get_span_context().trace_id

        # Both should be independent traces
        assert trace_id_1 != trace_id_2


class TestConvenienceFunctions:
    """Test convenience function aliases."""

    def test_convenience_functions_exist(self):
        """Test that convenience function aliases are available."""
        from ta_bot.utils.nats_trace_propagator import (
            extract_trace_context,
            has_trace_context,
            inject_trace_context,
            remove_trace_context,
        )

        # Verify functions exist
        assert callable(inject_trace_context)
        assert callable(extract_trace_context)
        assert callable(has_trace_context)
        assert callable(remove_trace_context)

    def test_convenience_functions_work(self, setup_tracing):
        """Test that convenience functions work correctly."""
        from ta_bot.utils.nats_trace_propagator import (
            extract_trace_context,
            has_trace_context,
            inject_trace_context,
        )

        tracer, _ = setup_tracing

        with tracer.start_as_current_span("test_span"):
            message = {"symbol": "BTCUSDT"}

            # Use convenience functions
            inject_trace_context(message)
            assert has_trace_context(message) is True

            ctx = extract_trace_context(message)
            assert ctx is not None
