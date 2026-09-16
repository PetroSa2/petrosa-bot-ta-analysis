"""
Tests for the vendored Data Manager client SDK (ta_bot/services/dm_sdk/,
petrosa-bot-ta-analysis#267).

Uses httpx.MockTransport to exercise the real HTTP request/retry/error/
circuit-breaker logic in DataManagerClient._request — this is genuine
error-handling code now owned by this repo (not the wrapper in
ta_bot/services/data_manager_client.py, which is already covered by
test_data_manager_client_service.py), so it earns real tests rather than
being carried as untested vendored surface.
"""

import httpx
import pytest

from ta_bot.services.dm_sdk import (
    APIError,
    ConnectionError as DMConnectionError,
    DataManagerClient,
    TimeoutError as DMTimeoutError,
)


def _client_with_transport(handler) -> DataManagerClient:
    """Build a DataManagerClient whose internal httpx.AsyncClient uses a
    MockTransport, so no real network calls happen."""
    client = DataManagerClient(base_url="http://test-dm:80", max_retries=1)
    client._client = httpx.AsyncClient(
        transport=httpx.MockTransport(handler), base_url="http://test-dm:80"
    )
    return client


@pytest.mark.asyncio
class TestDataManagerClientRequest:
    async def test_successful_health_request(self):
        # Real `/health/readiness` shape (petrosa-data-manager's `ReadinessStatus`
        # model): `{ready, components, timestamp}` — no `status` key.
        # petrosa-bot-ta-analysis#270.
        real_health_response = {
            "ready": True,
            "components": {"nats": "healthy", "mysql": "healthy"},
            "timestamp": "2026-09-12T00:00:00Z",
        }

        def handler(request: httpx.Request) -> httpx.Response:
            assert request.method == "GET"
            assert request.url.path == "/health/readiness"
            return httpx.Response(200, json=real_health_response)

        client = _client_with_transport(handler)
        result = await client.health()
        assert result == real_health_response

    async def test_successful_insert_request(self):
        def handler(request: httpx.Request) -> httpx.Response:
            assert request.method == "POST"
            assert request.url.path == "/api/v1/mongodb/signals"
            return httpx.Response(200, json={"inserted_count": 1})

        client = _client_with_transport(handler)
        result = await client.insert(
            database="mongodb", collection="signals", data={"symbol": "BTCUSDT"}
        )
        assert result == {"inserted_count": 1}

    async def test_successful_get_candles_request_with_start_end(self):
        from datetime import UTC, datetime

        def handler(request: httpx.Request) -> httpx.Response:
            assert request.url.path == "/data/candles"
            assert "start" in request.url.params
            assert "end" in request.url.params
            return httpx.Response(200, json={"data": []})

        client = _client_with_transport(handler)
        result = await client.get_candles(
            "BTCUSDT",
            "15m",
            start=datetime(2026, 1, 1, tzinfo=UTC),
            end=datetime(2026, 1, 2, tzinfo=UTC),
        )
        assert result == {"data": []}

    async def test_api_error_raised_on_4xx_with_json_detail(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(422, json={"detail": "validation failed"})

        client = _client_with_transport(handler)
        with pytest.raises(APIError) as excinfo:
            await client.insert(database="mongodb", collection="signals", data={})
        assert excinfo.value.status_code == 422
        assert "validation failed" in str(excinfo.value)

    async def test_api_error_raised_on_5xx_with_non_json_body(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(500, text="internal server error")

        client = _client_with_transport(handler)
        with pytest.raises(APIError) as excinfo:
            await client.health()
        assert excinfo.value.status_code == 500

    async def test_connect_error_wrapped_as_dm_connection_error(self):
        def handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("connection refused")

        client = _client_with_transport(handler)
        with pytest.raises(DMConnectionError):
            await client.health()

    async def test_timeout_wrapped_as_dm_timeout_error(self):
        def handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ReadTimeout("timed out")

        client = _client_with_transport(handler)
        with pytest.raises(DMTimeoutError):
            await client.health()

    async def test_unexpected_exception_propagates_and_records_failure(self):
        def handler(request: httpx.Request) -> httpx.Response:
            raise ValueError("boom")

        client = _client_with_transport(handler)
        with pytest.raises(ValueError):
            await client.health()
        assert client._circuit_breaker_failures == 1


@pytest.mark.asyncio
class TestCircuitBreaker:
    async def test_circuit_opens_after_threshold_failures(self):
        def handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("down")

        client = _client_with_transport(handler)
        for _ in range(client._circuit_breaker_threshold):
            with pytest.raises(DMConnectionError):
                await client.health()

        assert client._circuit_breaker_open is True
        # Once open, _check_circuit_breaker fails fast without another request.
        with pytest.raises(DMConnectionError, match="Circuit breaker is open"):
            await client.health()

    async def test_circuit_allows_half_open_probe_after_reset_timeout(self):
        """petrosa-bot-ta-analysis#290: once the reset timeout has elapsed,
        the breaker must let a single probe request through rather than
        failing fast forever."""

        def failing_handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("down")

        client = _client_with_transport(failing_handler)
        client._circuit_breaker_reset_timeout = 0.05
        for _ in range(client._circuit_breaker_threshold):
            with pytest.raises(DMConnectionError):
                await client.health()
        assert client._circuit_breaker_open is True

        # Immediately after opening, still fails fast (no time elapsed).
        with pytest.raises(DMConnectionError, match="Circuit breaker is open"):
            await client.health()

        # After the reset timeout elapses, a real HTTP request is attempted
        # again (the probe) instead of failing fast.
        import asyncio

        await asyncio.sleep(0.06)

        def success_handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"ready": True, "components": {}})

        client._client = httpx.AsyncClient(
            transport=httpx.MockTransport(success_handler),
            base_url="http://test-dm:80",
        )
        result = await client.health()
        assert result == {"ready": True, "components": {}}
        assert client._circuit_breaker_open is False
        assert client._circuit_breaker_failures == 0

    async def test_failed_half_open_probe_reopens_breaker(self):
        """A probe that itself fails must re-open the breaker for another
        full window rather than probing again on the very next call."""

        def failing_handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("still down")

        client = _client_with_transport(failing_handler)
        client._circuit_breaker_reset_timeout = 0.05
        for _ in range(client._circuit_breaker_threshold):
            with pytest.raises(DMConnectionError):
                await client.health()
        assert client._circuit_breaker_open is True

        import asyncio

        await asyncio.sleep(0.06)

        # The half-open probe itself fails.
        with pytest.raises(DMConnectionError):
            await client.health()
        assert client._circuit_breaker_open is True

        # Immediately after the failed probe, breaker fails fast again
        # (timer was refreshed, not left expired).
        with pytest.raises(DMConnectionError, match="Circuit breaker is open"):
            await client.health()

    async def test_circuit_closes_after_success_following_failures(self):
        state = {"calls": 0}

        def handler(request: httpx.Request) -> httpx.Response:
            state["calls"] += 1
            if state["calls"] <= 2:
                raise httpx.ConnectError("flaky")
            return httpx.Response(200, json={"ready": True, "components": {}})

        client = _client_with_transport(handler)
        for _ in range(2):
            with pytest.raises(DMConnectionError):
                await client.health()
        assert client._circuit_breaker_failures == 2

        result = await client.health()
        assert result == {"ready": True, "components": {}}
        assert client._circuit_breaker_failures == 0
        assert client._circuit_breaker_open is False


@pytest.mark.asyncio
class TestLifecycle:
    async def test_close_calls_aclose(self):
        client = DataManagerClient(base_url="http://test-dm:80")
        await client.close()
        assert client._client.is_closed

    async def test_async_context_manager_closes_on_exit(self):
        async with DataManagerClient(base_url="http://test-dm:80") as client:
            assert client is not None
        assert client._client.is_closed

    async def test_api_key_sent_as_bearer_header(self):
        captured = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["auth"] = request.headers.get("authorization")
            return httpx.Response(200, json={"ready": True, "components": {}})

        client = DataManagerClient(base_url="http://test-dm:80", api_key="secret-key")
        client._client = httpx.AsyncClient(
            transport=httpx.MockTransport(handler), base_url="http://test-dm:80"
        )
        await client.health()
        assert captured["auth"] == "Bearer secret-key"
