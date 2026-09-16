"""
Data Manager Client - Main client class for interacting with the API.

Trimmed vendor (petrosa-bot-ta-analysis#267): this is a reduced copy of
petrosa-data-manager/client/client.py, keeping only the operations
ta_bot/services/data_manager_client.py actually calls — health(), close(),
get_candles(), and insert(). The full upstream SDK also exposes query(),
update(), delete(), batch(), get_trades(), get_funding(), get_depth(), and
get_metrics(), none of which this repo uses; vendoring unused surface area
only adds untested/untestable dead code. If a future caller in this repo
needs one of those methods, re-add it (and its tests) at that point rather
than carrying it speculatively.
"""

import json
import logging
import time
from datetime import datetime
from typing import Any
from urllib.parse import urljoin

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from .exceptions import (
    APIError,
    ConnectionError as ClientConnectionError,
    TimeoutError as ClientTimeoutError,
)

logger = logging.getLogger(__name__)


class DataManagerClient:
    """
    Client for interacting with Petrosa Data Manager API.

    Supports both generic CRUD operations and domain-specific market data endpoints.
    Includes connection pooling, retries, and circuit breaker protection.

    Example:
        >>> client = DataManagerClient(base_url="http://data-manager:8000")
        >>> candles = await client.get_candles("BTCUSDT", "15m", limit=200)
        >>> await client.insert("mongodb", "trades_BTCUSDT", data=[...])
    """

    def __init__(
        self,
        base_url: str,
        timeout: int = 30,
        max_retries: int = 3,
        pool_size: int = 10,
        api_key: str | None = None,
        circuit_breaker_reset_timeout: float = 30.0,
    ):
        """
        Initialize Data Manager Client.

        Args:
            base_url: Base URL of the Data Manager API
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
            pool_size: HTTP connection pool size
            api_key: Optional API key for authentication
            circuit_breaker_reset_timeout: Seconds the breaker stays fully
                open before allowing a single half-open probe request through
                (petrosa-bot-ta-analysis#290). Without this, a breaker that
                opens during a transient upstream outage never closes again
                for the lifetime of the process, even once the upstream has
                fully recovered.
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self.api_key = api_key

        # Create HTTP client with connection pooling
        limits = httpx.Limits(
            max_keepalive_connections=pool_size, max_connections=pool_size * 2
        )
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(timeout),
            limits=limits,
            follow_redirects=True,
        )

        # Circuit breaker state (petrosa-bot-ta-analysis#290: half-open recovery)
        self._circuit_breaker_failures = 0
        self._circuit_breaker_threshold = 5
        self._circuit_breaker_open = False
        self._circuit_breaker_opened_at: float | None = None
        self._circuit_breaker_reset_timeout = circuit_breaker_reset_timeout

        logger.info(f"DataManagerClient initialized with base_url={base_url}")

    async def close(self):
        """Close the HTTP client and cleanup resources."""
        await self._client.aclose()
        logger.info("DataManagerClient closed")

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    def _check_circuit_breaker(self):
        """Check if circuit breaker is open.

        petrosa-bot-ta-analysis#290: a plain "if open: raise" never recovers
        on its own — once opened during a transient upstream outage, every
        subsequent call would fail fast forever, for the lifetime of the
        process, even long after the upstream came back healthy. Once
        `_circuit_breaker_reset_timeout` has elapsed since the breaker
        opened (or was last re-opened by a failed probe), let exactly one
        request through as a half-open probe: the caller's own
        `_record_success`/`_record_failure` then decides whether the
        breaker actually closes or stays open for another window.
        """
        if not self._circuit_breaker_open:
            return

        opened_at = self._circuit_breaker_opened_at
        elapsed = (
            time.monotonic() - opened_at if opened_at is not None else float("inf")
        )
        if elapsed >= self._circuit_breaker_reset_timeout:
            logger.info(
                "Circuit breaker reset timeout elapsed (%.1fs >= %.1fs) - "
                "allowing a half-open probe request",
                elapsed,
                self._circuit_breaker_reset_timeout,
            )
            return

        logger.warning(
            "Circuit breaker still open (%.1fs remaining until next probe)",
            self._circuit_breaker_reset_timeout - elapsed,
        )
        raise ClientConnectionError("Circuit breaker is open - too many failures")

    def _record_success(self):
        """Record successful request."""
        self._circuit_breaker_failures = 0
        if self._circuit_breaker_open:
            logger.info("Circuit breaker closed after successful request")
            self._circuit_breaker_open = False
            self._circuit_breaker_opened_at = None

    def _record_failure(self):
        """Record failed request."""
        self._circuit_breaker_failures += 1
        if self._circuit_breaker_failures >= self._circuit_breaker_threshold:
            self._circuit_breaker_open = True
            # Refresh the timer on every failure while open (including a
            # failed half-open probe) so the breaker stays fully open for a
            # fresh window rather than immediately probing again next call.
            self._circuit_breaker_opened_at = time.monotonic()
            logger.error("Circuit breaker opened after too many failures")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((httpx.ConnectError, httpx.TimeoutException)),
    )
    async def _request(
        self,
        method: str,
        endpoint: str,
        params: dict[str, Any] | None = None,
        json_data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Make HTTP request with retries and error handling.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint path
            params: Query parameters
            json_data: JSON body data

        Returns:
            Response JSON data

        Raises:
            APIError: API returned error response
            ConnectionError: Connection to API failed
            TimeoutError: Request timed out
        """
        self._check_circuit_breaker()

        url = urljoin(self.base_url, endpoint)
        headers = {}

        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        try:
            logger.debug(f"{method} {url} params={params}")

            response = await self._client.request(
                method=method,
                url=url,
                params=params,
                json=json_data,
                headers=headers,
            )

            # Check for HTTP errors
            if response.status_code >= 400:
                error_detail = response.text
                error_json: dict[str, Any] | None = None
                try:
                    error_json = response.json()
                    error_detail = error_json.get("detail", error_detail)
                except Exception:
                    # petrosa-bot-ta-analysis#267: a non-JSON error body (plain
                    # text 500s are common) must not crash the error handler
                    # itself with a second, unprotected .json() parse attempt —
                    # this was a latent bug in the vendored source. error_json
                    # stays None; APIError.response reflects that honestly.
                    pass

                self._record_failure()
                raise APIError(
                    f"API error: {error_detail}",
                    status_code=response.status_code,
                    response=error_json,
                )

            self._record_success()
            return response.json()

        except httpx.ConnectError as e:
            self._record_failure()
            raise ClientConnectionError(f"Failed to connect to {url}: {e}")

        except httpx.TimeoutException as e:
            self._record_failure()
            raise ClientTimeoutError(f"Request to {url} timed out: {e}")

        except Exception as e:
            self._record_failure()
            logger.error(f"Unexpected error in request to {url}: {e}", exc_info=True)
            raise

    # =============================================================================
    # GENERIC CRUD OPERATIONS (trimmed to what ta_bot actually calls — see
    # module docstring)
    # =============================================================================

    async def insert(
        self,
        database: str,
        collection: str,
        data: dict[str, Any] | list[dict[str, Any]],
        schema: str | None = None,
        validate: bool = False,
    ) -> dict[str, Any]:
        """
        Insert records into a database collection.

        Args:
            database: Database name ('mysql' or 'mongodb')
            collection: Collection/table name
            data: Data to insert (single record or list)
            schema: Schema name for validation
            validate: Enable schema validation

        Returns:
            API response with inserted count
        """
        params = {}
        if schema:
            params["schema"] = schema
        if validate:
            params["validate"] = "true"

        return await self._request(
            "POST",
            f"/api/v1/{database}/{collection}",
            params=params,
            json_data={"data": data},
        )

    # =============================================================================
    # DOMAIN-SPECIFIC MARKET DATA OPERATIONS
    # =============================================================================

    async def get_candles(
        self,
        pair: str,
        period: str,
        start: datetime | None = None,
        end: datetime | None = None,
        limit: int = 100,
        offset: int = 0,
        sort_order: str = "asc",
    ) -> dict[str, Any]:
        """
        Get OHLCV candle data for a trading pair.

        Args:
            pair: Trading pair symbol (e.g., 'BTCUSDT')
            period: Candle period (e.g., '1m', '15m', '1h')
            start: Start timestamp
            end: End timestamp
            limit: Maximum number of candles
            offset: Pagination offset
            sort_order: Sort order ('asc' or 'desc')

        Returns:
            API response with candle data
        """
        params = {
            "pair": pair,
            "period": period,
            "limit": limit,
            "offset": offset,
            "sort_order": sort_order,
        }

        if start:
            params["start"] = start.isoformat()
        if end:
            params["end"] = end.isoformat()

        return await self._request("GET", "/data/candles", params=params)

    # =============================================================================
    # HEALTH AND MONITORING
    # =============================================================================

    async def health(self) -> dict[str, Any]:
        """
        Check Data Manager API health status.

        Returns:
            Health status information
        """
        return await self._request("GET", "/health/readiness")
