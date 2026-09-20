"""
NATS listener service for receiving candle data and processing signals.
"""

import asyncio
import json
import logging
import time
from collections import deque
from typing import Any

from nats.aio.client import Client as NATS

from ta_bot.core.signal_engine import SignalEngine
from ta_bot.services.app_config_manager import AppConfigManager
from ta_bot.services.config_manager import StrategyConfigManager
from ta_bot.services.mysql_client import MySQLClient
from ta_bot.services.publisher import SignalPublisher

logger = logging.getLogger(__name__)


class NATSListener:
    """NATS message listener for candle data."""

    def __init__(
        self,
        nats_url: str,
        signal_engine: SignalEngine,
        publisher: SignalPublisher,
        nats_subject_prefix: str = "binance.extraction",
        nats_subject_prefix_production: str = "binance.extraction.production",
        nats_queue_group: str = "ta-bot-analysis",
        supported_symbols: list[str] | None = None,
        supported_timeframes: list[str] | None = None,
        app_config_manager: AppConfigManager | None = None,
        strategy_config_manager: StrategyConfigManager | None = None,
    ):
        """
        Initialize the NATS listener.

        Args:
            nats_url: NATS server URL
            signal_engine: SignalEngine instance for analyzing candles
            publisher: SignalPublisher for publishing signals
            nats_subject_prefix: NATS subject prefix
            nats_subject_prefix_production: NATS subject prefix for production
            nats_queue_group: NATS queue group shared by every replica (#304).
                NATS delivers a queue-grouped message to exactly one member
                of the group, so with `replicas: 2` this — not the removed
                `leader_election` placeholder — is what guarantees a single
                analysis cycle per message.
            supported_symbols: Default symbols (fallback if no runtime config)
            supported_timeframes: Default timeframes (fallback if no runtime config)
            app_config_manager: Optional AppConfigManager for runtime configuration
            strategy_config_manager: Optional StrategyConfigManager (#271/#283) used
                to resolve per-strategy, per-symbol configuration before each
                analysis cycle. `None` (the default, and the only value in
                production until a follow-up wires the #271 instance through) means
                every strategy resolves purely from `defaults.py` — see
                `_resolve_strategy_configs` docstring.
        """
        self.nats_url = nats_url
        self.signal_engine = signal_engine
        self.publisher = publisher
        self.nats_subject_prefix = nats_subject_prefix
        self.nats_subject_prefix_production = nats_subject_prefix_production
        self.nats_queue_group = nats_queue_group
        self.supported_symbols = supported_symbols or ["BTCUSDT", "ETHUSDT", "ADAUSDT"]
        self.supported_timeframes = supported_timeframes or ["15m", "1h"]
        self.app_config_manager = app_config_manager
        self.strategy_config_manager = strategy_config_manager
        self.nc = NATS()
        self.subscriptions: list[Any] = []
        self.mysql_client = MySQLClient()

        # Health signals consumed by BotTaAnalysisHealthEvaluator (P2.7 #248).
        self._recent_analysis_latencies: deque[float] = deque(maxlen=200)
        self.signals_emitted = 0
        self._mysql_healthy = True

        # Proof-of-life signals for #265: distinguish "listening, zero NATS
        # traffic ever arrived" from "listening, traffic arrived, no signals
        # matched" so the health evaluator can detect a truly stalled listener
        # instead of reporting healthy forever on connectivity alone.
        self.messages_received = 0
        self._started_at: float | None = None
        self._last_message_at: float | None = None

    async def start(self):
        """Start the NATS listener."""
        try:
            self._started_at = time.monotonic()
            # Connect to NATS
            await self.nc.connect(self.nats_url)
            logger.info(f"Connected to NATS server: {self.nats_url}")

            # Initialize MySQL client
            await self.mysql_client.connect()

            # Initialize publisher
            await self.publisher.start()

            # Subscribe to candle data subjects
            await self._subscribe_to_candle_data()

            logger.info("NATS listener started successfully")

        except Exception as e:
            logger.error(f"Error starting NATS listener: {e}")
            raise

    def _resolve_subscription_prefixes(self) -> list[str]:
        """
        Resolve the minimal set of subject prefixes to subscribe to (#304).

        NATS delivers a message once per *matching* subscription. The
        configured production prefix is a dot-delimited descendant of the
        base prefix (e.g. `binance.extraction.production` under
        `binance.extraction`), so a `>` wildcard subscription on the base
        prefix also matches every message published under the production
        prefix. Subscribing to both therefore delivers each production
        message twice, independent of the queue-group fix for replica
        fan-out.

        This keeps only the most specific prefix whenever one configured
        prefix is an ancestor of another, and de-duplicates identical
        values. Genuinely disjoint prefixes (no ancestor relationship) are
        both kept, since neither subscription would double-match the
        other's messages.
        """
        prefixes = list(
            dict.fromkeys(
                p
                for p in (
                    self.nats_subject_prefix,
                    self.nats_subject_prefix_production,
                )
                if p
            )
        )

        def _is_ancestor_of_another(candidate: str) -> bool:
            return any(
                other != candidate and other.startswith(f"{candidate}.")
                for other in prefixes
            )

        return [p for p in prefixes if not _is_ancestor_of_another(p)]

    async def _subscribe_to_candle_data(self):
        """Subscribe to candle data subjects."""
        # De-duplicated prefixes (#304) — see _resolve_subscription_prefixes.
        # Using '>' multi-token wildcard to capture all sub-tokens (e.g. symbol and period)
        subjects = [f"{prefix}.>" for prefix in self._resolve_subscription_prefixes()]

        for subject in subjects:
            try:
                logger.info(
                    f"Attempting to subscribe to: {subject} "
                    f"(queue group: {self.nats_queue_group})"
                )
                # queue=self.nats_queue_group (#304): with `replicas: 2` and no
                # queue group, NATS fans this subscription out to every
                # replica, so both pods ran a full analysis cycle per
                # message. A shared queue group makes NATS deliver each
                # message to exactly one member of the group.
                subscription = await self.nc.subscribe(
                    subject,
                    queue=self.nats_queue_group,
                    cb=self._handle_candle_message,
                )
                self.subscriptions.append(subscription)
                logger.info(f"✅ SUCCESSFULLY subscribed to: {subject}")
            except Exception as e:
                logger.error(f"❌ FAILED to subscribe to {subject}: {e}")

        # SELF-TEST: Verify listener by publishing to it
        try:
            test_subject = f"{self.nats_subject_prefix_production}.klines.SELFTEST.1m"
            logger.info(f"Running NATS self-test on: {test_subject}")
            await self.nc.publish(
                test_subject,
                json.dumps({"symbol": "SELFTEST", "period": "1m"}).encode(),
            )
        except Exception as e:
            logger.error(f"NATS self-test publication failed: {e}")

    async def _handle_candle_message(self, msg):
        """Handle incoming candle message."""
        # RAW PRINT FOR DEBUGGING - BYPASSING ALL LOGGERS
        import sys

        sys.stdout.write(f"\n[RAW] !!! NATS MESSAGE RECEIVED ON {msg.subject} !!!\n")
        sys.stdout.flush()

        self.messages_received += 1
        self._last_message_at = time.monotonic()

        try:
            # Log every message received with subject and data length
            subject = msg.subject
            data_length = len(msg.data)
            logger.info(
                f"Received NATS message - Subject: {subject}, Data length: {data_length} bytes"
            )

            # Log the raw message data for debugging
            raw_data = msg.data.decode()
            logger.info(
                f"Raw message data: {raw_data[:200]}..."
                if len(raw_data) > 200
                else f"Raw message data: {raw_data}"
            )

            # Parse message data
            data = json.loads(raw_data)

            # Support both single symbol and batch messages
            event_type = data.get("event_type")
            if event_type == "batch_extraction_completed":
                symbols = data.get("symbols", [])
                period = data.get("period")
                logger.info(
                    f"Processing batch extraction completion for {len(symbols)} symbols on {period}"
                )
                for symbol in symbols:
                    await self._process_symbol_extraction(symbol, period)
                return

            # Standard single symbol message
            symbol = data.get("symbol")
            period = data.get("period") or data.get("timeframe")

            if not symbol or not period:
                logger.warning(
                    f"Invalid message format - missing symbol or period: {data}"
                )
                return

            await self._process_symbol_extraction(symbol, period)

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse NATS message: {e}")
            logger.error(f"Raw message: {msg.data.decode()}")
        except Exception as e:
            logger.error(f"Error processing candle message: {e}")
            logger.error(f"Subject: {msg.subject}, Data: {msg.data.decode()[:200]}...")

    async def _resolve_strategy_configs(
        self, symbol: str, enabled_strategies: list[str] | None
    ) -> dict[str, dict] | None:
        """
        Resolve per-strategy configuration ahead of a synchronous analysis cycle (#283).

        For each strategy that will actually run (either `enabled_strategies`, or —
        when that runtime filter is unset — every strategy `SignalEngine` knows
        about), calls the async `StrategyConfigManager.get_config(strategy_id,
        symbol)`, which implements the full resolution order: symbol override ->
        global override -> `defaults.py` -> auto-persisted default. Results are
        collected into a plain dict and handed to `SignalEngine.analyze_candles`,
        which never performs I/O itself.

        Hot-reload behavior: `StrategyConfigManager` maintains its own 60s TTL
        cache (`cache_ttl_seconds`, set at construction in `main.py`), so this is
        effectively "resolved every analysis cycle, cache-backed" -- a config
        change via `/api/v1/strategies/**` is live within at most one cache TTL
        window, not just on process restart.

        Returns `None` when no `StrategyConfigManager` is wired (the default in
        production today -- see the constructor docstring) or when resolution
        fails outright, in which case `SignalEngine._resolve_strategy_config`
        falls back to `defaults.py` for every strategy. A failure resolving a
        single strategy's config degrades only that strategy to `defaults.py`,
        never raises, and never blocks the other strategies in the same cycle.
        """
        if self.strategy_config_manager is None:
            return None

        target_names = enabled_strategies or list(self.signal_engine.strategies.keys())
        if not target_names:
            return None

        results = await asyncio.gather(
            *(
                self.strategy_config_manager.get_config(name, symbol)
                for name in target_names
            ),
            return_exceptions=True,
        )

        strategy_configs: dict[str, dict] = {}
        for name, result in zip(target_names, results, strict=True):
            if isinstance(result, BaseException):
                logger.debug(
                    f"Config resolution failed for strategy '{name}'; it will "
                    f"fall back to defaults.py for this cycle: {result}"
                )
                continue
            strategy_configs[name] = result

        return strategy_configs

    async def _process_symbol_extraction(self, symbol: str, period: str):
        """Process extraction completion for a specific symbol and period."""
        try:
            # Load runtime configuration if available
            runtime_config = None
            if self.app_config_manager:
                try:
                    runtime_config = await self.app_config_manager.get_config()
                    logger.debug(
                        f"Loaded runtime config version {runtime_config.get('version', 0)}"
                    )
                except Exception as e:
                    logger.warning(
                        f"Failed to load runtime config, using defaults: {e}"
                    )

            # Determine symbols and timeframes from runtime config or defaults
            if runtime_config and runtime_config.get("symbols"):
                active_symbols = runtime_config["symbols"]
            else:
                active_symbols = self.supported_symbols

            if runtime_config and runtime_config.get("candle_periods"):
                active_timeframes = runtime_config["candle_periods"]
            else:
                active_timeframes = self.supported_timeframes

            # Check if symbol and timeframe are supported.
            # Logged at WARNING (not DEBUG, per #265): a config-drift mismatch
            # between the extractor's published symbols/timeframes and this
            # bot's active_symbols/active_timeframes would otherwise silently
            # drop every inbound message with zero visible trace at default
            # log levels.
            if symbol not in active_symbols:
                logger.warning(
                    f"Skipping unsupported symbol: {symbol} (active: {active_symbols})"
                )
                return

            if period not in active_timeframes:
                logger.warning(
                    f"Skipping unsupported timeframe: {period} (active: {active_timeframes})"
                )
                return

            logger.info(f"Processing extraction completion for {symbol} {period}")

            # Fetch candle data from MySQL (250 candles needed for EMA200)
            try:
                df = await self.mysql_client.fetch_candles(symbol, period, limit=250)
                self._mysql_healthy = True
            except Exception as fetch_exc:
                self._mysql_healthy = False
                logger.error(
                    f"Candle-data fetch failed for {symbol} {period}: {fetch_exc}"
                )
                return

            if df is None or len(df) == 0:
                logger.warning(f"No candle data available for {symbol} {period}")
                return

            logger.info(f"Fetched {len(df)} candles for {symbol} {period}")

            # Extract runtime configuration parameters
            enabled_strategies = None
            min_confidence = None
            max_confidence = None

            if runtime_config:
                enabled_strategies = runtime_config.get("enabled_strategies")
                min_confidence = runtime_config.get("min_confidence")
                max_confidence = runtime_config.get("max_confidence")

            # Resolve per-strategy configuration (#283) *before* handing off to
            # the executor below -- StrategyConfigManager.get_config() is async
            # (it may hit Mongo), and analyze_candles/its strategies must never
            # perform I/O on the synchronous hot path.
            strategy_configs = await self._resolve_strategy_configs(
                symbol, enabled_strategies
            )

            # Analyze candles with runtime configuration
            # Run CPU-bound pandas/numpy computation in a thread pool executor to avoid
            # blocking the asyncio event loop and causing readiness probe timeouts.
            loop = asyncio.get_running_loop()
            _analysis_start = time.perf_counter()
            signals = await loop.run_in_executor(
                None,
                lambda: self.signal_engine.analyze_candles(
                    df=df,
                    symbol=symbol,
                    period=period,
                    enabled_strategies=enabled_strategies,
                    min_confidence=min_confidence,
                    max_confidence=max_confidence,
                    strategy_configs=strategy_configs,
                ),
            )
            self._recent_analysis_latencies.append(
                time.perf_counter() - _analysis_start
            )

            if signals:
                logger.info(f"Generated {len(signals)} signals for {symbol} {period}")

                # Persist signals to MySQL (using new format)
                signal_data_list = []
                for signal in signals:
                    signal_data = signal.to_dict()
                    signal_data_list.append(signal_data)

                success = await self.mysql_client.persist_signals_batch(
                    signal_data_list
                )

                if success:
                    logger.info(
                        f"Successfully persisted {len(signals)} signals to MySQL"
                    )
                else:
                    logger.error(
                        f"Failed to persist signals to MySQL for {symbol} {period}"
                    )

                # Publish signals to Trade Engine regardless of DB persistence outcome
                logger.info(
                    f"🚀 PUBLISHING {len(signals)} signals to Trade Engine via publisher"
                )
                await self.publisher.publish_signals(signals)
                self.signals_emitted += len(signals)
                logger.info(f"✅ Publisher call completed for {len(signals)} signals")

            else:
                logger.info(
                    f"No signals generated for {symbol} {period} - all strategies conditions not met"
                )
        except Exception as e:
            logger.error(f"Error processing symbol {symbol} {period}: {e}")

    def get_health_metrics(self) -> dict[str, Any]:
        """Expose readable health signals for BotTaAnalysisHealthEvaluator (#248, #265)."""
        pub_client = getattr(self.publisher, "nats_client", None)
        latencies = self._recent_analysis_latencies
        now = time.monotonic()
        return {
            "nats_connected": bool(pub_client and pub_client.is_connected),
            "mysql_healthy": self._mysql_healthy,
            "analysis_latency_s": (
                sum(latencies) / len(latencies) if latencies else 0.0
            ),
            "signals_emitted": self.signals_emitted,
            # Proof-of-life signals (#265): let the evaluator distinguish
            # "connected, zero candle-extraction messages ever received" from
            # "connected, receiving traffic, just no signal matches".
            "messages_received": self.messages_received,
            "seconds_since_start": (
                (now - self._started_at) if self._started_at is not None else 0.0
            ),
            "seconds_since_last_message": (
                (now - self._last_message_at)
                if self._last_message_at is not None
                else None
            ),
        }

    async def _cleanup(self):
        """Clean up NATS connections and subscriptions."""
        try:
            # Stop publisher
            await self.publisher.stop()

            # Unsubscribe from all topics
            for subscription in self.subscriptions:
                await subscription.unsubscribe()

            # Close NATS connection
            await self.nc.close()

            # Close MySQL connection
            await self.mysql_client.disconnect()

            logger.info("NATS listener cleaned up")

        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

    async def stop(self):
        """Stop the NATS listener."""
        await self._cleanup()
