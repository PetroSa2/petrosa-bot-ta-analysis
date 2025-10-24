"""
NATS Trace Context Propagation Helper.

This module provides utilities for injecting and extracting OpenTelemetry trace context
into/from NATS messages to enable distributed tracing across services.

Usage:
    # On publisher side:
    message_dict = NATSTracePropagator.inject_context(message_dict)

    # On consumer side:
    ctx = NATSTracePropagator.extract_context(message_dict)
    with tracer.start_as_current_span("process_message", context=ctx):
        process_message(message_dict)
"""

from typing import Any

from opentelemetry import trace
from opentelemetry.context import Context
from opentelemetry.propagate import extract, get_global_textmap, inject
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator


class NATSTracePropagator:
    """Helper for injecting and extracting trace context in NATS messages."""

    # Reserved field name for trace headers in message payload
    TRACE_HEADERS_FIELD = "_otel_trace_headers"

    @staticmethod
    def inject_context(message_dict: dict[str, Any]) -> dict[str, Any]:
        """
        Inject current OpenTelemetry trace context into message dictionary.

        This extracts the current span context and injects it as W3C TraceContext headers
        into a reserved field in the message payload. The message is modified in place
        and also returned for convenience.

        Args:
            message_dict: Message dictionary to inject trace context into

        Returns:
            The same message dictionary with trace context injected

        Example:
            >>> signal_data = {"symbol": "BTCUSDT", "action": "BUY"}
            >>> signal_data = NATSTracePropagator.inject_context(signal_data)
            >>> print(signal_data)
            {
                "symbol": "BTCUSDT",
                "action": "BUY",
                "_otel_trace_headers": {
                    "traceparent": "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01",
                    "tracestate": ""
                }
            }
        """
        # Create a carrier dict to hold the propagated context
        carrier: dict[str, str] = {}

        # Inject current trace context into carrier
        # This uses the global propagator (TraceContext by default)
        inject(carrier)

        # Add carrier to message if it contains any context
        if carrier:
            message_dict[NATSTracePropagator.TRACE_HEADERS_FIELD] = carrier

        return message_dict

    @staticmethod
    def extract_context(message_dict: dict[str, Any]) -> Context:
        """
        Extract OpenTelemetry trace context from message dictionary.

        This extracts the W3C TraceContext headers from the reserved field in the message
        payload and returns an OpenTelemetry Context object that can be used to create
        child spans that continue the distributed trace.

        Args:
            message_dict: Message dictionary containing trace context

        Returns:
            OpenTelemetry Context with extracted trace information.
            If no trace context is found, returns an empty context.

        Example:
            >>> message_dict = {
            ...     "symbol": "BTCUSDT",
            ...     "_otel_trace_headers": {
            ...         "traceparent": "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01"
            ...     },
            ... }
            >>> ctx = NATSTracePropagator.extract_context(message_dict)
            >>> tracer = trace.get_tracer(__name__)
            >>> with tracer.start_as_current_span("process_signal", context=ctx):
            ...     process_signal(message_dict)
        """
        # Get trace headers from message
        carrier = message_dict.get(NATSTracePropagator.TRACE_HEADERS_FIELD, {})

        # Extract context from carrier
        # If carrier is empty, this returns an empty context
        ctx = extract(carrier)

        return ctx

    @staticmethod
    def has_trace_context(message_dict: dict[str, Any]) -> bool:
        """
        Check if message contains trace context.

        Args:
            message_dict: Message dictionary to check

        Returns:
            True if message contains trace context, False otherwise

        Example:
            >>> message_dict = {"symbol": "BTCUSDT"}
            >>> NATSTracePropagator.has_trace_context(message_dict)
            False
            >>> message_dict = NATSTracePropagator.inject_context(message_dict)
            >>> NATSTracePropagator.has_trace_context(message_dict)
            True
        """
        return NATSTracePropagator.TRACE_HEADERS_FIELD in message_dict and bool(
            message_dict[NATSTracePropagator.TRACE_HEADERS_FIELD]
        )

    @staticmethod
    def remove_trace_context(message_dict: dict[str, Any]) -> dict[str, Any]:
        """
        Remove trace context from message dictionary.

        Useful for cleaning up message before final processing or storage
        if you don't want to persist the trace headers.

        Args:
            message_dict: Message dictionary to clean

        Returns:
            The same message dictionary with trace context removed

        Example:
            >>> message_dict = {"symbol": "BTCUSDT", "_otel_trace_headers": {...}}
            >>> message_dict = NATSTracePropagator.remove_trace_context(message_dict)
            >>> print(message_dict)
            {"symbol": "BTCUSDT"}
        """
        message_dict.pop(NATSTracePropagator.TRACE_HEADERS_FIELD, None)
        return message_dict


# Convenience functions for backward compatibility
inject_trace_context = NATSTracePropagator.inject_context
extract_trace_context = NATSTracePropagator.extract_context
has_trace_context = NATSTracePropagator.has_trace_context
remove_trace_context = NATSTracePropagator.remove_trace_context
