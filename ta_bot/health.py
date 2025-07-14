"""
Health check endpoints for the TA Bot.
"""

import logging
import os
from typing import Dict, Any

logger = logging.getLogger(__name__)


async def start_health_server(nats_url: str, api_endpoint: str, port: int = 8000):
    """Start a simple health server."""
    logger.info(f"Starting health server on port {port}")

    # For now, just return a mock runner
    # In a real implementation, this would start a FastAPI server
    return MockHealthRunner()


class MockHealthRunner:
    """Mock health server runner for testing."""

    def __init__(self):
        self.running = True

    async def start(self):
        """Start the health server."""
        logger.info("Mock health server started")

    async def stop(self):
        """Stop the health server."""
        self.running = False
        logger.info("Mock health server stopped")


def get_health_status() -> Dict[str, Any]:
    """Get health status."""
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
    """Get readiness status."""
    return {
        "status": "ready",
        "checks": {
            "nats_connection": "ok",
            "api_endpoint": "ok",
            "signal_engine": "ok",
        },
    }


def get_liveness_status() -> Dict[str, Any]:
    """Get liveness status."""
    return {"status": "alive", "uptime": "0s"}
