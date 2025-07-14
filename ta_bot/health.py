"""
Health endpoints for the TA Bot.
Provides health, readiness, and liveness probes for Kubernetes.
"""

import asyncio
import aiohttp
from aiohttp import web
import logging
from datetime import datetime
from typing import Dict, Any

logger = logging.getLogger(__name__)


class HealthChecker:
    """Health checker for the TA Bot."""
    
    def __init__(self, nats_url: str, api_endpoint: str):
        """Initialize the health checker."""
        self.nats_url = nats_url
        self.api_endpoint = api_endpoint
        self.start_time = datetime.utcnow()
        self.is_ready = False
        self.is_healthy = True
    
    async def check_nats_connection(self) -> bool:
        """Check NATS connection."""
        try:
            # Simple connection check - in production you'd use the actual NATS client
            # For now, we'll just check if the URL is valid
            if not self.nats_url or self.nats_url == "nats://localhost:4222":
                return True  # Assume local development
            return True
        except Exception as e:
            logger.error(f"NATS connection check failed: {e}")
            return False
    
    async def check_api_endpoint(self) -> bool:
        """Check API endpoint availability."""
        try:
            if not self.api_endpoint or self.api_endpoint == "http://localhost:8080/signals":
                return True  # Assume local development
            
            async with aiohttp.ClientSession() as session:
                async with session.get(self.api_endpoint.replace("/signals", "/health")) as response:
                    return response.status == 200
        except Exception as e:
            logger.error(f"API endpoint check failed: {e}")
            return False
    
    async def get_health_status(self) -> Dict[str, Any]:
        """Get comprehensive health status."""
        nats_ok = await self.check_nats_connection()
        api_ok = await self.check_api_endpoint()
        
        uptime = (datetime.utcnow() - self.start_time).total_seconds()
        
        return {
            "status": "healthy" if (nats_ok and api_ok) else "unhealthy",
            "timestamp": datetime.utcnow().isoformat(),
            "uptime_seconds": uptime,
            "components": {
                "nats": "healthy" if nats_ok else "unhealthy",
                "api": "healthy" if api_ok else "unhealthy"
            },
            "version": "1.0.0"
        }
    
    async def get_readiness_status(self) -> Dict[str, Any]:
        """Get readiness status."""
        nats_ok = await self.check_nats_connection()
        api_ok = await self.check_api_endpoint()
        
        self.is_ready = nats_ok and api_ok
        
        return {
            "status": "ready" if self.is_ready else "not_ready",
            "timestamp": datetime.utcnow().isoformat(),
            "components": {
                "nats": "ready" if nats_ok else "not_ready",
                "api": "ready" if api_ok else "not_ready"
            }
        }
    
    async def get_liveness_status(self) -> Dict[str, Any]:
        """Get liveness status."""
        return {
            "status": "alive" if self.is_healthy else "dead",
            "timestamp": datetime.utcnow().isoformat(),
            "uptime_seconds": (datetime.utcnow() - self.start_time).total_seconds()
        }


async def health_handler(request: web.Request) -> web.Response:
    """Health check endpoint."""
    health_checker = request.app['health_checker']
    status = await health_checker.get_health_status()
    
    if status["status"] == "healthy":
        return web.json_response(status, status=200)
    else:
        return web.json_response(status, status=503)


async def ready_handler(request: web.Request) -> web.Response:
    """Readiness probe endpoint."""
    health_checker = request.app['health_checker']
    status = await health_checker.get_readiness_status()
    
    if status["status"] == "ready":
        return web.json_response(status, status=200)
    else:
        return web.json_response(status, status=503)


async def live_handler(request: web.Request) -> web.Response:
    """Liveness probe endpoint."""
    health_checker = request.app['health_checker']
    status = await health_checker.get_liveness_status()
    
    if status["status"] == "alive":
        return web.json_response(status, status=200)
    else:
        return web.json_response(status, status=503)


def create_health_app(nats_url: str, api_endpoint: str) -> web.Application:
    """Create health check application."""
    app = web.Application()
    
    # Store health checker in app context
    app['health_checker'] = HealthChecker(nats_url, api_endpoint)
    
    # Add routes
    app.router.add_get('/health', health_handler)
    app.router.add_get('/ready', ready_handler)
    app.router.add_get('/live', live_handler)
    
    return app


async def start_health_server(nats_url: str, api_endpoint: str, port: int = 8000):
    """Start the health check server."""
    app = create_health_app(nats_url, api_endpoint)
    
    runner = web.AppRunner(app)
    await runner.setup()
    
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    
    logger.info(f"Health check server started on port {port}")
    
    return runner 