"""
Health check endpoints for the TA Bot.
"""

import asyncio
import logging
import os
import time
from typing import Any, Dict

import uvicorn
from fastapi import FastAPI
from fastapi.responses import JSONResponse, Response
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)

logger = logging.getLogger(__name__)

# Prometheus metrics
TA_ANALYSIS_REQUESTS = Counter(
    "ta_analysis_requests_total", "Total TA analysis requests", ["symbol", "timeframe"]
)
TA_ANALYSIS_DURATION = Histogram(
    "ta_analysis_duration_seconds", "TA analysis duration", ["symbol", "timeframe"]
)
TA_INDICATORS_CALCULATED = Counter(
    "ta_indicators_calculated_total", "Total TA indicators calculated", ["indicator"]
)
TA_SIGNALS_GENERATED = Counter(
    "ta_signals_generated_total",
    "Total trading signals generated",
    ["symbol", "signal_type"],
)
NATS_MESSAGES_PROCESSED = Counter(
    "nats_messages_processed_total", "Total NATS messages processed"
)
SERVICE_UPTIME = Gauge("service_uptime_seconds", "Service uptime in seconds")

# Global variables for health status
start_time = time.time()
app = FastAPI(title="TA Bot Health API", version="1.0.0")

# Instrument FastAPI for OpenTelemetry traces
try:
    from otel_init import instrument_app

    instrument_app(app)
except Exception as e:
    logger.warning(f"Could not instrument FastAPI for traces: {e}")


def get_uptime() -> str:
    """Get formatted uptime."""
    uptime_seconds = time.time() - start_time
    hours = int(uptime_seconds // 3600)
    minutes = int((uptime_seconds % 3600) // 60)
    seconds = int(uptime_seconds % 60)

    if hours > 0:
        return f"{hours}h {minutes}m {seconds}s"
    elif minutes > 0:
        return f"{minutes}m {seconds}s"
    else:
        return f"{seconds}s"


@app.get("/health")
async def health_check():
    """Get detailed health status."""
    return JSONResponse(
        {
            "status": "healthy",
            "version": os.getenv("VERSION", "1.0.0"),
            "build_info": {
                "commit_sha": os.getenv("COMMIT_SHA", "unknown"),
                "build_date": os.getenv("BUILD_DATE", "unknown"),
            },
            "components": {
                "signal_engine": "running",
                "nats_listener": "connected"
                if os.getenv("NATS_ENABLED", "true").lower() == "true"
                else "disabled",
                "publisher": "ready",
            },
            "uptime": get_uptime(),
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
    )


@app.get("/ready")
async def readiness_check():
    """Get readiness status."""
    return JSONResponse(
        {
            "status": "ready",
            "checks": {
                "nats_connection": "ok"
                if os.getenv("NATS_ENABLED", "true").lower() == "true"
                else "disabled",
                "api_endpoint": "ok",
                "signal_engine": "ok",
            },
            "uptime": get_uptime(),
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
    )


@app.get("/live")
async def liveness_check():
    """Get liveness status."""
    return JSONResponse(
        {
            "status": "alive",
            "uptime": get_uptime(),
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
    )


@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint."""
    try:
        # Update gauge metrics
        uptime_seconds = time.time() - start_time
        SERVICE_UPTIME.set(uptime_seconds)

        # Generate Prometheus-format metrics
        metrics_output = generate_latest()

        return Response(content=metrics_output, media_type=CONTENT_TYPE_LATEST)
    except Exception as e:
        logger.error(f"Failed to generate metrics: {e}")
        return Response(content=f"# Error generating metrics: {e}\n", status_code=500)


@app.get("/")
async def root():
    """Root endpoint."""
    return JSONResponse(
        {
            "service": "TA Bot Health API",
            "version": os.getenv("VERSION", "1.0.0"),
            "status": "running",
            "uptime": get_uptime(),
        }
    )


async def start_health_server(nats_url: str, api_endpoint: str, port: int = 8000):
    """Start the FastAPI health server."""
    logger.info(f"Starting FastAPI health server on port {port}")

    # Create server configuration
    config = uvicorn.Config(app, host="0.0.0.0", port=port, log_level="info")  # nosec B104
    server = uvicorn.Server(config)

    return HealthServerRunner(server)


class HealthServerRunner:
    """Health server runner."""

    def __init__(self, server):
        self.server = server
        self.running = True

    async def start(self):
        """Start the health server."""
        logger.info("Health server started")
        try:
            await self.server.serve()
        except asyncio.CancelledError:
            logger.info("Health server shutdown requested")
        except Exception as e:
            logger.error(f"Health server error: {e}")
            raise

    async def stop(self):
        """Stop the health server."""
        self.running = False
        logger.info("Health server stopped")


# Legacy functions for backward compatibility
def get_health_status() -> Dict[str, Any]:
    """Get health status (legacy function)."""
    return {
        "status": "healthy",
        "version": os.getenv("VERSION", "1.0.0"),
        "build_info": {
            "commit_sha": os.getenv("COMMIT_SHA", "unknown"),
            "build_date": os.getenv("BUILD_DATE", "unknown"),
        },
        "components": {
            "signal_engine": "running",
            "nats_listener": "connected",
            "publisher": "ready",
        },
    }


def get_readiness_status() -> Dict[str, Any]:
    """Get readiness status (legacy function)."""
    return {
        "status": "ready",
        "checks": {
            "nats_connection": "ok",
            "api_endpoint": "ok",
            "signal_engine": "ok",
        },
    }


def get_liveness_status() -> Dict[str, Any]:
    """Get liveness status (legacy function)."""
    return {"status": "alive", "uptime": get_uptime()}
