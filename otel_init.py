"""
OpenTelemetry initialization for the TA Bot service.

This module sets up OpenTelemetry instrumentation for observability
and monitoring of the technical analysis bot service.
"""

import logging
import os
from typing import Optional

from opentelemetry import metrics, trace
from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.aiohttp_client import AioHttpClientInstrumentor
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.instrumentation.urllib3 import URLLib3Instrumentor
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

# Module-level logger
logger = logging.getLogger(__name__)

# Global logger provider for attaching handlers
_global_logger_provider = None
_otlp_logging_handler = None


def setup_telemetry(
    service_name: str = "ta-bot",
    service_version: str | None = None,
    otlp_endpoint: str | None = None,
    enable_metrics: bool = True,
    enable_traces: bool = True,
    enable_logs: bool = True,
) -> None:
    """
    Set up OpenTelemetry instrumentation.

    Args:
        service_name: Name of the service
        service_version: Version of the service
        otlp_endpoint: OTLP endpoint URL
        enable_metrics: Whether to enable metrics
        enable_traces: Whether to enable traces
        enable_logs: Whether to enable logs
    """
    # Early return if OTEL disabled
    if os.getenv("ENABLE_OTEL", "true").lower() not in ("true", "1", "yes"):
        return

    # Get configuration from environment variables
    service_version = service_version or os.getenv("OTEL_SERVICE_VERSION", "1.0.0")
    otlp_endpoint = otlp_endpoint or os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    enable_metrics = enable_metrics and os.getenv("ENABLE_METRICS", "true").lower() in (
        "true",
        "1",
        "yes",
    )
    enable_traces = enable_traces and os.getenv("ENABLE_TRACES", "true").lower() in (
        "true",
        "1",
        "yes",
    )
    enable_logs = enable_logs and os.getenv("ENABLE_LOGS", "true").lower() in (
        "true",
        "1",
        "yes",
    )

    # Create resource attributes
    resource_attributes = {
        "service.name": service_name,
        "service.version": service_version,
        "service.instance.id": os.getenv("HOSTNAME", "unknown"),
        "deployment.environment": os.getenv("ENVIRONMENT", "production"),
    }

    # Add custom resource attributes if provided
    custom_attributes = os.getenv("OTEL_RESOURCE_ATTRIBUTES")
    if custom_attributes:
        for attr in custom_attributes.split(","):
            if "=" in attr:
                key, value = attr.split("=", 1)
                resource_attributes[key.strip()] = value.strip()

    resource = Resource.create(resource_attributes)

    # Set up tracing if enabled
    if enable_traces and otlp_endpoint:
        try:
            # Create tracer provider
            tracer_provider = TracerProvider(resource=resource)

            # Create OTLP exporter
            headers_env = os.getenv("OTEL_EXPORTER_OTLP_HEADERS")
            span_headers: dict[str, str] | None = None
            if headers_env:
                # Parse headers as "key1=value1,key2=value2" format
                headers_list = [
                    tuple(h.split("=", 1)) for h in headers_env.split(",") if "=" in h
                ]
                span_headers = dict(headers_list)
            otlp_exporter = OTLPSpanExporter(
                endpoint=otlp_endpoint,
                headers=span_headers,
            )

            # Add batch processor
            tracer_provider.add_span_processor(BatchSpanProcessor(otlp_exporter))

            # Set global tracer provider
            trace.set_tracer_provider(tracer_provider)

            print(f"✅ OpenTelemetry tracing enabled for {service_name}")

        except Exception as e:
            print(f"⚠️  Failed to set up OpenTelemetry tracing: {e}")

    # Set up metrics if enabled
    if enable_metrics and otlp_endpoint:
        try:
            # Create metric reader
            metric_headers_env = os.getenv("OTEL_EXPORTER_OTLP_HEADERS")
            metric_headers: dict[str, str] | None = None
            if metric_headers_env:
                # Parse headers as "key1=value1,key2=value2" format
                metric_headers_list = [
                    tuple(h.split("=", 1))
                    for h in metric_headers_env.split(",")
                    if "=" in h
                ]
                metric_headers = dict(metric_headers_list)
            metric_reader = PeriodicExportingMetricReader(
                OTLPMetricExporter(
                    endpoint=otlp_endpoint,
                    headers=metric_headers,
                ),
                export_interval_millis=int(
                    os.getenv("OTEL_METRIC_EXPORT_INTERVAL", "60000")
                ),
            )

            # Create meter provider
            meter_provider = MeterProvider(
                resource=resource, metric_readers=[metric_reader]
            )

            # Set global meter provider
            metrics.set_meter_provider(meter_provider)

            print(f"✅ OpenTelemetry metrics enabled for {service_name}")

        except Exception as e:
            print(f"⚠️  Failed to set up OpenTelemetry metrics: {e}")

    # Set up logging export via OTLP if enabled
    if enable_logs and otlp_endpoint:
        global _global_logger_provider
        try:
            # Enrich logs with trace context
            # set_logging_format=False to avoid clearing existing handlers
            LoggingInstrumentor().instrument(set_logging_format=False)

            # Parse log headers
            log_headers_env = os.getenv("OTEL_EXPORTER_OTLP_HEADERS")
            log_headers: dict[str, str] | None = None
            if log_headers_env:
                log_headers_list = [
                    tuple(h.split("=", 1))
                    for h in log_headers_env.split(",")
                    if "=" in h
                ]
                log_headers = dict(log_headers_list)

            log_exporter = OTLPLogExporter(
                endpoint=otlp_endpoint,
                headers=log_headers,
            )

            logger_provider = LoggerProvider(resource=resource)
            logger_provider.add_log_record_processor(
                BatchLogRecordProcessor(log_exporter)
            )
            _global_logger_provider = logger_provider

            print(f"✅ OpenTelemetry logging export configured for {service_name}")
            print("   Note: Call attach_logging_handler_simple() in main() to activate")

        except Exception as e:
            print(f"⚠️  Failed to set up OpenTelemetry logging export: {e}")

    # Set up HTTP instrumentation
    try:
        RequestsInstrumentor().instrument()
        URLLib3Instrumentor().instrument()
        print(f"✅ OpenTelemetry HTTP instrumentation enabled for {service_name}")

    except Exception as e:
        print(f"⚠️  Failed to set up OpenTelemetry HTTP instrumentation: {e}")

    # Set up async HTTP instrumentation (aiohttp)
    try:
        AioHttpClientInstrumentor().instrument()
        print(f"✅ OpenTelemetry aiohttp instrumentation enabled for {service_name}")

    except Exception as e:
        print(f"⚠️  Failed to set up OpenTelemetry aiohttp instrumentation: {e}")

    print(f"🚀 OpenTelemetry setup completed for {service_name} v{service_version}")


def instrument_fastapi_app(app):
    """
    Instrument a FastAPI application.

    Args:
        app: FastAPI application instance
    """
    try:
        FastAPIInstrumentor.instrument_app(app)
        print("✅ FastAPI application instrumented")
    except Exception as e:
        print(f"⚠️  Failed to instrument FastAPI application: {e}")


def attach_logging_handler_simple():
    """
    Attach OTLP logging handler to root logger.

    For async services without Uvicorn (NATS listeners, async processors).
    This attaches the OTLP handler to the root logger only.

    Call this in main() after setup_telemetry() to activate log export.
    """
    global _global_logger_provider, _otlp_logging_handler

    if _global_logger_provider is None:
        print("⚠️  Logger provider not configured - logging export not available")
        return False

    try:
        root_logger = logging.getLogger()

        # Check if handler already attached
        if _otlp_logging_handler is not None:
            if _otlp_logging_handler in root_logger.handlers:
                print("✅ OTLP logging handler already attached")
                return True

        # Create and attach handler
        handler = LoggingHandler(
            level=logging.NOTSET,
            logger_provider=_global_logger_provider,
        )

        root_logger.addHandler(handler)
        _otlp_logging_handler = handler

        print("✅ OTLP logging handler attached to root logger")
        print(f"   Total handlers: {len(root_logger.handlers)}")

        return True

    except Exception as e:
        print(f"⚠️  Failed to attach logging handler: {e}")
        return False


def get_tracer(name: str = None) -> trace.Tracer:
    """
    Get a tracer instance.

    Args:
        name: Tracer name

    Returns:
        Tracer instance
    """
    return trace.get_tracer(name or "ta-bot")


def get_meter(name: str = None) -> metrics.Meter:
    """
    Get a meter instance.

    Args:
        name: Meter name

    Returns:
        Meter instance
    """
    return metrics.get_meter(name or "ta-bot")


def flush_telemetry(timeout_seconds: float = 5.0) -> None:
    """
    Force flush all telemetry data (traces, metrics, logs) to prevent data loss.

    This function should be called on graceful shutdown (e.g., SIGTERM, SIGINT)
    to ensure that the last batch of telemetry data is exported before the
    process terminates.

    **Important Notes:**
    - This function is synchronous and may block for up to `timeout_seconds`
    - The default timeout (5 seconds) is designed to allow batch processors
      time to export pending data
    - For asyncio applications, consider calling this from the shutdown handler
      rather than signal handlers to avoid blocking the event loop
    - OpenTelemetry's force_flush() has its own internal timeout, which this
      function respects

    Args:
        timeout_seconds: Maximum time to wait for flush operations (default: 5.0)

    Returns:
        None
    """
    import time

    start_time = time.time()
    try:
        # Flush traces (with timeout)
        tracer_provider = trace.get_tracer_provider()
        if hasattr(tracer_provider, "force_flush"):
            try:
                # force_flush() accepts a timeout parameter
                tracer_provider.force_flush(timeout_millis=int(timeout_seconds * 1000))
                logger.info("✅ Traces flushed successfully")
            except TypeError:
                # Fallback for providers that don't accept timeout
                tracer_provider.force_flush()
                logger.info("✅ Traces flushed successfully")

        # Flush metrics (with timeout if supported)
        meter_provider = metrics.get_meter_provider()
        if hasattr(meter_provider, "force_flush"):
            try:
                meter_provider.force_flush(timeout_millis=int(timeout_seconds * 1000))
                logger.info("✅ Metrics flushed successfully")
            except TypeError:
                meter_provider.force_flush()
                logger.info("✅ Metrics flushed successfully")

        # Flush logs (with timeout if supported)
        global _global_logger_provider
        if _global_logger_provider is not None and hasattr(
            _global_logger_provider, "force_flush"
        ):
            try:
                _global_logger_provider.force_flush(
                    timeout_millis=int(timeout_seconds * 1000)
                )
                logger.info("✅ Logs flushed successfully")
            except TypeError:
                _global_logger_provider.force_flush()
                logger.info("✅ Logs flushed successfully")

        # Ensure we don't exceed total timeout
        elapsed = time.time() - start_time
        if elapsed < timeout_seconds:
            # Brief wait to allow batch processors to finalize export
            remaining_time = timeout_seconds - elapsed
            time.sleep(min(0.5, remaining_time))

    except Exception as e:
        logger.error(f"⚠️  Error flushing telemetry: {e}")


def shutdown_telemetry() -> None:
    """
    Shutdown all telemetry providers to ensure clean termination.

    This function should be called after flush_telemetry() to properly shut down
    all OpenTelemetry providers and release resources.

    Returns:
        None
    """
    try:
        # Shutdown traces
        tracer_provider = trace.get_tracer_provider()
        if hasattr(tracer_provider, "shutdown"):
            tracer_provider.shutdown()
            logger.info("✅ Trace provider shut down successfully")

        # Shutdown metrics
        meter_provider = metrics.get_meter_provider()
        if hasattr(meter_provider, "shutdown"):
            meter_provider.shutdown()
            logger.info("✅ Metrics provider shut down successfully")

        # Shutdown logs
        global _global_logger_provider
        if _global_logger_provider is not None and hasattr(
            _global_logger_provider, "shutdown"
        ):
            _global_logger_provider.shutdown()
            logger.info("✅ Log provider shut down successfully")

    except Exception as e:
        logger.error(f"⚠️  Error shutting down telemetry: {e}")


def setup_signal_handlers() -> None:
    """
    Set up signal handlers for graceful shutdown with telemetry flushing.

    **Important:** This function registers signal handlers for SIGTERM and SIGINT
    that flush telemetry data before the process terminates. This ensures that
    the last batch of telemetry data is not lost when pods are killed in Kubernetes.

    **Note for asyncio applications:** The signal handler flushes telemetry
    synchronously. For async applications, the main event loop should also
    handle cleanup in its shutdown sequence.

    Returns:
        None
    """
    import signal
    import sys

    def signal_handler(signum: int, frame) -> None:  # type: ignore[no-untyped-def]
        """
        Signal handler that flushes telemetry and shuts down providers.

        Args:
            signum: Signal number
            frame: Current stack frame
        """
        signal_name = (
            signal.Signals(signum).name if signum in signal.Signals else str(signum)
        )
        logger.info(f"Received {signal_name}, shutting down gracefully...")

        # Flush telemetry data
        flush_telemetry(timeout_seconds=5.0)

        # Shutdown providers
        shutdown_telemetry()

        logger.info("Telemetry shutdown complete")
        # Note: For asyncio applications, the main event loop should handle
        # graceful shutdown. sys.exit() here ensures telemetry is flushed
        # even if the event loop doesn't complete cleanup in time.
        # The application's main loop should also call flush_telemetry()
        # and shutdown_telemetry() in its shutdown sequence.
        sys.exit(0)

    # Register signal handlers
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    logger.info("✅ Graceful shutdown signal handlers registered (SIGTERM, SIGINT)")


# Auto-setup if environment variable is set and not disabled
if os.getenv("ENABLE_OTEL", "true").lower() in ("true", "1", "yes"):
    if not os.getenv("OTEL_NO_AUTO_INIT"):
        if os.getenv("OTEL_AUTO_SETUP", "true").lower() in ("true", "1", "yes"):
            setup_telemetry()
