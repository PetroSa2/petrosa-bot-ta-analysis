#!/usr/bin/env python3

import sys
import os

# Add the project root to the path so we can import the module
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from ta_bot.utils.nats_trace_propagator import NATSTracePropagator

def setup_tracing():
    """Set up OpenTelemetry tracing with in-memory exporter for testing."""
    # Force creation of a new tracer provider for clean test environment
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    tracer = trace.get_tracer(__name__)
    return tracer, exporter

def main():
    print("Setting up tracing...")
    tracer, exporter = setup_tracing()
    
    print("Creating a span and testing inject_context...")
    with tracer.start_as_current_span("test_span"):
        message = {"symbol": "BTCUSDT", "action": "BUY"}
        print(f"Original message: {message}")
        
        result = NATSTracePropagator.inject_context(message)
        print(f"Message after inject_context: {result}")
        
        # Check if trace headers were added
        if NATSTracePropagator.TRACE_HEADERS_FIELD in result:
            print("SUCCESS: Trace headers field was added")
            trace_headers = result[NATSTracePropagator.TRACE_HEADERS_FIELD]
            print(f"Trace headers: {trace_headers}")
            
            if "traceparent" in trace_headers:
                print("SUCCESS: traceparent found in headers")
                traceparent = trace_headers["traceparent"]
                parts = traceparent.split("-")
                print(f"Traceparent parts: {parts}")
                
                if len(parts) == 4 and parts[0] == "00" and len(parts[1]) == 32 and len(parts[2]) == 16:
                    print("SUCCESS: traceparent format is correct")
                else:
                    print("ERROR: traceparent format is incorrect")
            else:
                print("ERROR: traceparent not found in headers")
        else:
            print("ERROR: Trace headers field was not added")
            print("Checking carrier contents from debug output...")
    
    print("\nTesting without active span...")
    message2 = {"symbol": "ETHUSDT", "action": "SELL"}
    print(f"Original message: {message2}")
    
    result2 = NATSTracePropagator.inject_context(message2)
    print(f"Message after inject_context: {result2}")
    
    if NATSTracePropagator.TRACE_HEADERS_FIELD in result2:
        print("Trace headers field was added even without active span")
    else:
        print("No trace headers field added when no active span")

if __name__ == "__main__":
    main()
