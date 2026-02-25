# ruff: noqa
import os

os.environ[
    "OTEL_PYTHON_DISABLED_INSTRUMENTATIONS"
] = "true"  # Disable auto-instrumentation for clean test

from opentelemetry import trace  # noqa: E402
from opentelemetry.propagate import extract, inject  # noqa: E402
from opentelemetry.sdk.trace import TracerProvider  # noqa: E402
from opentelemetry.sdk.trace.export import SimpleSpanProcessor  # noqa: E402
from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
    InMemorySpanExporter,  # noqa: E402
)

from ta_bot.utils.nats_trace_propagator import NATSTracePropagator  # noqa: E402

# Set up tracing
exporter = InMemorySpanExporter()
provider = TracerProvider()
provider.add_span_processor(SimpleSpanProcessor(exporter))
trace.set_tracer_provider(provider)
tracer = trace.get_tracer(__name__)

# Test the inject_context method directly
print("Testing NATSTracePropagator.inject_context...")

message = {"symbol": "BTCUSDT", "action": "BUY"}
print(f"Original message: {message}")

# Test without active span
result1 = NATSTracePropagator.inject_context(message.copy())
print(f"After inject_context (no active span): {result1}")

# Test with active span
with tracer.start_as_current_span("test_span"):
    message2 = {"symbol": "BTCUSDT", "action": "BUY"}
    result2 = NATSTracePropagator.inject_context(message2)
    print(f"After inject_context (with active span): {result2}")
    print(f"Has trace context: {NATSTracePropagator.has_trace_context(result2)}")
