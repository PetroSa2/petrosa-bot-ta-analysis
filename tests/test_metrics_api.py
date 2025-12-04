"""
Tests for Performance Metrics API.

These tests verify the metrics API endpoints work correctly and return
proper data structures for agent consumption.
"""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

# Import the FastAPI app
from ta_bot.health import app
from ta_bot.models.metrics import (
    ComparisonResponse,
    PerformanceMetricsResponse,
    ResourceUsageResponse,
    SuccessRateResponse,
    TrendResponse,
)
from ta_bot.services.metrics_aggregator import MetricsAggregator


@pytest.fixture
def client():
    """Create test client"""
    return TestClient(app)


@pytest.fixture
def metrics_aggregator():
    """Create metrics aggregator instance"""
    return MetricsAggregator()


class TestMetricsAggregator:
    """Test MetricsAggregator class"""

    def test_parse_timeframe_minutes(self, metrics_aggregator):
        """Test parsing timeframe in minutes"""
        assert metrics_aggregator.parse_timeframe("5m") == 300
        assert metrics_aggregator.parse_timeframe("15m") == 900
        assert metrics_aggregator.parse_timeframe("30m") == 1800

    def test_parse_timeframe_hours(self, metrics_aggregator):
        """Test parsing timeframe in hours"""
        assert metrics_aggregator.parse_timeframe("1h") == 3600
        assert metrics_aggregator.parse_timeframe("24h") == 86400

    def test_parse_timeframe_days(self, metrics_aggregator):
        """Test parsing timeframe in days"""
        assert metrics_aggregator.parse_timeframe("1d") == 86400
        assert metrics_aggregator.parse_timeframe("7d") == 604800
        assert metrics_aggregator.parse_timeframe("30d") == 2592000

    def test_parse_timeframe_invalid_format(self, metrics_aggregator):
        """Test parsing invalid timeframe format"""
        with pytest.raises(ValueError, match="Invalid timeframe"):
            metrics_aggregator.parse_timeframe("invalid")

    def test_parse_timeframe_invalid_value(self, metrics_aggregator):
        """Test parsing invalid timeframe value"""
        with pytest.raises(ValueError, match="Invalid timeframe value"):
            metrics_aggregator.parse_timeframe("abch")

    @pytest.mark.asyncio
    async def test_get_metrics(self, metrics_aggregator):
        """Test getting aggregated metrics"""
        start_time = datetime.utcnow() - timedelta(hours=1)
        metrics = await metrics_aggregator.get_metrics(
            start_time=start_time,
            metric_filter=None,
            strategy_id=None,
            symbol=None,
        )

        assert "latency" in metrics
        assert "throughput" in metrics
        assert "errors" in metrics
        assert "resource_usage" in metrics

    @pytest.mark.asyncio
    async def test_get_metrics_with_filter(self, metrics_aggregator):
        """Test getting specific metric"""
        start_time = datetime.utcnow() - timedelta(hours=1)
        metrics = await metrics_aggregator.get_metrics(
            start_time=start_time,
            metric_filter="latency",
            strategy_id=None,
            symbol=None,
        )

        assert "latency" in metrics
        assert len(metrics) == 1

    @pytest.mark.asyncio
    async def test_get_success_rates(self, metrics_aggregator):
        """Test getting success rates"""
        success_data = await metrics_aggregator.get_success_rates(
            strategy_id="rsi_extreme_reversal",
            window="24h",
            symbol="BTCUSDT",
        )

        assert "signals_generated" in success_data
        assert "signals_executed" in success_data
        assert "execution_rate" in success_data
        assert "win_rate" in success_data
        assert "symbol_breakdown" in success_data

    @pytest.mark.asyncio
    async def test_get_resource_usage(self, metrics_aggregator):
        """Test getting resource usage"""
        resource_data = await metrics_aggregator.get_resource_usage(
            pod_id="ta-bot-abc123",
            timeframe="1h",
        )

        assert "cpu" in resource_data
        assert "memory" in resource_data
        assert "pod_count" in resource_data

    @pytest.mark.asyncio
    async def test_get_metric_trends(self, metrics_aggregator):
        """Test getting metric trends"""
        trend_data = await metrics_aggregator.get_metric_trends(
            metric="latency_p95",
            period="7d",
            interval="1h",
            strategy_id=None,
        )

        assert "data_points" in trend_data
        assert "trend_analysis" in trend_data
        assert len(trend_data["data_points"]) > 0

    @pytest.mark.asyncio
    async def test_compare_metrics(self, metrics_aggregator):
        """Test comparing metrics before and after"""
        before = datetime.utcnow() - timedelta(hours=2)
        after = datetime.utcnow() - timedelta(hours=1)

        comparison_data = await metrics_aggregator.compare_metrics(
            before=before,
            after=after,
            metric=None,
            window=3600,
        )

        assert "comparison" in comparison_data
        assert "overall_assessment" in comparison_data
        assert "recommendation" in comparison_data


class TestPerformanceMetricsAPI:
    """Test Performance Metrics API endpoints"""

    def test_performance_metrics_endpoint(self, client):
        """Test GET /api/v1/metrics/performance"""
        response = client.get("/api/v1/metrics/performance?timeframe=1h")

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert data["timeframe"] == "1h"
        assert "metrics" in data
        assert "sample_count" in data
        assert "collection_timestamp" in data

    def test_performance_metrics_with_filter(self, client):
        """Test performance metrics with metric filter"""
        response = client.get(
            "/api/v1/metrics/performance?timeframe=24h&metric=latency"
        )

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert data["timeframe"] == "24h"
        assert "metrics" in data

    def test_performance_metrics_with_strategy_filter(self, client):
        """Test performance metrics filtered by strategy"""
        response = client.get(
            "/api/v1/metrics/performance?timeframe=1h&strategy_id=rsi_extreme_reversal"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["metadata"]["strategy_id"] == "rsi_extreme_reversal"

    def test_performance_metrics_invalid_timeframe(self, client):
        """Test performance metrics with invalid timeframe"""
        response = client.get("/api/v1/metrics/performance?timeframe=invalid")

        assert response.status_code == 422  # Validation error

    def test_success_rates_endpoint(self, client):
        """Test GET /api/v1/metrics/success-rates"""
        response = client.get("/api/v1/metrics/success-rates?window=24h")

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert data["window"] == "24h"
        assert "success_metrics" in data
        assert "symbol_breakdown" in data

    def test_success_rates_with_strategy(self, client):
        """Test success rates filtered by strategy"""
        response = client.get(
            "/api/v1/metrics/success-rates?window=24h&strategy_id=rsi_extreme_reversal"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["strategy_id"] == "rsi_extreme_reversal"

    def test_resource_usage_endpoint(self, client):
        """Test GET /api/v1/metrics/resource-usage"""
        response = client.get("/api/v1/metrics/resource-usage?timeframe=1h")

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert data["timeframe"] == "1h"
        assert "resources" in data
        assert "pod_count" in data

    def test_trends_endpoint(self, client):
        """Test GET /api/v1/metrics/trends"""
        response = client.get(
            "/api/v1/metrics/trends?metric=latency_p95&period=7d&interval=1h"
        )

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert data["metric"] == "latency_p95"
        assert data["period"] == "7d"
        assert data["interval"] == "1h"
        assert "data_points" in data
        assert "trend_analysis" in data
        assert isinstance(data["data_points"], list)

    def test_trends_endpoint_missing_metric(self, client):
        """Test trends endpoint without required metric parameter"""
        response = client.get("/api/v1/metrics/trends?period=7d&interval=1h")

        assert response.status_code == 422  # Validation error

    def test_comparison_endpoint(self, client):
        """Test GET /api/v1/metrics/comparison"""
        before = (datetime.utcnow() - timedelta(hours=2)).isoformat()
        after = (datetime.utcnow() - timedelta(hours=1)).isoformat()

        response = client.get(
            f"/api/v1/metrics/comparison?before={before}&after={after}&window=3600"
        )

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert "before_timestamp" in data
        assert "after_timestamp" in data
        assert "comparison" in data
        assert "overall_assessment" in data
        assert "recommendation" in data

    def test_comparison_endpoint_invalid_timestamps(self, client):
        """Test comparison with after timestamp before before timestamp"""
        before = (datetime.utcnow() - timedelta(hours=1)).isoformat()
        after = (datetime.utcnow() - timedelta(hours=2)).isoformat()

        response = client.get(
            f"/api/v1/metrics/comparison?before={before}&after={after}&window=3600"
        )

        assert response.status_code == 400  # Bad request

    def test_metrics_health_endpoint(self, client):
        """Test GET /api/v1/metrics/health"""
        response = client.get("/api/v1/metrics/health")

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "healthy"
        assert data["service"] == "ta-bot-metrics-api"
        assert "timestamp" in data


class TestMetricsCaching:
    """Test metrics caching functionality"""

    @pytest.mark.asyncio
    async def test_cache_stores_results(self, metrics_aggregator):
        """Test that metrics are cached"""
        start_time = datetime.utcnow() - timedelta(hours=1)

        # First call
        await metrics_aggregator.get_metrics(
            start_time=start_time,
            metric_filter=None,
            strategy_id=None,
            symbol=None,
        )

        # Check cache has entry
        assert len(metrics_aggregator.cache) > 0

    @pytest.mark.asyncio
    async def test_cache_returns_cached_data(self, metrics_aggregator):
        """Test that cached data is returned on subsequent calls"""
        start_time = datetime.utcnow() - timedelta(hours=1)

        # First call
        result1 = await metrics_aggregator.get_metrics(
            start_time=start_time,
            metric_filter=None,
            strategy_id=None,
            symbol=None,
        )

        # Second call (should be cached)
        result2 = await metrics_aggregator.get_metrics(
            start_time=start_time,
            metric_filter=None,
            strategy_id=None,
            symbol=None,
        )

        # Results should be identical (from cache)
        assert result1 == result2


class TestMetricsResponseModels:
    """Test Pydantic response models"""

    def test_performance_metrics_response_model(self):
        """Test PerformanceMetricsResponse model validation"""
        from ta_bot.models.metrics import LatencyMetrics, PerformanceMetricsData

        response = PerformanceMetricsResponse(
            success=True,
            timeframe="1h",
            metrics=PerformanceMetricsData(
                latency=LatencyMetrics(p50=45.2, p95=120.5, p99=280.3)
            ),
            sample_count=360,
            collection_timestamp=datetime.utcnow(),
        )

        assert response.success is True
        assert response.timeframe == "1h"
        assert response.metrics.latency is not None
        assert response.metrics.latency.p50 == 45.2

    def test_success_rate_response_model(self):
        """Test SuccessRateResponse model validation"""
        from ta_bot.models.metrics import SuccessMetrics

        response = SuccessRateResponse(
            success=True,
            window="24h",
            success_metrics=SuccessMetrics(
                signals_generated=125,
                signals_executed=98,
                execution_rate=0.784,
                winning_trades=62,
                losing_trades=36,
                win_rate=0.633,
            ),
        )

        assert response.success is True
        assert response.success_metrics.signals_generated == 125
        assert response.success_metrics.execution_rate == 0.784
